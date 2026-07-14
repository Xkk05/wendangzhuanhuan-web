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
