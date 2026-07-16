import { useEffect, useRef } from 'react';
import { App } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { sanitizeReturnTo } from '../utils/authStorage';
import { resolveOAuthRedirectUri } from '../utils/oauthConfig';
import { useUserStore } from '../stores/useUserStore';
import LoadingPage from '../components/LoadingPage';

function OAuthCallbackPage() {
  const { message } = App.useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const handledRef = useRef(false);
  const handleOAuthCallback = useUserStore((state) => state.handleOAuthCallback);

  useEffect(() => {
    if (handledRef.current) return;
    handledRef.current = true;

    const params = new URLSearchParams(location.search);
    const code = params.get('code');
    const state = params.get('state');

    // 弹窗模式：startLoginProcess 在 localStorage 设置了 kq_login_mode = 'popup'
    // 弹窗内只传 code+state 回主窗口，让主窗口 store 完成 token 交换
    const loginMode = (() => {
      try { return localStorage.getItem('kq_login_mode'); } catch { return null; }
    })();
    if (loginMode === 'popup') {
      try { localStorage.removeItem('kq_login_mode'); } catch { /* ignore */ }

      if (!code) {
        try {
          localStorage.setItem(
            'kq_login_popup_result',
            JSON.stringify({ success: false, error: 'Missing OAuth code', ts: Date.now() })
          );
        } catch { /* ignore */ }
        window.close();
        return;
      }
      try {
        localStorage.setItem(
          'kq_login_popup_result',
          JSON.stringify({ success: true, code, state, ts: Date.now() })
        );
      } catch { /* ignore */ }
      window.close();
      return;
    }

    // 主窗口模式（直接回调）
    handleOAuthCallback({
      code,
      state,
      redirectUri: resolveOAuthRedirectUri(),
    })
      .then((returnTo) => {
        if (returnTo === '__external_payment_redirect__') {
          return;
        }
        const safeReturnTo = sanitizeReturnTo(returnTo);
        navigate(safeReturnTo || '/', { replace: true });
      })
      .catch((callbackError) => {
        message.error(callbackError?.message || '登录失败，请重试');
        navigate('/account', { replace: true });
      });
  }, [handleOAuthCallback, location.search, navigate, message]);

  return <LoadingPage />;
}

export default OAuthCallbackPage;
