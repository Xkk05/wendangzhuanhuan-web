import { useState, useEffect, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { LANGUAGE_OPTIONS } from '../constants/languages';
import '../App.css';

function ToolSidebar({
  sections,
  activeSection,
  onSectionClick,
  onToolClick,
  isCompact = false,
  isOpen = false,
  onClose,
}) {
  const { t, i18n } = useTranslation();
  const [searchTerm, setSearchTerm] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef(null);
  const languageOptions = LANGUAGE_OPTIONS;
  const currentLanguage =
    languageOptions.find((item) => item.value === i18n.language)?.value || 'zh_CN';
  const currentLanguageLabel =
    languageOptions.find((item) => item.value === currentLanguage)?.label || LANGUAGE_OPTIONS[0].label;

  const handleClose = () => {
    setShowDropdown(false);
    setSearchTerm('');
    onClose?.();
  };

  const searchResults = useMemo(() => {
    if (!searchTerm.trim() || !sections) {
      return [];
    }

    const results = [];
    sections.forEach((section) => {
      if (section.tools) {
        section.tools.forEach((tool) => {
          if (tool.name.toLowerCase().includes(searchTerm.toLowerCase())) {
            results.push({ ...tool, section });
          }
        });
      }
    });
    return results;
  }, [searchTerm, sections]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchChange = (event) => {
    const value = event.target.value;
    setSearchTerm(value);
    setShowDropdown(Boolean(value.trim()));
  };

  const handleSearchResultClick = (result) => {
    setSearchTerm('');
    setShowDropdown(false);

    if (onToolClick) {
      onToolClick(result, result.section);
    }

    if (isCompact && onClose) {
      handleClose();
    }
  };

  if (!sections) return null;

  return (
    <>
      {isCompact && (
        <div
          className={`sidebar-overlay ${isOpen ? 'visible' : ''}`}
          onClick={handleClose}
        />
      )}

      <aside className={`sidebar ${isCompact ? 'sidebar-mobile' : ''} ${isOpen ? 'is-open' : ''}`}>
        {isCompact && (
          <div className="sidebar-mobile-header">
            <div className="sidebar-mobile-header-copy">
              <strong>{t('header.app_title')}</strong>
              <label className="sidebar-mobile-language">
                <span>{currentLanguageLabel}</span>
                <select
                  value={currentLanguage}
                  onChange={(event) => i18n.changeLanguage(event.target.value)}
                  aria-label={t('header.app_title')}
                >
                  {languageOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <button type="button" className="sidebar-mobile-close" onClick={handleClose}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        )}

        <div className="sidebar-search-wrapper" ref={searchRef}>
          <div className="sidebar-search-input-container">
            <svg className="sidebar-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              type="text"
              className="sidebar-search-input"
              placeholder={t('sidebar.search_placeholder')}
              value={searchTerm}
              onChange={handleSearchChange}
              onFocus={() => {
                if (searchTerm.trim()) {
                  setShowDropdown(true);
                }
              }}
            />
          </div>

          {showDropdown && (
            <div className="search-results-dropdown">
              {searchResults.length > 0 ? (
                searchResults.map((result, index) => (
                  <div
                    key={`${result.section.name}-${result.name}-${index}`}
                    className="search-result-item"
                    onClick={() => handleSearchResultClick(result)}
                  >
                    <span className="search-result-name">
                      {result.name.split(new RegExp(`(${searchTerm})`, 'gi')).map((part, i) =>
                        part.toLowerCase() === searchTerm.toLowerCase() ? (
                          <span key={i} className="search-result-match">{part}</span>
                        ) : (
                          part
                        )
                      )}
                    </span>
                    <span className="search-result-category">{t(`categories.${result.section.name}`)}</span>
                  </div>
                ))
              ) : (
                <div className="search-no-results">{t('sidebar.no_results')}</div>
              )}
            </div>
          )}
        </div>

        <nav className="sidebar-nav">
          {sections.map((section) => (
            <div
              key={section.name}
              className={`sidebar-item ${activeSection?.name === section.name ? 'active' : ''}`}
              onClick={() => {
                onSectionClick(section);
                if (isCompact && onClose) {
                  handleClose();
                }
              }}
            >
              <span className="sidebar-text">{t(`categories.${section.name}`)}</span>
              {activeSection?.name === section.name && (
                <svg className="sidebar-active-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              )}
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}

export default ToolSidebar;
