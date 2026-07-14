import axios from 'axios';
import { getApiBaseUrl } from './api';

function buildAuthHeaders(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const AuthService = {
  async getLoginUrl({ redirectUri, state } = {}) {
    const apiBaseUrl = await getApiBaseUrl();
    const res = await axios.post(`${apiBaseUrl}/api/auth/login-url`, {
      redirect_uri: redirectUri,
      state,
    });
    return res.data;
  },

  async exchangeOAuthCode({ code, state, redirectUri }) {
    const apiBaseUrl = await getApiBaseUrl();
    const res = await axios.post(`${apiBaseUrl}/api/auth/oauth-exchange`, {
      code,
      state,
      redirectUri,
    });
    return res.data;
  },

  async checkLogin(token) {
    const apiBaseUrl = await getApiBaseUrl();
    const res = await axios.get(`${apiBaseUrl}/api/auth/check-login`, {
      headers: buildAuthHeaders(token),
    });
    return Boolean(res.data?.data?.logged_in);
  },

  async getUserInfo(token) {
    const apiBaseUrl = await getApiBaseUrl();
    const res = await axios.get(`${apiBaseUrl}/api/auth/user-info`, {
      headers: buildAuthHeaders(token),
    });
    return res.data?.data || null;
  },

  async getUserProfile(token) {
    const apiBaseUrl = await getApiBaseUrl();
    const res = await axios.get(`${apiBaseUrl}/api/auth/user-profile`, {
      headers: buildAuthHeaders(token),
    });
    return res.data?.data || null;
  },

  async getRecentRecords(token, limit = 10) {
    const apiBaseUrl = await getApiBaseUrl();
    const res = await axios.get(`${apiBaseUrl}/api/user-center/recent-records`, {
      headers: buildAuthHeaders(token),
      params: { limit },
    });
    return res.data?.data || [];
  },

  async logout(token) {
    const apiBaseUrl = await getApiBaseUrl();
    const res = await axios.post(
      `${apiBaseUrl}/api/auth/logout`,
      {},
      {
        headers: buildAuthHeaders(token),
      }
    );
    return res.data;
  },

  async getMembershipInfo(token) {
    const apiBaseUrl = await getApiBaseUrl();
    const res = await axios.post(
      `${apiBaseUrl}/api/user-center/member-package-info`,
      {},
      { headers: buildAuthHeaders(token) }
    );
    return res.data?.data || null;
  },

  async getWebMemberPackageInfo(token, options = {}) {
    const apiBaseUrl = await getApiBaseUrl();
    const body = new URLSearchParams();
    if (options.forceSync) {
      body.set('force_sync', 'true');
    }
    if (options.previousExpireAt) {
      body.set('previous_expire_at', String(options.previousExpireAt));
    }
    if (typeof options.previousActive === 'boolean') {
      body.set('previous_active', String(options.previousActive));
    }
    const res = await axios.post(
      `${apiBaseUrl}/api/user-center/member-package-info`,
      body,
      {
        headers: {
          ...buildAuthHeaders(token),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    );
    return res.data || null;
  },

  async createWebMemberOrder(token, { packageId, payType }) {
    const apiBaseUrl = await getApiBaseUrl();
    const body = new URLSearchParams();
    body.set('package_id', String(packageId));
    body.set('pay_type', String(payType));
    const res = await axios.post(`${apiBaseUrl}/api/user-center/create-member-order`, body, {
      headers: {
        ...buildAuthHeaders(token),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return res.data || null;
  },

  async getMembershipPaymentPageUrl(token, returnUrl) {
    const apiBaseUrl = await getApiBaseUrl();
    const res = await axios.get(`${apiBaseUrl}/api/user-center/payment-page-url`, {
      headers: buildAuthHeaders(token),
      params: returnUrl ? { return_url: returnUrl } : {},
    });
    return res.data?.data || null;
  },

  async checkWebMemberOrderPaystatus(token, orderNo) {
    const apiBaseUrl = await getApiBaseUrl();
    const body = new URLSearchParams();
    body.set('order_no', String(orderNo));
    const res = await axios.post(`${apiBaseUrl}/api/user-center/check-member-order-paystatus`, body, {
      headers: {
        ...buildAuthHeaders(token),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return res.data || null;
  },
};
