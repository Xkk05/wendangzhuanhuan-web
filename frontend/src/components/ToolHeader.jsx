import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { Avatar, Select } from 'antd';
import { UserOutlined, LoadingOutlined, GlobalOutlined } from '@ant-design/icons';
import { persistCurrentToolSnapshot } from '../utils/authStorage';
import { useUserStore } from '../stores/useUserStore';
import { LANGUAGE_OPTIONS } from '../constants/languages';
import '../styles/LoginModal.css';
import '../App.css';

function ToolHeader({ onHomeClick, activeSection }) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { isLoggedIn, userInfo, isPolling, openUserCenter, init } = useUserStore();
  const { theme, toggleTheme } = useTheme();
  const [appVersion, setAppVersion] = useState('v1.0.0');

  const languages = LANGUAGE_OPTIONS;

  const handleLanguageChange = (value) => {
    i18n.changeLanguage(value);
  };

  const currentPath = `${location.pathname}${location.search}${location.hash}`;

  const handleOpenUserCenter = () => {
    persistCurrentToolSnapshot(currentPath);
    openUserCenter(navigate, currentPath);
  };

  useEffect(() => {
    init();
    // 获取真实版本号
    const fetchVersion = async () => {
      if (window.electronAPI && window.electronAPI.getVersion) {
        try {
          const version = await window.electronAPI.getVersion();
          if (version) {
            setAppVersion(`v${version}`);
          }
        } catch (err) {
          console.error('Failed to get version:', err);
        }
      }
    };
    fetchVersion();
  }, [init]);

  const renderUserArea = () => {
    if (isLoggedIn && userInfo) {
      return (
        <div
          className="user-profile-trigger"
          onClick={handleOpenUserCenter}
        >
          <Avatar size={24} src={userInfo.avatar} icon={<UserOutlined />} />
          <span className="user-nickname">{userInfo.nickname}</span>
        </div>
      );
    }

    if (isPolling) {
      return (
        <button className="user-btn user-btn-polling" onClick={handleOpenUserCenter}>
          <LoadingOutlined spin />
          <span>{t('header.logging_in')}</span>
        </button>
      );
    }

    return (
      <button className="user-btn" onClick={handleOpenUserCenter}>
        {t('header.login')}
      </button>
    );
  };

  // 窗口控制逻辑
  const handleMin = () => {
    if (window.electronAPI) {
      window.electronAPI.windowMinimize();
    }
  };

  const handleMax = () => {
    if (window.electronAPI) {
      window.electronAPI.windowMaximize();
    }
  };

  const handleClose = () => {
    if (window.electronAPI) {
      window.electronAPI.windowClose();
    }
  };

  return (
    <nav className="top-nav">
      <div className="nav-left">
        <div className="nav-logo-wrapper">
          <img src="app.ico" alt="Logo" className="nav-app-icon" />
          <div className="nav-app-info">
            <div className="nav-app-title-wrapper">
              <div className="nav-app-title">{t('header.app_title')}</div>
              <span className="nav-app-version">{appVersion}</span>
            </div>
            <div className="nav-app-subtitle">{t('header.app_subtitle')}</div>
          </div>
        </div>
        
        {/* 我的主页按钮 */}
        <button 
          className={`nav-home-btn ${activeSection === '我的主页' || activeSection === t('header.home') ? 'active' : ''}`}
          onClick={onHomeClick}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: (activeSection === '我的主页' || activeSection === t('header.home')) ? 'var(--primary-color)' : 'transparent',
            color: (activeSection === '我的主页' || activeSection === t('header.home')) ? '#fff' : 'var(--text-secondary)',
            border: 'none',
            padding: '6px 14px',
            borderRadius: '18px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '500',
            transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
            marginLeft: '20px',
            boxShadow: (activeSection === '我的主页' || activeSection === t('header.home')) ? '0 4px 12px rgba(0, 163, 255, 0.2)' : 'none',
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            <polyline points="9 22 9 12 15 12 15 22"></polyline>
          </svg>
          {t('header.home')}
        </button>
      </div>

      <div className="nav-right">
        <div className="user-btn-container">
          {renderUserArea()}
        </div>

        {/* Language Select */}
        <div className="language-selector" style={{ display: 'flex', alignItems: 'center', margin: '0 8px' }}>
          <Select
            value={i18n.language}
            onChange={handleLanguageChange}
            options={languages}
            variant="borderless"
            popupMatchSelectWidth={false}
            suffixIcon={<GlobalOutlined style={{ fontSize: '16px', color: 'var(--text-secondary)' }} />}
            style={{ 
              width: 'auto',
              minWidth: '80px',
              fontSize: '13px'
            }}
            styles={{
              popup: {
                root: {
                  borderRadius: '12px',
                  padding: '4px',
                  boxShadow: 'var(--shadow-lg)'
                }
              }
            }}
          />
        </div>

        {/* Theme Toggle */}
        <button
          className="window-control-btn"
          onClick={toggleTheme}
          title={theme === 'light' ? '切换深色模式' : '切换浅色模式'}
        >
          {theme === 'light' ? (
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
          ) : (
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="5"></circle>
              <line x1="12" y1="1" x2="12" y2="3"></line>
              <line x1="12" y1="21" x2="12" y2="23"></line>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
              <line x1="1" y1="12" x2="3" y2="12"></line>
              <line x1="21" y1="12" x2="23" y2="12"></line>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            </svg>
          )}
        </button>

        {/* 窗口控制器 */}
        <div className="window-controls">
          <button className="window-control-btn" onClick={handleMin} title="最小化">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
          <button className="window-control-btn" onClick={handleMax} title="最大化/还原">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="5" y="5" width="14" height="14" rx="2" ry="2"></rect>
            </svg>
          </button>
          <button className="window-control-btn close-btn" onClick={handleClose} title="关闭">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>
    </nav>
  );
}

export default ToolHeader;
