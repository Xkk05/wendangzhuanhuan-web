import { DownOutlined, MenuOutlined, SearchOutlined } from '@ant-design/icons';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  persistCurrentToolSnapshot,
} from '../utils/authStorage';
import { useUserStore } from '../stores/useUserStore';
import './WebShell.css';

const SITE_ORIGIN = 'https://www.kunqiongai.com';

function WebHeader() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { isLoggedIn, userInfo, isPolling, openUserCenter, startLoginProcess, init, prewarmMembershipPaymentIntent } = useUserStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [showMobileSearch, setShowMobileSearch] = useState(false);
  const mobileSearchInputRef = useRef(null);
  const paymentIntentPrewarmRef = useRef({ route: '', promise: null });

  useEffect(() => {
    init();
  }, [init]);

  useEffect(() => {
    if (showMobileSearch) {
      mobileSearchInputRef.current?.focus();
    }
  }, [showMobileSearch]);

  const isCompactNavLanguage = i18n.language !== 'zh_CN' && i18n.language !== 'zh_TW';
  const currentPath = `${location.pathname}${location.search}${location.hash}`;
  const activeNavKey = useMemo(() => {
    const pathname = location.pathname || '/';
    if (
      pathname === '/' ||
      pathname.includes('/tools/docx') ||
      pathname.includes('/tools/html') ||
      pathname.includes('/tools/pdf') ||
      pathname.includes('/tools/excel') ||
      pathname.includes('/tools/txt') ||
      pathname.includes('/tools/xml') ||
      pathname.includes('/tools/json')
    ) {
      return 'web';
    }
    return 'web';
  }, [location.pathname]);

  const navItems = [
    { key: 'home', label: t('webHeader.nav.home', 'Home'), href: `${SITE_ORIGIN}/` },
    { key: 'ai', label: t('webHeader.nav.ai_tools', 'AI Tools'), href: `${SITE_ORIGIN}/category/ai` },
    {
      key: 'aiapps',
      label: t('webHeader.nav.ai_smart_apps', 'AI Smart Apps'),
      href: 'https://aiapps.kunqiongai.com/',
    },
    {
      key: 'web',
      label: t('webHeader.nav.web_tools', 'Web Tools'),
      href: `${SITE_ORIGIN}/category/web`,
    },
    {
      key: 'office',
      label: t('webHeader.nav.office_tools', 'Office Tools'),
      href: `${SITE_ORIGIN}/category/office`,
    },
    {
      key: 'multimedia',
      label: t('webHeader.nav.multimedia', 'Multimedia'),
      href: `${SITE_ORIGIN}/category/multimedia`,
    },
    {
      key: 'development',
      label: t('webHeader.nav.development_tools', 'Development Tools'),
      href: `${SITE_ORIGIN}/category/development`,
    },
    {
      key: 'text',
      label: t('webHeader.nav.text_processing', 'Text Processing'),
      href: `${SITE_ORIGIN}/category/text`,
    },
    {
      key: 'file',
      label: t('webHeader.nav.file_processing', 'File Processing'),
      href: `${SITE_ORIGIN}/category/file`,
    },
    {
      key: 'more',
      label: t('webHeader.nav.more_tools', 'More Tools'),
      children: [
        {
          key: 'system',
          label: t('webHeader.nav.system_tools', 'System Tools'),
          href: `${SITE_ORIGIN}/category/system`,
        },
        {
          key: 'life',
          label: t('webHeader.nav.life_tools', 'Life Tools'),
          href: `${SITE_ORIGIN}/category/life`,
        },
      ],
    },
    {
      key: 'news',
      label: t('webHeader.nav.industry_news', 'AI News'),
      href: `${SITE_ORIGIN}/news`,
    },
    {
      key: 'custom',
      label: t('webHeader.nav.software_customization', 'Custom Software'),
      href: `${SITE_ORIGIN}/custom`,
    },
  ];

  const searchAria = t('webHeader.search_aria', 'Search');
  const searchPlaceholder = t('webHeader.search_placeholder', 'Search tools, apps, etc.');

  const submitSearch = (event) => {
    event.preventDefault();
    const keyword = searchQuery.trim();
    const targetUrl = keyword
      ? `${SITE_ORIGIN}/?s=${encodeURIComponent(keyword)}`
      : `${SITE_ORIGIN}/`;
    window.location.href = targetUrl;
  };

  const handleUserClick = () => {
    persistCurrentToolSnapshot(currentPath);
    openUserCenter(navigate, currentPath);
  };

  const prewarmPaymentIntent = async ({ force = false } = {}) => {
    if (!force && paymentIntentPrewarmRef.current.promise && paymentIntentPrewarmRef.current.route === currentPath) {
      return paymentIntentPrewarmRef.current.promise;
    }
    const promise = prewarmMembershipPaymentIntent(currentPath, { force })
      .then((data) => {
        paymentIntentPrewarmRef.current = { route: currentPath, promise: null };
        return data;
      })
      .catch((error) => {
        paymentIntentPrewarmRef.current = { route: currentPath, promise: null };
        throw error;
      });
    paymentIntentPrewarmRef.current = { route: currentPath, promise };
    return promise;
  };

  const handleLoginClick = () => {
    persistCurrentToolSnapshot(currentPath);
    void startLoginProcess({
      returnTo: currentPath,
    });
  };

  return (
    <header className="web-header web-header-home">
      <div className="web-header-container kq-header-container">
        <div className="web-header-left">
          <a href={`${SITE_ORIGIN}/`} className="web-logo-link kq-logo-link">
            <img
              src="/web-assets/logo.png"
              alt={t('webHeader.brand_title', 'KUNQIONG AI TOOLS')}
              className="web-logo-img kq-logo-img"
            />
          </a>
        </div>

        <nav
          className={`web-nav kq-nav ${isCompactNavLanguage ? 'kq-nav-compact' : 'kq-nav-default'}`}
          aria-label={t('webHeader.menu_aria', 'Primary navigation')}
        >
          <div className="web-nav-track kq-nav-track">
            {navItems.map((item) => (
              <div
                key={item.key}
                className={`web-nav-item-wrapper kq-nav-item-wrapper ${item.children ? 'kq-nav-item-dropdown' : ''}`}
              >
                {item.children ? (
                  <>
                    <button
                      type="button"
                      className="web-nav-link kq-nav-link kq-nav-trigger"
                    >
                      <span>{item.label}</span>
                      <DownOutlined className="kq-nav-trigger-arrow" />
                    </button>
                    <div className="kq-nav-dropdown-menu">
                      {item.children.map((child) => (
                        <a
                          key={child.key}
                          href={child.href}
                          className={`kq-nav-dropdown-link ${activeNavKey === child.key ? 'active' : ''}`}
                        >
                          {child.label}
                        </a>
                      ))}
                    </div>
                  </>
                ) : (
                  <a
                    href={item.href}
                    className={`web-nav-link kq-nav-link ${activeNavKey === item.key ? 'active' : ''}`}
                  >
                    {item.label}
                  </a>
                )}
              </div>
            ))}
          </div>
        </nav>

        <div className="web-header-right kq-header-right">
          <form className="web-search-box kq-search-box" onSubmit={submitSearch}>
            <button
              type="submit"
              className="web-search-submit kq-search-icon-btn"
              aria-label={searchAria}
            >
              <SearchOutlined />
            </button>
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              type="text"
              placeholder={searchPlaceholder}
            />
          </form>

          <div className="web-header-actions kq-header-actions">
            <button
              type="button"
              className="web-mobile-search-btn kq-header-search-btn"
              aria-label={searchAria}
              onClick={() => setShowMobileSearch((value) => !value)}
            >
              <img src="/web-assets/sousuo.png" alt={searchAria} className="kq-header-search-icon" />
            </button>
            <button
              type="button"
              className="web-mobile-menu-btn kq-mobile-menu-btn"
              aria-label={t('webHeader.menu_aria', 'Navigation menu')}
            >
              <MenuOutlined />
            </button>

            {isLoggedIn && userInfo ? (
              <button
                type="button"
                className="web-user-trigger kq-user-trigger"
                onClick={handleUserClick}
                onMouseEnter={() => { void prewarmPaymentIntent().catch(() => null); }}
                onFocus={() => { void prewarmPaymentIntent().catch(() => null); }}
                onPointerDown={() => { void prewarmPaymentIntent().catch(() => null); }}
              >
                <span className="web-user-avatar">
                  {userInfo.avatar ? (
                    <img src={userInfo.avatar} alt={userInfo.nickname || 'User'} />
                  ) : (
                    <span>{(userInfo.nickname || 'U').slice(0, 1)}</span>
                  )}
                </span>
                <span className="web-user-name">{userInfo.nickname}</span>
              </button>
            ) : (
              <button
                type="button"
                className="web-login-btn kq-login-btn"
                onClick={handleLoginClick}
                disabled={isPolling}
              >
                {isPolling ? t('header.logging_in', 'Logging in...') : t('header.login', 'Login')}
              </button>
            )}
          </div>
        </div>
      </div>

      {showMobileSearch && (
        <form className="kq-mobile-search-bar" onSubmit={submitSearch}>
          <button type="submit" className="kq-mobile-search-submit" aria-label={searchAria}>
            <SearchOutlined />
          </button>
          <input
            ref={mobileSearchInputRef}
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            type="text"
            placeholder={searchPlaceholder}
          />
        </form>
      )}
    </header>
  );
}

export default WebHeader;
