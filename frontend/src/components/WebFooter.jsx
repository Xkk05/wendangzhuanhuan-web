import { useTranslation } from 'react-i18next';
import './WebShell.css';

const SITE_ORIGIN = 'https://www.kunqiongai.com';
const FOOTER_LANGUAGE_ROWS = [
  ['zh_CN', 'zh_TW', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'it', 'pt', 'pt_BR', 'ru', 'ar', 'vi', 'th'],
  ['id', 'pl', 'nl', 'tr', 'uk', 'he', 'fa', 'hi', 'bn', 'ms', 'sw', 'ta', 'tl', 'ur'],
];

function WebFooter({ languages = [], currentLanguage = 'zh_CN', onLanguageChange }) {
  const { t } = useTranslation();
  const languageMap = new Map(languages.map((language) => [language.value, language]));

  const quickLinks = [
    { label: t('webFooter.quick_links.home', 'Home'), href: `${SITE_ORIGIN}/` },
    { label: t('webFooter.quick_links.ai_tools', 'AI Tools'), href: `${SITE_ORIGIN}/category/ai` },
    {
      label: t('webFooter.quick_links.custom_service', 'Consulting Services'),
      href: `${SITE_ORIGIN}/custom`,
    },
    { label: t('webFooter.quick_links.industry_news', 'Industry News'), href: `${SITE_ORIGIN}/news` },
    { label: t('webFooter.quick_links.feedback', 'Feedback'), href: `${SITE_ORIGIN}/feedback` },
  ];

  const categoryLinks = [
    { label: t('webFooter.tool_links.text_processing', 'Text Processing'), href: `${SITE_ORIGIN}/category/text` },
    { label: t('webFooter.tool_links.multimedia', 'Multimedia'), href: `${SITE_ORIGIN}/category/multimedia` },
    { label: t('webFooter.tool_links.office_tools', 'Office Tools'), href: `${SITE_ORIGIN}/category/office` },
    { label: t('webFooter.tool_links.file_processing', 'File Processing'), href: `${SITE_ORIGIN}/category/file` },
    { label: t('webFooter.tool_links.code_development', 'Code Development'), href: `${SITE_ORIGIN}/category/development` },
  ];

  const handleLanguageClick = (code) => {
    if (typeof onLanguageChange === 'function') {
      onLanguageChange(code);
    }
  };

  return (
    <div className="kq-web-footer-stack">
      <section className="kq-language-panel">
        <div className="kq-language-panel-inner">
          <div className="kq-language-title">{t('webFooter.language_title', 'Language')}</div>
          <div className="kq-language-links" aria-label={t('webFooter.language_title', 'Language')}>
            {FOOTER_LANGUAGE_ROWS.map((row) => (
              <div className="kq-language-link-row" key={row.join('-')}>
                {row.map((code) => languageMap.get(code)).filter(Boolean).map((language) => (
                  <button
                    type="button"
                    key={language.value}
                    className={`kq-language-link ${language.value === currentLanguage ? 'active' : ''}`}
                    onClick={() => handleLanguageClick(language.value)}
                    aria-pressed={language.value === currentLanguage}
                  >
                    {language.label}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="kq-footer">
        <div className="kq-footer-container">
          <div className="kq-footer-content">
            <div className="kq-footer-section kq-footer-brand-section">
              <a href={`${SITE_ORIGIN}/`} className="kq-footer-brand-link">
                <img
                  src="/web-assets/logo2.png"
                  alt={t('webFooter.brand_title', 'KUNQIONG AI TOOLS')}
                  className="kq-footer-logo"
                />
              </a>
              <p className="kq-footer-desc">
                {t(
                  'webFooter.description',
                  'We provide quality AI tools and consulting services for individuals and businesses.',
                )}
              </p>
              <div className="kq-footer-social">
                <a
                  href={`${SITE_ORIGIN}/#`}
                  className="kq-social-icon"
                  aria-label={t('webFooter.social.douyin', 'Douyin')}
                >
                  <img src="/web-assets/dy.png" alt={t('webFooter.social.douyin', 'Douyin')} />
                </a>
                <a
                  href={`${SITE_ORIGIN}/#`}
                  className="kq-social-icon"
                  aria-label={t('webFooter.social.wechat', 'WeChat')}
                >
                  <img src="/web-assets/wx.png" alt={t('webFooter.social.wechat', 'WeChat')} />
                </a>
                <a
                  href={`${SITE_ORIGIN}/#`}
                  className="kq-social-icon"
                  aria-label={t('webFooter.social.weibo', 'Weibo')}
                >
                  <img src="/web-assets/wb.png" alt={t('webFooter.social.weibo', 'Weibo')} />
                </a>
              </div>
            </div>

            <div className="kq-footer-section">
              <h4>{t('webFooter.sections.quick_links', 'Quick Links')}</h4>
              <ul>
                {quickLinks.map((item) => (
                  <li key={item.href}>
                    <a href={item.href}>{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>

            <div className="kq-footer-section">
              <h4>{t('webFooter.sections.tool_categories', 'Tool Categories')}</h4>
              <ul>
                {categoryLinks.map((item) => (
                  <li key={item.href}>
                    <a href={item.href}>{item.label}</a>
                  </li>
                ))}
              </ul>
            </div>

            <div className="kq-footer-section">
              <h4>{t('webFooter.sections.contact_us', 'Contact Us')}</h4>
              <ul className="kq-contact-list">
                <li>
                  <img src="/web-assets/gonsi.png" alt="" className="kq-contact-icon-img" />
                  <span>{t('webFooter.contact.company_name', 'Jiangxi Hexagram Technology Co., Ltd.')}</span>
                </li>
                <li>
                  <img src="/web-assets/dianhua.png" alt="" className="kq-contact-icon-img" />
                  <span>{t('webFooter.contact.phone_number', '+86 17770307066')}</span>
                </li>
                <li>
                  <img src="/web-assets/weizhi.png" alt="" className="kq-contact-icon-img" />
                  <span>
                    {t(
                      'webFooter.contact.address_detail',
                      '9F, Building 9, Tianyou Avenue, High-speed Railway Test Zone, Shangrao, Jiangxi',
                    )}
                  </span>
                </li>
                <li>
                  <img src="/web-assets/youxiang.png" alt="" className="kq-contact-icon-img" />
                  <span>{t('webFooter.contact.email_address', '11247931@qq.com')}</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="kq-footer-bottom">
            <div className="kq-back-to-top">
              <button
                type="button"
                className="kq-back-to-top-btn"
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              >
                {t('webFooter.back_to_top', 'Back to top')}
              </button>
            </div>

            <p className="kq-copyright-links">
              <span>
                {t('webFooter.copyright', {
                  year: new Date().getFullYear(),
                  brand: t('webFooter.brand_title', 'KUNQIONG AI TOOLS'),
                })}
              </span>
              <span className="kq-separator">|</span>
              <a href={`${SITE_ORIGIN}/user-agreement`} target="_blank" rel="noreferrer">
                {t('webFooter.user_agreement', 'User Agreement')}
              </a>
              <span className="kq-separator">|</span>
              <a href={`${SITE_ORIGIN}/privacy-policy`} target="_blank" rel="noreferrer">
                {t('webFooter.privacy_policy', 'Privacy Policy')}
              </a>
              <span className="kq-separator">|</span>
              <a href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">
                {t('webFooter.icp_number', 'Gan ICP No. 2022004738-6')}
              </a>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default WebFooter;
