import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import toast from 'react-hot-toast';
import { AuthService } from '../services/auth';
import {
  buildOAuthLoginUrl,
  createOAuthState,
  resolveOAuthRedirectUri,
} from '../utils/oauthConfig';
import {
  clearPaymentIntentCache,
  clearPendingMembershipSync,
  clearPaymentResumeCheckoutPending,
  clearPaymentResumeTarget,
  clearOAuthRequest,
  formatToolNameFromPath,
  hasPaymentResumeCheckoutPending,
  markPaymentResumeCheckoutPending,
  readPaymentIntentCache,
  readPaymentResumeTarget,
  readOAuthReturnTo,
  readOAuthState,
  sanitizeReturnTo,
  storePaymentIntentCache,
  storeOAuthRequest,
} from '../utils/authStorage';

const DEFAULT_RETURN_TO = '/';
let refreshMembershipStatusInFlight = null;

const getDefaultRedirectUri = () => {
  return resolveOAuthRedirectUri();
};

const getSafeReturnTo = (returnTo) => sanitizeReturnTo(returnTo || DEFAULT_RETURN_TO);

const buildAccountRouteForReturnTo = (returnTo) => {
  const safeReturnTo = getSafeReturnTo(returnTo);
  const params = new URLSearchParams({ returnTo: safeReturnTo });
  const toolName = formatToolNameFromPath(safeReturnTo);
  if (toolName) {
    params.set('tool', toolName);
  }
  return `/account?${params.toString()}`;
};

const buildAbsoluteAccountRouteForReturnTo = (returnTo) => {
  if (typeof window === 'undefined') {
    return buildAccountRouteForReturnTo(returnTo);
  }
  return `${window.location.origin}${buildAccountRouteForReturnTo(returnTo)}`;
};

const buildPaymentReturnUrlForRoute = (absoluteAccountRoute) => {
  if (typeof window === 'undefined') {
    return absoluteAccountRoute;
  }
  return `${window.location.origin}/payment-return.html?target=${encodeURIComponent(absoluteAccountRoute)}`;
};

const mergeMembershipIntoProfile = (profile, membershipPayload, previousProfile) => {
  if (!profile && !previousProfile) {
    return null;
  }

  const baseProfile = profile || previousProfile || null;
  if (!baseProfile) {
    return null;
  }

  const webMemberData = membershipPayload?.data || {};
  const active = webMemberData.web_member_active == null
    ? Boolean(baseProfile?.is_vip || previousProfile?.is_vip)
    : Boolean(webMemberData.web_member_active);
  const isVip = webMemberData.web_member_active == null
    ? Boolean(baseProfile?.is_vip)
    : Boolean(baseProfile?.is_vip || active);
  const expireAt = webMemberData.web_member_expire_at
    || baseProfile?.vip_expire_time
    || previousProfile?.vip_expire_time
    || null;
  const vipLevel = isVip
    ? Number(baseProfile?.vip_level || previousProfile?.vip_level || 1)
    : 0;
  const trialActive = isVip
    ? false
    : Boolean(
      webMemberData.trial_active == null
        ? baseProfile?.trial_active
        : webMemberData.trial_active
    );

  return {
    ...baseProfile,
    web_member_active: webMemberData.web_member_active == null
      ? Boolean(baseProfile.web_member_active ?? baseProfile.is_vip)
      : active,
    web_member_expire_at: expireAt,
    vip_expire_time: expireAt || baseProfile.vip_expire_time,
    is_vip: isVip,
    vip_level: vipLevel,
    trial_active: trialActive,
    access_code: baseProfile.access_code || webMemberData.access_code || '',
    payment_auth_expired: Boolean(baseProfile.payment_auth_expired || webMemberData.payment_auth_expired),
    access_state: isVip ? 'member_active' : (baseProfile.access_state || webMemberData.access_state || ''),
  };
};

export const useUserStore = create(
  persist(
    (set, get) => ({
      token: null,
      apiWebToken: null,
      userInfo: null,
      userProfile: null,
      webMemberStatus: null,
      recentRecords: [],
      isLoggedIn: false,
      isPolling: false,
      profileHydrating: false,
      isLoginModalVisible: false,
      pendingReturnTo: DEFAULT_RETURN_TO,

      showLoginModal: (returnTo = DEFAULT_RETURN_TO) => {
        set({
          isLoginModalVisible: true,
          pendingReturnTo: getSafeReturnTo(returnTo),
        });
      },

      hideLoginModal: () => set({ isLoginModalVisible: false }),

      prewarmMembershipPaymentIntent: async (returnTo = DEFAULT_RETURN_TO, options = {}) => {
        const token = get().token || null;
        if (!token || typeof window === 'undefined') {
          return null;
        }

        const absoluteAccountRoute = buildAbsoluteAccountRouteForReturnTo(returnTo);
        const now = Date.now();
        const sharedCached = readPaymentIntentCache();
        if (
          !options.force
          && sharedCached?.data
          && sharedCached.route === absoluteAccountRoute
          && now - sharedCached.fetchedAt < 30 * 1000
        ) {
          return sharedCached.data;
        }

        const paymentReturnUrl = buildPaymentReturnUrlForRoute(absoluteAccountRoute);
        const data = await AuthService.getMembershipPaymentPageUrl(token, paymentReturnUrl);
        if (data?.payment_url) {
          storePaymentIntentCache({
            route: absoluteAccountRoute,
            fetchedAt: Date.now(),
            data,
          });
        } else if (options.force) {
          clearPaymentIntentCache();
        }
        return data;
      },

      openUserCenter: async (navigate, returnTo = DEFAULT_RETURN_TO) => {
        const safeReturnTo = getSafeReturnTo(returnTo);
        set({ pendingReturnTo: safeReturnTo, isLoginModalVisible: false });
        navigate(buildAccountRouteForReturnTo(safeReturnTo));
      },

      startLoginProcess: async (options = {}) => {
        const returnTo = getSafeReturnTo(options.returnTo || get().pendingReturnTo || DEFAULT_RETURN_TO);
        const redirectUri = options.redirectUri || getDefaultRedirectUri();
        const generatedState = options.state || createOAuthState();
        set({ isPolling: true, pendingReturnTo: returnTo, isLoginModalVisible: false });

        try {
          const { loginUrl } = buildOAuthLoginUrl({
            state: generatedState,
            redirectUri,
          });
          const state = generatedState;
          if (!state || !loginUrl) {
            throw new Error('Failed to create Kunqiong login URL');
          }

          storeOAuthRequest({ state, returnTo });

          if (window.electronAPI?.openExternal) {
            await window.electronAPI.openExternal(loginUrl);
          } else {
            window.location.href = loginUrl;
          }

          return loginUrl;
        } catch (error) {
          set({ isPolling: false });
          toast.error(error?.message || 'Failed to start login');
          throw error;
        }
      },

      refreshProfile: async (options = {}) => {
        let { token } = get();
        if (!token) {
          set({ userInfo: null, userProfile: null, recentRecords: [], isLoggedIn: false, webMemberStatus: null, profileHydrating: false });
          return null;
        }

        try {
          // 1. 获取主站会员信息 (只有在非静默模式下才请求，避免登录时 401 中断流程)
          let packageInfo = null;
          if (!options.skipWebMember) {
            packageInfo = await AuthService.getWebMemberPackageInfo(token, {
              forceSync: Boolean(options.forceMembershipSync),
              previousExpireAt: options.previousExpireAt || '',
              previousActive: typeof options.previousActive === 'boolean' ? options.previousActive : undefined,
            }).catch(() => null);
          }
          
          // 重新检查 token
          token = get().token;
          if (!token) return null;

          // 2. 获取子站用户信息
          const userInfo = await AuthService.getUserInfo(token).catch(() => null);
          
          token = get().token;
          if (!token) return null;

          // 3. 获取详细 Profile
          const userProfile = await AuthService.getUserProfile(token).catch(() => null);
          
          token = get().token;
          if (!token) return null;

          // 4. 获取最近记录
          const recentRecords = await AuthService.getRecentRecords(token, 10).catch(() => []);

          // 从 profile 响应中提取 apiWebToken（主站 Token），优先使用 profile 返回的值
          const apiWebToken = userProfile?.api_web_token || get().apiWebToken || token;
          if (apiWebToken) {
            localStorage.setItem('kq_api_web_token', apiWebToken);
            const hostname = window.location.hostname;
            const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
            const domain = isLocalhost ? '' : '.kunqiongai.com';
            const domainAttr = domain ? `domain=${domain};` : '';
            const secureAttr = window.location.protocol === 'https:' ? 'Secure;' : '';
            document.cookie = `api_web_token=${encodeURIComponent(apiWebToken)}; path=/; ${domainAttr} SameSite=None; ${secureAttr}`;
            document.cookie = `kq_token=${encodeURIComponent(apiWebToken)}; path=/; ${domainAttr} SameSite=None; ${secureAttr}`;
          }

          const mergedProfile = mergeMembershipIntoProfile(userProfile, packageInfo, get().userProfile);
          const webMemberStatus = {
            active: Boolean(mergedProfile?.web_member_active || mergedProfile?.is_vip),
            expireAt: mergedProfile?.web_member_expire_at || mergedProfile?.vip_expire_time || null,
          };

          set({
            apiWebToken: apiWebToken || null,
            userInfo,
            userProfile: mergedProfile,
            webMemberStatus,
            recentRecords,
            isLoggedIn: Boolean(mergedProfile),
            isPolling: false,
            profileHydrating: false,
          });

          return mergedProfile;
        } catch (error) {
          console.error('refreshProfile error:', error);
          set({ profileHydrating: false, isPolling: false });
          return null;
        }
      },

      refreshMembershipStatus: async (options = {}) => {
        let { token } = get();
        if (!token) {
          return null;
        }

        const shouldDedup = !options.forceMembershipSync;
        if (shouldDedup && refreshMembershipStatusInFlight) {
          return refreshMembershipStatusInFlight;
        }

        try {
          const requestPromise = AuthService.getWebMemberPackageInfo(token, {
            forceSync: Boolean(options.forceMembershipSync),
            previousExpireAt: options.previousExpireAt || '',
            previousActive: typeof options.previousActive === 'boolean' ? options.previousActive : undefined,
          }).catch(() => null);
          if (shouldDedup) {
            refreshMembershipStatusInFlight = requestPromise;
          }
          const packageInfo = await requestPromise;

          token = get().token;
          if (!token) return null;

          const previousProfile = get().userProfile;
          const mergedProfile = mergeMembershipIntoProfile(previousProfile, packageInfo, previousProfile);
          const webMemberStatus = {
            active: Boolean(mergedProfile?.web_member_active || mergedProfile?.is_vip),
            expireAt: mergedProfile?.web_member_expire_at || mergedProfile?.vip_expire_time || null,
          };

          set({
            userProfile: mergedProfile,
            webMemberStatus,
            isLoggedIn: Boolean(mergedProfile || get().isLoggedIn),
            profileHydrating: false,
          });

          return mergedProfile;
        } catch (error) {
          console.error('refreshMembershipStatus error:', error);
          set({ profileHydrating: false });
          return null;
        } finally {
          if (shouldDedup) {
            refreshMembershipStatusInFlight = null;
          }
        }
      },

      handleOAuthCallback: async ({ code, state, redirectUri }) => {
        const storedState = readOAuthState();
        if (!code) {
          throw new Error('Missing OAuth code');
        }
        if (!state || state !== storedState) {
          clearOAuthRequest();
          throw new Error('Login callback state mismatch');
        }

        set({ isPolling: true });

        try {
          const result = await AuthService.exchangeOAuthCode({
            code,
            state,
            redirectUri: redirectUri || getDefaultRedirectUri(),
          });
          const data = result?.data || {};
          const token = data.access_token;
          const apiWebToken = data.api_web_token || token;
          if (!token) {
            throw new Error('Local session token is missing');
          }

          // 将 api_web_token 写入 cookie 和 localStorage，使主站支付页面能识别登录态，同时也让前端请求能带上
          if (apiWebToken) {
            localStorage.setItem('kq_api_web_token', apiWebToken);
            const hostname = window.location.hostname;
            const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
            const domain = isLocalhost ? '' : '.kunqiongai.com';
            const domainAttr = domain ? `domain=${domain};` : '';
            const secureAttr = window.location.protocol === 'https:' ? 'Secure;' : '';
            document.cookie = `api_web_token=${encodeURIComponent(apiWebToken)}; path=/; ${domainAttr} SameSite=None; ${secureAttr}`;
            document.cookie = `kq_token=${encodeURIComponent(apiWebToken)}; path=/; ${domainAttr} SameSite=None; ${secureAttr}`;
          }

          set({
            token,
            apiWebToken: apiWebToken || null,
            userInfo: data.user || null,
            userProfile: data.user_profile || null,
            webMemberStatus: {
              active: Boolean(data?.user_profile?.web_member_active || data?.user_profile?.is_vip),
              expireAt: data?.user_profile?.web_member_expire_at || data?.user_profile?.vip_expire_time || null,
            },
            isLoggedIn: true,
            isPolling: false,
            profileHydrating: true,
          });
          void get().refreshProfile({ skipWebMember: true }).finally(() => {
            const { profileHydrating } = get();
            if (profileHydrating) {
              set({ profileHydrating: false, isPolling: false });
            }
          });
          void get().refreshMembershipStatus().catch(() => null);

          const paymentResumeTarget = readPaymentResumeTarget();
          if (paymentResumeTarget) {
            markPaymentResumeCheckoutPending();
            clearPaymentResumeTarget();
            const safeResumeTarget = getSafeReturnTo(paymentResumeTarget);
            clearOAuthRequest();
            set({ pendingReturnTo: safeResumeTarget });
            window.setTimeout(() => {
              void get().prewarmMembershipPaymentIntent(safeResumeTarget, { force: true }).catch(() => null);
            }, 0);
            return safeResumeTarget;
          }
          const returnTo = getSafeReturnTo(readOAuthReturnTo());
          clearOAuthRequest();
          set({ pendingReturnTo: returnTo });
          return returnTo;
        } catch (error) {
          clearOAuthRequest();
          set({ isPolling: false });
          throw error;
        }
      },

      requireFeatureAccess: ({ navigate, returnTo, filesCount = 1, disableWatermark = false, t }) => {
        // 跳过登录：所有用户均可使用完整功能
        return true;
      },

      logout: async () => {
        const { token } = get();
        clearOAuthRequest();
        clearPaymentResumeCheckoutPending();
        clearPaymentResumeTarget();
        clearPendingMembershipSync();
        set({
          token: null,
          apiWebToken: null,
          userInfo: null,
          userProfile: null,
          recentRecords: [],
          isLoggedIn: false,
          isPolling: false,
          isLoginModalVisible: false,
          pendingReturnTo: DEFAULT_RETURN_TO,
        });
        localStorage.removeItem('kq_api_web_token');
        // 同时清理可能存在的 cookie
        const hostname = window.location.hostname;
        const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
        const domain = isLocalhost ? '' : '.kunqiongai.com';
        const domainAttr = domain ? `domain=${domain};` : '';
        const secureAttr = window.location.protocol === 'https:' ? 'Secure;' : '';
        document.cookie = `api_web_token=; path=/; ${domainAttr} expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=None; ${secureAttr}`;
        document.cookie = `kq_token=; path=/; ${domainAttr} expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=None; ${secureAttr}`;
        console.log('User logged out, tokens cleared');

        try {
          if (token) {
            void AuthService.logout(token);
          }
        } catch {
          // Local cleanup still wins.
        }
      },

      init: async () => {
        // 检查是否有持久化的真实 token
        const persistedToken = get().token;
        if (persistedToken && persistedToken !== '__guest_bypass_token__') {
          // 有真实 token，尝试验证登录状态
          try {
            const loggedIn = await AuthService.checkLogin(persistedToken);
            if (loggedIn) {
              set({ isLoggedIn: true, isPolling: false, profileHydrating: false });
              // 异步刷新 profile
              void get().refreshProfile({ skipWebMember: true }).catch(() => {});
              return;
            }
          } catch {
            // 验证失败，清除过期 token
          }
        }
        // 访客模式：未登录状态
        set({
          isLoggedIn: false,
          token: null,
          apiWebToken: null,
          userInfo: null,
          userProfile: null,
          recentRecords: [],
          isPolling: false,
          profileHydrating: false,
        });
      },

      hasPendingPaymentResumeCheckout: () => hasPaymentResumeCheckoutPending(),

      clearPendingPaymentResumeCheckout: () => clearPaymentResumeCheckoutPending(),
    }),
    {
      name: 'user-storage',
      partialize: (state) => ({
        // Bug#6: Do NOT persist guest/bogus tokens to localStorage.
        // Only persist tokens that look like real OAuth/JWT tokens.
        token: (() => {
          const t = state.token;
          if (!t || t === '__guest_bypass_token__' || t.length < 10) return null;
          if (t.startsWith('__') && t.endsWith('__')) return null;
          return t;
        })(),
        apiWebToken: state.apiWebToken,
        userInfo: state.userInfo,
        userProfile: state.userProfile,
        isLoggedIn: state.isLoggedIn,
        // webMemberStatus is NOT persisted; it is fetched from main-site on each refreshProfile
      }),
    }
  )
);
