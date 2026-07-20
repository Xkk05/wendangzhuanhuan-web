const PROD_OAUTH_CALLBACK_URL = import.meta?.env?.VITE_OAUTH_CALLBACK_URL || '';
const DEV_OAUTH_CALLBACK_ORIGIN = 'http://localhost:5176';
const DEV_OAUTH_CLIENT_ID = 'app_971b24a9955eae3b';
const PROD_OAUTH_CLIENT_ID = 'app_d2765ab4687d35dd';
const OAUTH_AUTHORIZE_URL = 'https://login.kunqiongai.com/authorize.html';
const OAUTH_LOGIN_URL = 'https://login.kunqiongai.com/login.html';
const OAUTH_SCOPE = 'basic';

function isLoopbackHost(hostname) {
  return hostname === 'localhost' || hostname === '127.0.0.1';
}

export function normalizeLocalOAuthOrigin() {
  if (typeof window === 'undefined' || window.electronAPI) {
    return false;
  }

  const { protocol, hostname, port } = window.location;
  if (protocol !== 'http:' || hostname !== '127.0.0.1' || port !== '5176') {
    return false;
  }

  const normalizedUrl = new URL(window.location.href);
  normalizedUrl.hostname = 'localhost';
  window.location.replace(normalizedUrl.toString());
  return true;
}

export function resolveOAuthRedirectUri() {
  if (typeof window === 'undefined') {
    return `${DEV_OAUTH_CALLBACK_ORIGIN}/oauth/callback`;
  }

  const { origin, hostname } = window.location;
  if (isLoopbackHost(hostname)) {
    return `${DEV_OAUTH_CALLBACK_ORIGIN}/oauth/callback`;
  }

  if (window.electronAPI) {
    return `${origin}/oauth/callback`;
  }

  return PROD_OAUTH_CALLBACK_URL || `${origin}/oauth/callback`;
}

export function createOAuthState() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '');
  }

  return `${Date.now()}${Math.random().toString(16).slice(2)}`;
}

export function resolveOAuthClientId() {
  if (typeof window === 'undefined') {
    return DEV_OAUTH_CLIENT_ID;
  }

  const { hostname } = window.location;
  const isLocalHost = hostname === 'localhost' || hostname === '127.0.0.1';
  return isLocalHost ? DEV_OAUTH_CLIENT_ID : PROD_OAUTH_CLIENT_ID;
}

export function buildOAuthAuthorizeUrl({ state, redirectUri }) {
  const url = new URL(OAUTH_AUTHORIZE_URL);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('client_id', resolveOAuthClientId());
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('state', state);
  url.searchParams.set('scope', OAUTH_SCOPE);
  return url.toString();
}

export function buildOAuthLoginUrl({ state, redirectUri }) {
  const authorizeUrl = buildOAuthAuthorizeUrl({ state, redirectUri });
  const loginUrl = new URL(OAUTH_LOGIN_URL);
  loginUrl.searchParams.set('redirect', authorizeUrl);
  loginUrl.searchParams.set('returnUrl', authorizeUrl);
  return {
    loginUrl: loginUrl.toString(),
    authorizeUrl,
    clientId: resolveOAuthClientId(),
  };
}
