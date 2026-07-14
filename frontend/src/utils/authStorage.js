const AUTH_STORAGE_KEY = 'user-storage';
const OAUTH_STATE_KEY = 'kunqiong_oauth_state';
const OAUTH_RETURN_TO_KEY = 'kunqiong_oauth_return_to';
const PAYMENT_RESUME_KEY = 'kunqiong_payment_resume';
const PAYMENT_SYNC_KEY = 'kunqiong_payment_sync';
const PAYMENT_RETURN_EVENT_KEY = 'kq_membership_payment_return';
const PAYMENT_RESUME_CHECKOUT_KEY = 'kunqiong_payment_resume_checkout';
const PAYMENT_INTENT_CACHE_KEY = 'kunqiong_payment_intent_cache';
const CURRENT_TOOL_NAME_KEY = 'lastCurrentToolName';
const CURRENT_TOOL_PATH_KEY = 'lastCurrentToolPath';

export function readPersistedAuthState() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed?.state || parsed || {};
  } catch {
    return {};
  }
}

export function getPersistedToken() {
  return readPersistedAuthState().token || null;
}

export function getApiWebToken() {
  try {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'api_web_token' || name === 'kq_token') {
        return decodeURIComponent(value);
      }
    }
  } catch {
    // ignore
  }
  return localStorage.getItem('kq_api_web_token') || null;
}

export function storeOAuthRequest({ state, returnTo }) {
  if (state) {
    sessionStorage.setItem(OAUTH_STATE_KEY, state);
  }
  if (returnTo) {
    sessionStorage.setItem(OAUTH_RETURN_TO_KEY, returnTo);
  }
}

export function readOAuthState() {
  return sessionStorage.getItem(OAUTH_STATE_KEY);
}

export function readOAuthReturnTo() {
  return sessionStorage.getItem(OAUTH_RETURN_TO_KEY);
}

export function clearOAuthRequest() {
  sessionStorage.removeItem(OAUTH_STATE_KEY);
  sessionStorage.removeItem(OAUTH_RETURN_TO_KEY);
}

export function storePaymentResumeTarget(targetUrl) {
  if (targetUrl) {
    sessionStorage.setItem(PAYMENT_RESUME_KEY, targetUrl);
  }
}

export function readPaymentResumeTarget() {
  return sessionStorage.getItem(PAYMENT_RESUME_KEY);
}

export function clearPaymentResumeTarget() {
  sessionStorage.removeItem(PAYMENT_RESUME_KEY);
}

export function markPaymentResumeCheckoutPending() {
  sessionStorage.setItem(PAYMENT_RESUME_CHECKOUT_KEY, '1');
}

export function hasPaymentResumeCheckoutPending() {
  return sessionStorage.getItem(PAYMENT_RESUME_CHECKOUT_KEY) === '1';
}

export function clearPaymentResumeCheckoutPending() {
  sessionStorage.removeItem(PAYMENT_RESUME_CHECKOUT_KEY);
}

export function storePendingMembershipSync(payload = {}) {
  try {
    localStorage.setItem(PAYMENT_SYNC_KEY, JSON.stringify({
      returnTo: payload.returnTo || '',
      expireAt: payload.expireAt || '',
      active: Boolean(payload.active),
      startedAt: Date.now(),
    }));
  } catch {
    // ignore storage failures
  }
}

export function readPendingMembershipSync() {
  try {
    const raw = localStorage.getItem(PAYMENT_SYNC_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      return null;
    }
    return {
      returnTo: parsed.returnTo || '',
      expireAt: parsed.expireAt || '',
      active: Boolean(parsed.active),
      startedAt: Number(parsed.startedAt || 0),
    };
  } catch {
    return null;
  }
}

export function clearPendingMembershipSync() {
  localStorage.removeItem(PAYMENT_SYNC_KEY);
}

export function storePaymentIntentCache(payload = {}) {
  try {
    sessionStorage.setItem(PAYMENT_INTENT_CACHE_KEY, JSON.stringify({
      route: payload.route || '',
      fetchedAt: Number(payload.fetchedAt || Date.now()),
      data: payload.data || null,
    }));
  } catch {
    // ignore storage failures
  }
}

export function readPaymentIntentCache() {
  try {
    const raw = sessionStorage.getItem(PAYMENT_INTENT_CACHE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') {
      return null;
    }
    return {
      route: parsed.route || '',
      fetchedAt: Number(parsed.fetchedAt || 0),
      data: parsed.data || null,
    };
  } catch {
    return null;
  }
}

export function clearPaymentIntentCache() {
  sessionStorage.removeItem(PAYMENT_INTENT_CACHE_KEY);
}

export function storePaymentReturnEvent(payload = {}) {
  try {
    localStorage.setItem(PAYMENT_RETURN_EVENT_KEY, JSON.stringify({
      type: 'KQ_MEMBERSHIP_PAYMENT_RETURN',
      targetUrl: payload.targetUrl || '',
      ts: Date.now(),
    }));
  } catch {
    // ignore storage failures
  }
}

export function readPaymentReturnEvent() {
  try {
    const raw = localStorage.getItem(PAYMENT_RETURN_EVENT_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || parsed.type !== 'KQ_MEMBERSHIP_PAYMENT_RETURN') {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function clearPaymentReturnEvent() {
  localStorage.removeItem(PAYMENT_RETURN_EVENT_KEY);
}

export function sanitizeReturnTo(value) {
  if (!value || typeof value !== 'string') {
    return '/';
  }

  if (value.startsWith('/') && !value.startsWith('//')) {
    return value;
  }

  try {
    const url = new URL(value, window.location.origin);
    if (url.origin === window.location.origin) {
      return `${url.pathname}${url.search}${url.hash}`;
    }
  } catch {
    return '/';
  }

  return '/';
}

export function formatToolNameFromPath(pathname) {
  if (!pathname || typeof pathname !== 'string') {
    return '';
  }

  const match = pathname.match(/^\/tool\/([^/]+)\/([^/?#]+)/i);
  if (!match) {
    return '';
  }

  return `${match[1].toUpperCase()} To ${match[2].toUpperCase()}`;
}

export function persistCurrentToolSnapshot(pathname, explicitName) {
  try {
    const safePath = sanitizeReturnTo(pathname);
    const toolName = explicitName || formatToolNameFromPath(safePath);
    if (!toolName) {
      return;
    }

    localStorage.setItem(CURRENT_TOOL_NAME_KEY, toolName);
    localStorage.setItem(CURRENT_TOOL_PATH_KEY, safePath);
  } catch {
    // ignore storage failures
  }
}

export function readCurrentToolSnapshot() {
  try {
    const storedToolName = localStorage.getItem(CURRENT_TOOL_NAME_KEY);
    const storedToolPath = localStorage.getItem(CURRENT_TOOL_PATH_KEY);
    return {
      name: storedToolName || '',
      path: storedToolPath || '',
    };
  } catch {
    return { name: '', path: '' };
  }
}
