import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import { App } from 'antd';
import { AuthService } from '../services/auth';
import { createSafeTranslator } from '../utils/safeTranslation';
import {
  clearPaymentIntentCache,
  clearPendingMembershipSync,
  getPersistedToken,
  readPendingMembershipSync,
  readPaymentIntentCache,
  storePaymentResumeTarget,
  storePaymentIntentCache,
  storePendingMembershipSync,
  sanitizeReturnTo,
} from '../utils/authStorage';
import { useUserStore } from '../stores/useUserStore';

function getMembershipStatus(userProfile, t, profileHydrating = false) {
  const hasResolvedStatus = Boolean(
    userProfile?.is_vip
    || userProfile?.trial_active
    || userProfile?.access_state
    || userProfile?.vip_expire_time
    || userProfile?.trial_expire_time
  );
  if (profileHydrating && !hasResolvedStatus) {
    return t('userCenter.syncing_status', { defaultValue: '状态同步中' });
  }
  if (userProfile?.is_vip) return t('userCenter.status_active');
  if (userProfile?.trial_active) return t('userCenter.status_trial');
  return t('userCenter.status_standard');
}

function getRemainingDays(userProfile, t, profileHydrating = false) {
  const hasResolvedExpireAt = Boolean(
    userProfile?.web_member_expire_at
    || userProfile?.vip_expire_time
    || userProfile?.trial_expire_time
  );
  if (profileHydrating && !hasResolvedExpireAt) return '--';
  if (!userProfile?.is_vip && Number.isFinite(userProfile?.remaining_days) && userProfile.remaining_days > 0) {
    return `${userProfile.remaining_days}${t('userCenter.time_unit_day', { defaultValue: '天' })}`;
  }
  // 优先逻辑：如果是会员，取正式会员到期时间；否则取试用到期时间
  const expireAt = userProfile?.is_vip 
    ? userProfile?.web_member_expire_at || userProfile?.vip_expire_time
    : userProfile?.trial_expire_time;
    
  if (!expireAt) return '--';
  const expireDate = new Date(expireAt);
  if (Number.isNaN(expireDate.getTime())) return '--';
  const now = new Date();
  const diffMs = expireDate.getTime() - now.getTime();
  
  if (diffMs <= 0) return '0';

  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  let result = '';
  if (days > 0) result += `${days}${t('userCenter.time_unit_day', { defaultValue: '天' })}`;
  if (hours > 0) result += `${hours}${t('userCenter.time_unit_hour', { defaultValue: '时' })}`;
  if (minutes > 0 || (days === 0 && hours === 0)) {
    result += `${minutes}${t('userCenter.time_unit_minute', { defaultValue: '分' })}`;
  }
  
  return result;
}

function formatDateTime(value) {
  if (!value) return '--';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString(undefined, { hour12: false });
}

function getVipLevelLabel(userProfile, t, profileHydrating = false) {
  const hasResolvedLevel = Boolean(userProfile?.is_vip || userProfile?.vip_level || userProfile?.trial_active);
  if (profileHydrating && !hasResolvedLevel) return '--';
  if (userProfile?.is_vip) {
    return `VIP${userProfile?.vip_level > 1 ? userProfile.vip_level : ''}`;
  }
  if (userProfile?.vip_level) {
    return `VIP${userProfile.vip_level > 1 ? userProfile.vip_level : ''}`;
  }
  if (userProfile?.trial_active) {
    return t('userCenter.status_trial');
  }
  return t('userCenter.status_standard');
}

function getVipExpireLabel(userProfile, t, profileHydrating = false) {
  if (profileHydrating && !userProfile?.vip_expire_time && !userProfile?.is_vip) return '--';
  if (userProfile?.vip_expire_time) {
    return formatDateTime(userProfile.vip_expire_time);
  }
  return userProfile?.is_vip ? '--' : t('userCenter.not_enabled');
}

function formatRecordStatus(status, t) {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'completed' || normalized === 'success' || normalized === 'done') {
    return t('userCenter.record_status_completed');
  }
  if (normalized === 'failed' || normalized === 'error') {
    return t('userCenter.record_status_failed');
  }
  if (normalized === 'processing' || normalized === 'running') {
    return t('userCenter.record_status_processing');
  }
  if (normalized === 'waiting' || normalized === 'pending' || normalized === 'queued') {
    return t('userCenter.record_status_waiting');
  }
  return status || '--';
}

function getPhoneValue(userInfo, userProfile) {
  return userInfo?.phone
    || userInfo?.mobile
    || userInfo?.phone_number
    || userProfile?.phone
    || userProfile?.mobile
    || userProfile?.phone_number
    || '--';
}

function getMembershipExpireAt(userProfile) {
  return userProfile?.web_member_expire_at || userProfile?.vip_expire_time || '';
}

function buildPaymentReturnUrl(targetUrl) {
  if (typeof window === 'undefined') {
    return targetUrl || '';
  }
  const callbackUrl = new URL('/payment-return.html', window.location.origin);
  callbackUrl.searchParams.set('target', targetUrl || `${window.location.origin}/account`);
  return callbackUrl.toString();
}

function UserCenterPage() {
  const { message } = App.useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const { t: rawT, i18n } = useTranslation();
  const fallbackT = i18n.getFixedT('en');
  const t = createSafeTranslator(rawT, fallbackT, i18n.language);
  const paymentIntentCacheRef = useRef({
    route: '',
    fetchedAt: 0,
    data: null,
    promise: null,
  });
  const lastMembershipSyncAtRef = useRef(0);
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const returnTo = sanitizeReturnTo(searchParams.get('returnTo'));

  const {
    isLoggedIn,
    isPolling,
    profileHydrating,
    userInfo,
    userProfile,
    recentRecords,
    init,
    startLoginProcess,
    logout,
    hasPendingPaymentResumeCheckout,
    clearPendingPaymentResumeCheckout,
  } = useUserStore();

  useEffect(() => {
    // 页面加载时只初始化基础信息，不强制刷新 profile（避免触发自动登出循环）
    if (!isLoggedIn) {
      init();
    } else {
      useUserStore.getState().refreshProfile({ skipWebMember: true });
    }
  }, [init, isLoggedIn]);

  useEffect(() => {
    if (!isLoggedIn) {
      return undefined;
    }

    let timers = [];

    const syncProfile = (options = {}) => {
      useUserStore.getState().refreshProfile(options);
    };

    const syncProfileWithRetry = () => {
      const now = Date.now();
      if (now - lastMembershipSyncAtRef.current < 2500) {
        return;
      }
      lastMembershipSyncAtRef.current = now;
      timers.forEach((timer) => clearTimeout(timer));
      timers = [];
      useUserStore.getState().refreshMembershipStatus();
      syncProfile({ skipWebMember: true });
      [1500, 4000, 8000].forEach((delay) => {
        const timer = window.setTimeout(() => {
          useUserStore.getState().refreshMembershipStatus();
        }, delay);
        timers.push(timer);
      });
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        syncProfileWithRetry();
      }
    };

    const hasPaymentReturnHint = ['kq_token', 'token', 'api_web_token', 'order_no', 'pay_status']
      .some((key) => searchParams.has(key));
    if (hasPaymentReturnHint) {
      syncProfileWithRetry();
    }

    window.addEventListener('focus', syncProfileWithRetry);
    window.addEventListener('pageshow', syncProfileWithRetry);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      timers.forEach((timer) => clearTimeout(timer));
      window.removeEventListener('focus', syncProfileWithRetry);
      window.removeEventListener('pageshow', syncProfileWithRetry);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isLoggedIn, searchParams]);

  useEffect(() => {
    if (!isLoggedIn) {
      return undefined;
    }

    const pendingSync = readPendingMembershipSync();
    if (!pendingSync) {
      return undefined;
    }

    if (pendingSync.startedAt && Date.now() - pendingSync.startedAt > 2 * 60 * 1000) {
      clearPendingMembershipSync();
      return undefined;
    }

    if (location.pathname !== '/account') {
      return undefined;
    }

    const hasPaymentReturnHint = ['kq_token', 'token', 'api_web_token', 'order_no', 'pay_status']
      .some((key) => searchParams.has(key));
    const currentExpireAt = getMembershipExpireAt(userProfile);
    const currentActive = Boolean(userProfile?.is_vip || userProfile?.web_member_active);
    const matchesPendingSnapshot = Boolean(
      pendingSync.active
      && currentActive
      && currentExpireAt
      && currentExpireAt === (pendingSync.expireAt || '')
    );
    if (matchesPendingSnapshot && !hasPaymentReturnHint) {
      clearPendingMembershipSync();
      return undefined;
    }

    let disposed = false;
    let intervalId = null;
    let timeoutId = null;
    let syncInFlight = false;

    const stopSync = () => {
      if (intervalId) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
      if (timeoutId) {
        window.clearTimeout(timeoutId);
        timeoutId = null;
      }
    };

    const hasMembershipUpdated = (profile) => {
      const nextExpireAt = getMembershipExpireAt(profile);
      const nextActive = Boolean(profile?.is_vip || profile?.web_member_active);

      if (!pendingSync.active) {
        return nextActive || (nextExpireAt && nextExpireAt !== pendingSync.expireAt);
      }

      return Boolean(nextExpireAt) && nextExpireAt !== pendingSync.expireAt;
    };

    const syncUntilUpdated = async () => {
      if (syncInFlight) {
        return;
      }
      syncInFlight = true;
      const profile = await useUserStore.getState().refreshMembershipStatus({
        forceMembershipSync: true,
        previousExpireAt: pendingSync.expireAt || '',
        previousActive: pendingSync.active,
      });
      try {
        if (disposed) {
          return;
        }
        if (hasMembershipUpdated(profile)) {
          void useUserStore.getState().refreshProfile({ skipWebMember: true });
          clearPendingMembershipSync();
          stopSync();
        }
      } finally {
        syncInFlight = false;
      }
    };

    syncUntilUpdated();
    intervalId = window.setInterval(syncUntilUpdated, 1500);
    timeoutId = window.setTimeout(() => {
      clearPendingMembershipSync();
      stopSync();
    }, 90 * 1000);

    return () => {
      disposed = true;
      stopSync();
    };
  }, [isLoggedIn, location.pathname]);

  const resolvePaymentIntent = useCallback(async ({ force = false } = {}) => {
    const token = getPersistedToken();
    if (!token) {
      return null;
    }

    const currentRoute = `${window.location.origin}${location.pathname}${location.search || ''}`;
    const paymentReturnUrl = buildPaymentReturnUrl(currentRoute);
    const cached = paymentIntentCacheRef.current;
    const now = Date.now();
    const sharedCached = readPaymentIntentCache();
    const isFresh = !force
      && cached.data
      && cached.route === currentRoute
      && now - cached.fetchedAt < 30 * 1000;

    if (isFresh) {
      return cached.data;
    }

    if (!force && sharedCached?.data && sharedCached.route === currentRoute && now - sharedCached.fetchedAt < 30 * 1000) {
      paymentIntentCacheRef.current = {
        route: sharedCached.route,
        fetchedAt: sharedCached.fetchedAt,
        data: sharedCached.data,
        promise: null,
      };
      return sharedCached.data;
    }

    if (cached.promise && cached.route === currentRoute && !force) {
      return cached.promise;
    }

    const nextPromise = AuthService.getMembershipPaymentPageUrl(token, paymentReturnUrl)
      .then((data) => {
        const fetchedAt = Date.now();
        paymentIntentCacheRef.current = {
          route: currentRoute,
          fetchedAt,
          data,
          promise: null,
        };
        storePaymentIntentCache({
          route: currentRoute,
          fetchedAt,
          data,
        });
        return data;
      })
      .catch((error) => {
        paymentIntentCacheRef.current = {
          route: currentRoute,
          fetchedAt: 0,
          data: null,
          promise: null,
        };
        clearPaymentIntentCache();
        throw error;
      });

    paymentIntentCacheRef.current = {
      route: currentRoute,
      fetchedAt: cached.fetchedAt,
      data: cached.data,
      promise: nextPromise,
    };

    return nextPromise;
  }, [location.pathname, location.search]);

  useEffect(() => {
    if (!isLoggedIn || !userProfile) {
      paymentIntentCacheRef.current = {
        route: '',
        fetchedAt: 0,
        data: null,
        promise: null,
      };
      clearPaymentIntentCache();
      return;
    }

    if (userProfile?.access_code === 'upstream_login_expired' || userProfile?.payment_auth_expired) {
      return;
    }

    const timer = window.setTimeout(() => {
      void resolvePaymentIntent().catch(() => null);
    }, 150);

    return () => {
      window.clearTimeout(timer);
    };
  }, [isLoggedIn, userProfile, resolvePaymentIntent]);

  const membershipStatus = getMembershipStatus(userProfile, t, profileHydrating);
  const phoneValue = getPhoneValue(userInfo, userProfile);

  const handleMembershipRedirect = useCallback(async () => {
    const token = getPersistedToken();
    if (!token) {
      message.warning(t('userCenter.login_required_action'));
      return;
    }

    const currentRoute = `${window.location.origin}${location.pathname}${location.search || ''}`;
    const cachedPaymentIntent = paymentIntentCacheRef.current?.data;
    const canInstantRedirect = Boolean(
      cachedPaymentIntent
      && paymentIntentCacheRef.current?.route === currentRoute
      && Date.now() - (paymentIntentCacheRef.current?.fetchedAt || 0) < 30 * 1000
    );
    let loadingTimer = null;
    const showLoadingLater = () => {
      if (canInstantRedirect) {
        return;
      }
      loadingTimer = window.setTimeout(() => {
        message.loading({ content: t('userCenter.checking_status', { defaultValue: '正在跳转支付...' }), key: 'check-status' });
      }, 180);
    };

    const clearLoadingLater = () => {
      if (loadingTimer) {
        window.clearTimeout(loadingTimer);
        loadingTimer = null;
      }
    };

    showLoadingLater();
    try {
      if (userProfile?.access_code === 'upstream_login_expired' || userProfile?.payment_auth_expired) {
        clearLoadingLater();
        storePaymentResumeTarget(currentRoute);
        message.loading({
          content: t('userCenter.session_expired_relogin', { defaultValue: '支付凭证已过期，正在重新登录...' }),
          key: 'check-status',
        });
        startLoginProcess({ returnTo: currentRoute });
        return;
      }

      const paymentIntent = await resolvePaymentIntent();
      clearLoadingLater();
      const paymentUrl = paymentIntent?.payment_url;
      if (paymentIntent?.requires_relogin || paymentIntent?.payment_auth_expired) {
        storePaymentResumeTarget(currentRoute);
        message.loading({
          content: t('userCenter.session_expired_relogin', { defaultValue: '支付凭证已过期，正在重新登录...' }),
          key: 'check-status',
        });
        startLoginProcess({ returnTo: currentRoute });
        return;
      }
      if (paymentUrl) {
        storePendingMembershipSync({
          returnTo: currentRoute,
          expireAt: getMembershipExpireAt(userProfile),
          active: Boolean(userProfile?.is_vip || userProfile?.web_member_active),
        });
        message.destroy('check-status');
        window.location.assign(paymentUrl);
      } else {
        message.error(t('userCenter.payment_url_missing', { defaultValue: '支付链接获取失败，请刷新重试。' }));
      }
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const errorCode = detail?.code || err?.response?.data?.code || '';
      clearLoadingLater();
      if (err?.response?.status === 401 || errorCode === 'upstream_login_expired' || errorCode === 'login_expired') {
        storePaymentResumeTarget(currentRoute);
        message.loading({
          content: t('userCenter.session_expired_relogin', { defaultValue: '支付凭证已过期，正在重新登录...' }),
          key: 'check-status',
        });
        startLoginProcess({ returnTo: currentRoute });
        return;
      }
      console.error('Check membership status failed:', err);
      message.error({ content: t('userCenter.check_failed', { defaultValue: '状态检查失败，请稍后重试' }), key: 'check-status' });
    } finally {
      clearLoadingLater();
      message.destroy('check-status');
    }
  }, [location.pathname, location.search, message, resolvePaymentIntent, startLoginProcess, t, userProfile]);

  useEffect(() => {
    if (!isLoggedIn) {
      return;
    }
    if (!hasPendingPaymentResumeCheckout()) {
      return;
    }

    clearPendingPaymentResumeCheckout();
    const timer = window.setTimeout(() => {
      void handleMembershipRedirect();
    }, 50);

    return () => window.clearTimeout(timer);
  }, [
    clearPendingPaymentResumeCheckout,
    handleMembershipRedirect,
    hasPendingPaymentResumeCheckout,
    isLoggedIn,
  ]);

  return (
    <div className="user-center-page">
      <div className="user-center-shell">
        {!isLoggedIn || !userProfile ? (
          <section className="user-center-card user-center-login-card">
            <div>
              <span className="user-center-chip">{t('userCenter.not_logged_in')}</span>
              <h2>{t('userCenter.login_title')}</h2>
              <p>{t('userCenter.login_hint')}</p>
            </div>
            <button
              type="button"
              className="user-center-primary-btn"
              onClick={() => startLoginProcess({ returnTo })}
              disabled={isPolling}
            >
              {isPolling ? t('header.logging_in') : t('userCenter.login_now')}
            </button>
          </section>
        ) : (
          <>
            <section className="user-center-card user-center-overview-card">
              <div className="user-center-overview-main">
                {userInfo?.avatar ? (
                  <img src={userInfo.avatar} alt={userInfo?.nickname || 'avatar'} className="user-center-avatar" />
                ) : (
                  <div className="user-center-avatar user-center-avatar-fallback">
                    {(userInfo?.nickname || userInfo?.username || 'U').slice(0, 1)}
                  </div>
                )}

                <div className="user-center-overview-copy">
                  <h1>{t('userCenter.account_center_title')}</h1>
                  <p>{t('userCenter.account_center_subtitle')}</p>
                </div>
              </div>

              <div className="user-center-actions">
                <button type="button" className="user-center-secondary-btn" onClick={() => navigate('/')}>
                  {t('userCenter.back_home')}
                </button>
                <button type="button" className="user-center-secondary-btn user-center-logout-btn" onClick={logout}>
                  {t('loginModal.logout')}
                </button>
              </div>
            </section>

            <div className="user-center-summary-grid">
              <section className="user-center-card user-center-summary-card">
                <span className="user-center-summary-label">{t('userCenter.current_status')}</span>
                <strong className="user-center-summary-value">{membershipStatus}</strong>
              </section>

              <section className="user-center-card user-center-summary-card">
                <span className="user-center-summary-label">{t('userCenter.remaining_days')}</span>
                <strong className="user-center-summary-value">{getRemainingDays(userProfile, t, profileHydrating)}</strong>
              </section>
            </div>

            <div className="user-center-detail-grid">
              <section className="user-center-card user-center-detail-card">
                <div className="user-center-section-head">
                  <h3>{t('userCenter.profile_section')}</h3>
                  <button type="button" className="user-center-link-btn" onClick={init}>
                    {t('userCenter.refresh')}
                  </button>
                </div>

                <div className="user-center-kv-list">
                  <div className="user-center-kv-row">
                    <span>{t('userCenter.nickname')}</span>
                    <strong>{userInfo?.nickname || userInfo?.username || '--'}</strong>
                  </div>
                  <div className="user-center-kv-row">
                    <span>{t('userCenter.user_id')}</span>
                    <strong>{userProfile?.profile_id || userInfo?.profile_id || userProfile?.user_id || userInfo?.user_id || '--'}</strong>
                  </div>
                  <div className="user-center-kv-row">
                    <span>{t('userCenter.phone_label')}</span>
                    <strong>{phoneValue}</strong>
                  </div>
                  <div className="user-center-kv-row">
                    <span>{t('userCenter.current_tool')}</span>
                    <strong>{t('header.app_title')}</strong>
                  </div>
                </div>
              </section>

              <section className="user-center-card user-center-detail-card">
                <div className="user-center-section-head">
                  <h3>{t('userCenter.membership_section')}</h3>
                  <button
                    type="button"
                    className="user-center-link-btn"
                    onClick={handleMembershipRedirect}
                    onMouseEnter={() => { void resolvePaymentIntent().catch(() => null); }}
                    onFocus={() => { void resolvePaymentIntent().catch(() => null); }}
                    onPointerDown={() => { void resolvePaymentIntent().catch(() => null); }}
                  >
                    {userProfile?.is_vip ? t('userCenter.renew_membership') : t('userCenter.activate_now')}
                  </button>
                </div>

                <div className="user-center-kv-list">
                  <div className="user-center-kv-row">
                    <span>{t('userCenter.status_label')}</span>
                    <strong className="user-center-status-badge">{membershipStatus}</strong>
                  </div>
                  <div className="user-center-kv-row">
                    <span>{t('userCenter.vip_level')}</span>
                    <strong>{getVipLevelLabel(userProfile, t, profileHydrating)}</strong>
                  </div>
                  <div className="user-center-kv-row">
                    <span>{t('userCenter.trial_start_time')}</span>
                    <strong>{profileHydrating || userProfile?.is_vip ? '--' : formatDateTime(userProfile?.trial_started_at)}</strong>
                  </div>
                  <div className="user-center-kv-row">
                    <span>{t('userCenter.trial_expire_time')}</span>
                    <strong>{profileHydrating || userProfile?.is_vip ? '--' : formatDateTime(userProfile?.trial_expire_time)}</strong>
                  </div>
                  <div className="user-center-kv-row">
                    <span>{t('userCenter.vip_expire_time')}</span>
                    <strong>{getVipExpireLabel(userProfile, t, profileHydrating)}</strong>
                  </div>
                </div>
              </section>
            </div>

            <section className="user-center-card user-center-record-card">
              <div className="user-center-section-head">
                <h3>{t('userCenter.recent_records')}</h3>
                <button type="button" className="user-center-link-btn">
                  {t('userCenter.view_all_records')}
                </button>
              </div>

              {recentRecords?.length ? (
                <div className="user-center-record-table-wrap">
                  <div className="user-center-record-table">
                    <div className="user-center-record-head">
                      <div>{t('userCenter.record_file_name')}</div>
                      <div>{t('userCenter.record_conversion')}</div>
                      <div>{t('userCenter.record_status')}</div>
                      <div>{t('userCenter.record_completed_at')}</div>
                    </div>
                    <div className="user-center-record-body">
                      {recentRecords.map((record) => {
                        const fileName = record.fileName || t('userCenter.record_file_fallback');
                        const sourceFormat = record.sourceFormat || t('userCenter.record_format_fallback');
                        const targetFormat = record.targetFormat || t('userCenter.record_format_fallback');
                        const displayTime = record.completedAt || record.createdAt || t('userCenter.record_time_fallback');

                        return (
                          <div className="user-center-record-row" key={record.id}>
                            <div className="user-center-record-col">
                              <span className="user-center-record-label">{t('userCenter.record_file_name')}</span>
                              <strong>{fileName}</strong>
                            </div>
                            <div className="user-center-record-col">
                              <span className="user-center-record-label">{t('userCenter.record_conversion')}</span>
                              <span>{sourceFormat} {'->'} {targetFormat}</span>
                            </div>
                            <div className="user-center-record-col">
                              <span className="user-center-record-label">{t('userCenter.record_status')}</span>
                              <span className={`user-center-record-status is-${String(record.status || '').toLowerCase()}`}>
                                {formatRecordStatus(record.status, t)}
                              </span>
                            </div>
                            <div className="user-center-record-col">
                              <span className="user-center-record-label">{t('userCenter.record_completed_at')}</span>
                              <span>{displayTime}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="user-center-empty-block">
                  <p className="user-center-empty-title">{t('userCenter.no_records')}</p>
                  <p className="user-center-empty">{t('userCenter.no_records_hint')}</p>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}

export default UserCenterPage;
