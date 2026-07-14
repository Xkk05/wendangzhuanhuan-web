import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { categories } from '../data';
import MobileToolPage from './MobileToolPage';
import './MobileApp.css';

const sectionList = categories.major_functions || [];

function MobileApp() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { source, target } = useParams();
  const [activeSectionName, setActiveSectionName] = useState(sectionList[0]?.name || '');

  const selectedTool = useMemo(() => {
    if (!source || !target) return null;
    const toolName = `${source.toUpperCase()} To ${target.toUpperCase()}`;

    for (const section of sectionList) {
      const matchedTool = section.tools.find(
        (tool) => tool.name.toLowerCase() === toolName.toLowerCase()
      );

      if (matchedTool) {
        return matchedTool.name;
      }
    }

    return null;
  }, [source, target]);

  const activeSection = useMemo(() => {
    if (selectedTool) {
      const matchedSection = sectionList.find((section) =>
        section.tools.some((tool) => tool.name === selectedTool)
      );

      if (matchedSection) {
        return matchedSection;
      }
    }

    return sectionList.find((section) => section.name === activeSectionName) || sectionList[0] || null;
  }, [activeSectionName, selectedTool]);

  const handleToolOpen = (toolName) => {
    const parts = toolName.split(' To ');
    if (parts.length !== 2) return;

    navigate(`/mobile/tool/${parts[0].toLowerCase()}/${parts[1].toLowerCase()}`);
  };

  if (!activeSection && !selectedTool) {
    return null;
  }

  return (
    <div className="mobile-app-shell">
      <header className="mobile-app-header">
        <p className="mobile-app-kicker">Mobile Preview</p>
        <h1 className="mobile-app-title">{t('header.app_title')}</h1>
        <p className="mobile-app-subtitle">
          这套移动端页面单独放在 `mobile/` 目录里，桌面端现有页面和样式保持原样。
        </p>
      </header>

      {selectedTool ? (
        <MobileToolPage toolName={selectedTool} onBack={() => navigate('/mobile')} />
      ) : (
        <main className="mobile-home">
          <section className="mobile-panel">
            <div className="mobile-panel-header">
              <h2>功能分类</h2>
              <span>{sectionList.length} 组</span>
            </div>
            <div className="mobile-chip-list">
              {sectionList.map((section) => (
                <button
                  key={section.name}
                  type="button"
                  className={`mobile-chip ${activeSection?.name === section.name ? 'active' : ''}`}
                  onClick={() => setActiveSectionName(section.name)}
                >
                  {t(`categories.${section.name}`)}
                </button>
              ))}
            </div>
          </section>

          <section className="mobile-panel">
            <div className="mobile-panel-header">
              <h2>{t(`categories.${activeSection?.name}`)}</h2>
              <span>{activeSection?.tools.length || 0} 个工具</span>
            </div>
            <div className="mobile-tool-list">
              {activeSection?.tools.map((tool) => {
                const parts = tool.name.split(' To ');
                return (
                  <button
                    key={tool.name}
                    type="button"
                    className="mobile-tool-card"
                    onClick={() => handleToolOpen(tool.name)}
                  >
                    <div className="mobile-tool-badge">
                      <span>{parts[0] || 'FILE'}</span>
                      <span className="mobile-tool-arrow">TO</span>
                      <span>{parts[1] || 'FILE'}</span>
                    </div>
                    <div className="mobile-tool-copy">
                      <strong>{tool.name}</strong>
                      <p>{tool.description}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </section>
        </main>
      )}
    </div>
  );
}

export default MobileApp;
