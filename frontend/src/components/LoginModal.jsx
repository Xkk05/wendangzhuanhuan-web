import { useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useUserStore } from '../stores/useUserStore';
import { resolveOAuthRedirectUri } from '../utils/oauthConfig';

function LoginModal() {
  const { t } = useTranslation();
  const isVisible = useUserStore((s) => s.isLoginModalVisible);
  const isPolling = useUserStore((s) => s.isPolling);
  const pendingReturnTo = useUserStore((s) => s.pendingReturnTo);
  const startLoginProcess = useUserStore((s) => s.startLoginProcess);
  const cancelLoginProcess = useUserStore((s) => s.cancelLoginProcess);
  const hideLoginModal = useUserStore((s) => s.hideLoginModal);
  const handleOAuthCallback = useUserStore((s) => s.handleOAuthCallback);
  const pollTimerRef = useRef(null);

  const handleLogin = async () => {
    try {
      await startLoginProcess({ returnTo: pendingReturnTo });
    } catch {
      // Login process handles its own errors
    }
  };

  const handleCancel = () => {
    if (isPolling) {
      cancelLoginProcess();
    }
    hideLoginModal();
  };

  // 轮询弹窗登录结果
  const pollForCompletion = useCallback(() => {
    const raw = (() => {
      try { return localStorage.getItem('kq_login_popup_result'); } catch { return null; }
    })();
    if (!raw) return;

    try { localStorage.removeItem('kq_login_popup_result'); } catch { /* ignore */ }

    try {
      const data = JSON.parse(raw);
      if (!data?.success || !data?.code) return;

      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }

      // 主窗口 store 完成 token 交换
      handleOAuthCallback({
        code: data.code,
        state: data.state,
        redirectUri: resolveOAuthRedirectUri(),
      })
        .then(() => {
          const storeState = useUserStore.getState();
          if (storeState.isLoggedIn) {
            storeState.hideLoginModal();
          }
        })
        .catch(() => {
          useUserStore.getState().hideLoginModal();
        });
    } catch {
      // 数据格式错误
    }
  }, [handleOAuthCallback]);

  useEffect(() => {
    if (isVisible && isPolling) {
      pollTimerRef.current = setInterval(pollForCompletion, 1500);
    }
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [isVisible, isPolling, pollForCompletion]);

  if (!isVisible) return null;

  return (
    <div className="modal-overlay" onClick={handleCancel}>
      <div className="login-modal" onClick={(e) => e.stopPropagation()}>
        <div className="login-modal-header">
          <h2>{t('loginModal.title', '登录')}</h2>
          <button className="modal-close-btn" onClick={handleCancel}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {isPolling ? (
          <div className="login-modal-body">
            <div className="login-modal-spinner" />
            <p className="login-modal-message">
              {t('loginModal.waiting_login', '请在新窗口中完成登录...')}
            </p>
            <button className="login-modal-cancel" onClick={handleCancel}>
              {t('loginModal.cancel_login', '取消登录')}
            </button>
          </div>
        ) : (
          <div className="login-modal-body">
            <div className="login-modal-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
            <p className="login-modal-message">
              {t('loginModal.message', '请先登录账号，即可使用所有转换功能')}
            </p>
            <button className="login-modal-btn" onClick={handleLogin}>
              {t('loginModal.loginButton', '登录鲲穹账号')}
            </button>
            <button className="login-modal-cancel" onClick={handleCancel}>
              {t('loginModal.cancel', '稍后再说')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default LoginModal;
