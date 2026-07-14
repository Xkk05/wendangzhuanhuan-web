import { useEffect, useRef } from 'react';
import { BrowserRouter, HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ConfigProvider, theme as antTheme, App as AntApp } from 'antd';
import MainPage from './pages/MainPage';
import OAuthCallbackPage from './pages/OAuthCallbackPage';
import UserCenterPage from './pages/UserCenterPage';
import MembershipUpgradeModal from './components/MembershipUpgradeModal';
import { useThemeStore } from './stores/useThemeStore';
import { useUserStore } from './stores/useUserStore';
import {
  clearPendingMembershipSync,
  clearPaymentReturnEvent,
  readPendingMembershipSync,
  readPaymentReturnEvent,
} from './utils/authStorage';
import './App.css';

function App() {
  const theme = useThemeStore((state) => state.theme);
  const isLoggedIn = useUserStore((state) => state.isLoggedIn);
  const isDark = theme === 'dark';
  const isElectron = typeof window !== 'undefined' && Boolean(window.electronAPI);
  const Router = isElectron ? HashRouter : BrowserRouter;
  const paymentPollingRef = useRef(null);
  const paymentSyncInFlightRef = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !isLoggedIn) {
      if (paymentPollingRef.current) {
        window.clearInterval(paymentPollingRef.current);
        paymentPollingRef.current = null;
      }
      return undefined;
    }

    const stopPolling = () => {
      if (paymentPollingRef.current) {
        window.clearInterval(paymentPollingRef.current);
        paymentPollingRef.current = null;
      }
    };

    const startMembershipSync = () => {
      const pendingSync = readPendingMembershipSync();
      if (!pendingSync) {
        stopPolling();
        return;
      }

      const runSync = async () => {
        if (paymentSyncInFlightRef.current) {
          return;
        }
        paymentSyncInFlightRef.current = true;
        const latestPending = readPendingMembershipSync();
        if (!latestPending) {
          paymentSyncInFlightRef.current = false;
          stopPolling();
          return;
        }

        if (latestPending.startedAt && Date.now() - latestPending.startedAt > 10 * 60 * 1000) {
          clearPendingMembershipSync();
          clearPaymentReturnEvent();
          paymentSyncInFlightRef.current = false;
          stopPolling();
          return;
        }

        try {
          const profile = await useUserStore.getState().refreshMembershipStatus({
            forceMembershipSync: true,
            previousExpireAt: latestPending.expireAt || '',
            previousActive: latestPending.active,
          });

          const nextExpireAt = profile?.web_member_expire_at || profile?.vip_expire_time || '';
          const nextActive = Boolean(profile?.is_vip || profile?.web_member_active);
          const changed = latestPending.active
            ? Boolean(nextExpireAt) && nextExpireAt !== latestPending.expireAt
            : nextActive || (nextExpireAt && nextExpireAt !== latestPending.expireAt);

          if (changed) {
            void useUserStore.getState().refreshProfile({ skipWebMember: true });
            clearPendingMembershipSync();
            clearPaymentReturnEvent();
            stopPolling();
          }
        } finally {
          paymentSyncInFlightRef.current = false;
        }
      };

      void runSync();
      if (!paymentPollingRef.current) {
        paymentPollingRef.current = window.setInterval(runSync, 1500);
      }
    };

    const handlePaymentReturnMessage = (event) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== 'KQ_MEMBERSHIP_PAYMENT_RETURN') return;
      startMembershipSync();
    };

    const handlePaymentReturnStorage = (event) => {
      if (event.key !== 'kq_membership_payment_return' || !event.newValue) return;
      startMembershipSync();
    };

    const handleWindowFocus = () => {
      if (readPendingMembershipSync()) {
        startMembershipSync();
      }
    };

    if (readPendingMembershipSync() || readPaymentReturnEvent()) {
      startMembershipSync();
    }

    window.addEventListener('message', handlePaymentReturnMessage);
    window.addEventListener('storage', handlePaymentReturnStorage);
    window.addEventListener('focus', handleWindowFocus);

    return () => {
      window.removeEventListener('message', handlePaymentReturnMessage);
      window.removeEventListener('storage', handlePaymentReturnStorage);
      window.removeEventListener('focus', handleWindowFocus);
      stopPolling();
    };
  }, [isLoggedIn]);

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
        token: {
          colorPrimary: isDark ? '#60a5fa' : '#2563eb',
          colorBgContainer: isDark ? '#1e293b' : '#ffffff',
          colorBgElevated: isDark ? '#1e293b' : '#ffffff',
          colorText: isDark ? '#f1f5f9' : '#1e293b',
          colorTextSecondary: isDark ? '#94a3b8' : '#64748b',
          borderRadius: 8,
        },
        components: {
          Modal: {
            contentBg: isDark ? '#1e293b' : '#ffffff',
            headerBg: isDark ? '#1e293b' : '#ffffff',
          }
        }
      }}
    >
      <AntApp>
        <Router>
          <Toaster
            position="top-right"
            containerStyle={{
              top: 70,
            }}
            toastOptions={{
              duration: 3000,
              style: {
                background: 'var(--card-bg)',
                color: 'var(--text-primary)',
                boxShadow: 'var(--shadow-md)',
                borderRadius: '8px',
                padding: '10px 14px',
                fontSize: '14px',
                fontWeight: '500',
                minHeight: '48px',
              },
              success: {
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 4000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
          <MembershipUpgradeModal />
          <Routes>
            <Route path="/" element={<MainPage isElectron={isElectron} />} />
            <Route path="/account" element={<UserCenterPage />} />
            <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
            <Route path="/tools/:category" element={<MainPage isElectron={isElectron} />} />
            <Route path="/tool/:source/:target" element={<MainPage isElectron={isElectron} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </AntApp>
    </ConfigProvider>
  );
}

export default App;
