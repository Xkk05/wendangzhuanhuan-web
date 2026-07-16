import { useState, useEffect, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useParams, useNavigate } from 'react-router-dom';
import { Select } from 'antd';
import { GlobalOutlined, StarFilled, StarOutlined } from '@ant-design/icons';
import { categories } from '../data';
import Dashboard from '../components/Dashboard';
import ToolHeader from '../components/ToolHeader';
import ToolSidebar from '../components/ToolSidebar';
import ToolDetailContent from '../components/ToolDetailContent';
import WebHeader from '../components/WebHeader';
import WebFooter from '../components/WebFooter';
import SeoHead from '../components/SeoHead';
import {
  getCategoryByExtension,
  findSectionByToolName,
  getSectionByCategorySlug,
  getCategorySlugBySectionName,
} from '../utils/toolHelpers';
import { persistCurrentToolSnapshot } from '../utils/authStorage';
import { DEFAULT_OG_IMAGE, getLocalizedPath, getSeoData } from '../utils/seo';
import { LANGUAGE_OPTIONS } from '../constants/languages';
import '../App.css';

const DEFAULT_WEB_SECTION_NAME = '__home__';
const HOME_SECTION_NAME = '__home__';
const FAVORITES_STORAGE_KEY = 'toolFavorites';

function MainPage({ isElectron = false }) {
  const { t, i18n } = useTranslation();
  const { source, target, category } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const categoryData = useMemo(() => {
    const allCategories = categories.major_functions || [];
    if (isElectron) {
      return allCategories;
    }

    return allCategories
      .filter((section) => section.name !== 'ppt_converter')
      .map((section) => ({
        ...section,
        tools: (section.tools || []).filter((tool) => {
          const toolName = tool.name || '';
          return !/^PPT\s+To\s+/i.test(toolName) && !/\s+To\s+PPT$/i.test(toolName);
        }),
      }))
      .filter((section) => (section.tools || []).length > 0);
  }, [isElectron]);

  const languages = useMemo(() => LANGUAGE_OPTIONS, []);

  const currentLanguage = useMemo(() => languages.some((item) => item.value === i18n.language)
    ? i18n.language
    : 'zh_CN', [i18n.language, languages]);

  const [activeSection, setActiveSection] = useState(
    categoryData.find((section) => section.name === DEFAULT_WEB_SECTION_NAME) || categoryData[0] || null
  );
  const [isMaximized, setIsMaximized] = useState(false);
  const [isCompactWeb, setIsCompactWeb] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth <= 960 : false
  );
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [history, setHistory] = useState(() => {
    try {
      const savedHistory = localStorage.getItem('toolHistory');
      return savedHistory ? JSON.parse(savedHistory) : [];
    } catch {
      return [];
    }
  });
  const [favorites, setFavorites] = useState(() => {
    try {
      const savedFavorites = localStorage.getItem(FAVORITES_STORAGE_KEY);
      return savedFavorites ? JSON.parse(savedFavorites) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    document.body.classList.toggle('web-mode', !isElectron);
    return () => {
      document.body.classList.remove('web-mode');
    };
  }, [isElectron]);

  useEffect(() => {
    if (isElectron) {
      return undefined;
    }

    document.body.classList.toggle('web-sidebar-open', isCompactWeb && isSidebarOpen);
    return () => {
      document.body.classList.remove('web-sidebar-open');
    };
  }, [isCompactWeb, isElectron, isSidebarOpen]);

  useEffect(() => {
    if (isElectron) {
      return undefined;
    }

    const handleResize = () => {
      const compact = window.innerWidth <= 960;
      setIsCompactWeb(compact);
      if (!compact) {
        setIsSidebarOpen(false);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [isElectron]);

  useEffect(() => {
    localStorage.setItem('toolHistory', JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favorites));
  }, [favorites]);

  const addToHistory = useCallback((toolName) => {
    setHistory((prev) => {
      const nextHistory = [toolName, ...prev.filter((item) => item !== toolName)];
      return nextHistory.slice(0, 10);
    });
  }, []);

  const handleFavoriteToggle = useCallback((toolName) => {
    setFavorites((prev) => (
      prev.includes(toolName)
        ? prev.filter((item) => item !== toolName)
        : [toolName, ...prev]
    ));
  }, []);

  useEffect(() => {
    const electron = window.require ? window.require('electron') : null;
    if (electron) {
      const handleMaximizedStateChange = (event, state) => {
        setIsMaximized(state);
      };
      electron.ipcRenderer.on('window-maximized-state-changed', handleMaximizedStateChange);
      return () => {
        electron.ipcRenderer.removeListener('window-maximized-state-changed', handleMaximizedStateChange);
      };
    }

    return undefined;
  }, []);

  useEffect(() => {
    const handleDragOver = (event) => {
      event.preventDefault();
      event.stopPropagation();
    };

    const handleDrop = (event) => {
      if (event.defaultPrevented) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();

      const files = event.dataTransfer.files;
      if (!files || files.length === 0) {
        return;
      }

      const file = files[0];
      const extension = file.name.split('.').pop();
      const categoryName = getCategoryByExtension(extension);
      if (!categoryName) {
        return;
      }

      const section = categoryData.find((item) => item.name === categoryName);
      if (section) {
        setActiveSection(section);
        const sectionSlug = getCategorySlugBySectionName(section.name);
        navigate(sectionSlug ? `/tools/${sectionSlug}` : '/');
      }
    };

    window.addEventListener('dragover', handleDragOver);
    window.addEventListener('drop', handleDrop);

    return () => {
      window.removeEventListener('dragover', handleDragOver);
      window.removeEventListener('drop', handleDrop);
    };
  }, [categoryData, navigate]);

  const selectedTool = useMemo(() => {
    if (!source || !target || !categoryData.length) {
      return null;
    }

    const toolName = `${source.toUpperCase()} To ${target.toUpperCase()}`;
    for (const section of categoryData) {
      const matchedTool = section.tools.find(
        (tool) => tool.name.toLowerCase() === toolName.toLowerCase()
      );
      if (matchedTool) {
        return matchedTool.name;
      }
    }

    return null;
  }, [source, target, categoryData]);

  const derivedSection = useMemo(() => {
    if (!selectedTool) {
      return null;
    }
    return findSectionByToolName(selectedTool);
  }, [selectedTool]);

  const categorySection = useMemo(() => getSectionByCategorySlug(category), [category]);
  const isHomeSection = !selectedTool && !category && activeSection?.name === HOME_SECTION_NAME;
  const effectiveSection = isHomeSection ? null : (derivedSection || categorySection || activeSection);
  const activeTools = useMemo(
    () => categoryData.find((section) => section.name === effectiveSection?.name)?.tools || [],
    [categoryData, effectiveSection]
  );

  const handleBackToGrid = useCallback(() => {
    const sectionSlug = getCategorySlugBySectionName(effectiveSection?.name);
    navigate(sectionSlug ? `/tools/${sectionSlug}` : '/');
  }, [effectiveSection, navigate]);

  const handleSectionClick = useCallback((section) => {
    setActiveSection(section);
    setIsSidebarOpen(false);
    const sectionSlug = getCategorySlugBySectionName(section.name);
    navigate(sectionSlug ? `/tools/${sectionSlug}` : '/');
  }, [navigate]);

  const handleHomeClick = useCallback(() => {
    setActiveSection({ name: HOME_SECTION_NAME });
    setIsSidebarOpen(false);
    navigate('/');
  }, [navigate]);

  const handleToolClick = useCallback((tool, section) => {
    addToHistory(tool.name);
    setIsSidebarOpen(false);

    const parts = tool.name.split(' To ');
    if (parts.length === 2) {
      navigate(`/tool/${parts[0].toLowerCase()}/${parts[1].toLowerCase()}`);
    } else {
      navigate('/');
    }

    if (section) {
      setActiveSection(section);
      return;
    }

    const foundSection = findSectionByToolName(tool.name);
    if (foundSection) {
      setActiveSection(foundSection);
    }
  }, [addToHistory, navigate]);

  const toolDetail = useMemo(() => {
    if (!selectedTool) {
      return null;
    }

    return <ToolDetailContent toolName={selectedTool} onBack={handleBackToGrid} />;
  }, [selectedTool, handleBackToGrid]);

  useEffect(() => {
    if (!selectedTool) {
      return;
    }

    const timer = window.setTimeout(() => {
      addToHistory(selectedTool);
    }, 0);
    persistCurrentToolSnapshot(
      `${location.pathname}${location.search}${location.hash}`,
      selectedTool
    );
    return () => window.clearTimeout(timer);
  }, [addToHistory, location.hash, location.pathname, location.search, selectedTool]);

  const seo = useMemo(() => getSeoData({
    pathname: location.pathname,
    selectedTool,
    effectiveSection,
    t,
    language: currentLanguage,
  }), [currentLanguage, effectiveSection, location.pathname, selectedTool, t]);

  const handleLanguageChange = useCallback((value) => {
    i18n.changeLanguage(value);
    if (!isElectron) {
      const nextUrl = getLocalizedPath(location.pathname, value);
      window.history.replaceState({}, '', nextUrl);
    }
  }, [i18n, isElectron, location.pathname]);

  const renderFavoriteButton = useCallback((toolName) => {
    const isFavorite = favorites.includes(toolName);
    return (
      <button
        type="button"
        className="favorite-btn"
        onClick={(event) => {
          event.stopPropagation();
          handleFavoriteToggle(toolName);
        }}
        title={isFavorite ? t('dashboard.unfavorite') : t('dashboard.favorite')}
      >
        {isFavorite ? <StarFilled style={{ color: '#fbbf24' }} /> : <StarOutlined />}
      </button>
    );
  }, [favorites, handleFavoriteToggle, t]);

  const categoryCards = categoryData.map((section) => {
    const SectionIcon = section.icon;
    return (
      <button
        key={section.name}
        type="button"
        className="category-home-card"
        onClick={() => handleSectionClick(section)}
      >
        <div className="category-home-card-icon">
          <SectionIcon />
        </div>
        <div className="category-home-card-copy">
          <h3>{t(`categories.${section.name}`)}</h3>
          <p>{section.tools.length} tools</p>
        </div>
        <span className="category-home-card-arrow">›</span>
      </button>
    );
  });

  const shellContent = (
    <>
      {isElectron && (
        <ToolHeader
          onHomeClick={handleHomeClick}
          activeSection={
            isHomeSection
              ? t('header.home')
              : t(`categories.${effectiveSection?.name}`)
          }
        />
      )}

      {!isElectron && <WebHeader />}

      <div className={`main-layout ${isElectron ? '' : 'web-main-layout'}`}>
        {isElectron && (
          <ToolSidebar
            sections={categoryData}
            activeSection={isHomeSection ? null : effectiveSection}
            onSectionClick={handleSectionClick}
            onToolClick={handleToolClick}
            isCompact={!isElectron && isCompactWeb}
            isOpen={isSidebarOpen}
            onClose={() => setIsSidebarOpen(false)}
          />
        )}

        <main className="content-area">
          <div className={`content-wrapper ${!isElectron ? 'web-content-wrapper' : ''}`}>
            {isElectron ? (
              selectedTool ? (
                toolDetail
              ) : isHomeSection ? (
                <Dashboard
                  history={history}
                  favorites={favorites}
                  onToolClick={handleToolClick}
                  onFavoriteToggle={handleFavoriteToggle}
                />
              ) : (
                <>
                  <div className="section-header">
                    <div className="section-divider"></div>
                    <h2 className="section-title">{t(`categories.${effectiveSection?.name}`)}</h2>
                  </div>

                  <div className="card-grid">
                    {activeTools.map((tool) => {
                      const parts = tool.name.split(' To ');
                      const sourceName = parts[0] || 'TOOL';
                      const targetName = parts[1] || 'BOX';

                      return (
                        <div
                          key={tool.name}
                          className="tool-card"
                          onClick={() => handleToolClick(tool)}
                        >
                          {renderFavoriteButton(tool.name)}
                          <div className="tool-card-icon">
                            <span className="format-text source">{sourceName}</span>
                            <div className="format-divider"></div>
                            <span className="format-text target">{targetName}</span>
                          </div>
                          <div className="card-content">
                            <div className="card-header-row">
                              <h3 className="card-title">{tool.name}</h3>
                              <div className="card-tags">
                                <span className="tag">{sourceName} TOOLS</span>
                              </div>
                            </div>
                            <p className="card-desc">{tool.description}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </>
              )
            ) : (
                <div className="web-content-container">
                  <div className="web-tool-card">
                    <div className="web-project-header-card">
                      <div className="web-project-info">
                        <h1 className="web-project-title">{t('header.app_title')}</h1>
                        <p className="web-project-desc">{t('header.app_subtitle')}</p>
                      </div>
                      <div className="web-project-actions">
                        <div className="web-language-select">
                          <GlobalOutlined className="web-language-icon" />
                          <Select
                            value={currentLanguage}
                            onChange={handleLanguageChange}
                            options={languages}
                            variant="borderless"
                            popupMatchSelectWidth={false}
                            className="web-language-dropdown"
                          />
                        </div>
                      </div>
                    </div>
                    <nav className="web-internal-nav">
                     {categoryData.map((section) => (
                       <button
                         key={section.name}
                         type="button"
                         className={`web-internal-nav-item ${
                           effectiveSection?.name === section.name && !isHomeSection ? 'active' : ''
                         }`}
                         onClick={() => handleSectionClick(section)}
                       >
                         {t(`categories.${section.name}`)}
                       </button>
                     ))}
                   </nav>
                    <div className={`web-primary-stage ${!selectedTool && !isHomeSection ? 'web-primary-stage-fixed' : ''}`}>
                    {selectedTool ? (
                      toolDetail
                    ) : isHomeSection ? (
                      <>
                        <Dashboard
                          history={history}
                          favorites={favorites}
                          onToolClick={handleToolClick}
                          onFavoriteToggle={handleFavoriteToggle}
                        />
                        <section className="category-home-section" style={{ marginTop: 32 }}>
                          <div className="section-header">
                            <div className="section-divider"></div>
                            <h2 className="section-title">{t('home.all_categories')}</h2>
                          </div>
                          <div className="category-home-grid">
                            {categoryCards}
                          </div>
                        </section>
                      </>
                    ) : (
                      <>
                        <div className="section-header">
                          <div className="section-divider"></div>
                          <h2 className="section-title">{t(`categories.${effectiveSection?.name}`)}</h2>
                        </div>

                        <div className="card-grid">
                          {activeTools.map((tool) => {
                            const parts = tool.name.split(' To ');
                            const sourceName = parts[0] || 'TOOL';
                            const targetName = parts[1] || 'BOX';

                            return (
                              <div
                                key={tool.name}
                                className="tool-card"
                                onClick={() => handleToolClick(tool)}
                              >
                                {renderFavoriteButton(tool.name)}
                                <div className="tool-card-icon">
                                  <span className="format-text source">{sourceName}</span>
                                  <div className="format-divider"></div>
                                  <span className="format-text target">{targetName}</span>
                                </div>
                                <div className="card-content">
                                  <div className="card-header-row">
                                    <h3 className="card-title">{tool.name}</h3>
                                    <div className="card-tags">
                                      <span className="tag">{sourceName} TOOLS</span>
                                    </div>
                                  </div>
                                  <p className="card-desc">{tool.description}</p>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </>
                    )}
                    </div>
                  </div>
                </div>
            )}
          </div>
        </main>
      </div>

      {!isElectron && (
        <WebFooter
          languages={languages}
          currentLanguage={currentLanguage}
          onLanguageChange={handleLanguageChange}
        />
      )}
    </>
  );

  return (
    <div className={isElectron ? `app-container ${isMaximized ? 'maximized' : ''}` : 'web-page-shell'}>
      {!isElectron && (
        <SeoHead
          title={seo.title}
          description={seo.description}
          canonicalUrl={seo.canonicalUrl}
          imageUrl={DEFAULT_OG_IMAGE}
          keywords={seo.keywords}
          locale={seo.locale}
          alternateLinks={seo.alternateLinks}
        />
      )}
      {!isElectron ? (
        <div className="web-page-content">{shellContent}</div>
      ) : (
        shellContent
      )}
    </div>
  );
}

export default MainPage;
