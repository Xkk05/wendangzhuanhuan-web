import React from 'react';
import { useTranslation } from 'react-i18next';
import { findToolByName } from '../utils/toolHelpers';
import { StarFilled, StarOutlined, HistoryOutlined, AppstoreOutlined } from '@ant-design/icons';
import '../App.css';

function Dashboard({ history, favorites, onToolClick, onFavoriteToggle }) {
  const { t } = useTranslation();
  const favoriteTools = favorites
    .map((name) => findToolByName(name))
    .filter(Boolean);

  const historyTools = history
    .map((name) => findToolByName(name))
    .filter(Boolean);

  const renderToolCard = (tool, isFavorite) => {
    if (!tool) return null;
    const parts = tool.name.split(' To ');
    const source = parts[0] || 'TOOL';
    const target = parts[1] || 'BOX';

    return (
      <div
        key={tool.name}
        className="tool-card dashboard-card"
        onClick={() => onToolClick(tool)}
      >
        <div className="tool-card-icon">
          <span className="format-text source">{source}</span>
          <div className="format-divider"></div>
          <span className="format-text target">{target}</span>
        </div>
        <div className="card-content">
          <div className="card-header-row">
            <h3 className="card-title">{tool.name}</h3>
            <button
              className="favorite-btn"
              onClick={(e) => {
                e.stopPropagation();
                onFavoriteToggle(tool.name);
              }}
              title={isFavorite ? t('dashboard.unfavorite') : t('dashboard.favorite')}
            >
              {isFavorite ? <StarFilled style={{ color: '#fbbf24' }} /> : <StarOutlined />}
            </button>
          </div>
          <p className="card-desc">{tool.description}</p>
        </div>
      </div>
    );
  };

  return (
    <div className="dashboard-container">
      <div className="section-header">
        <div className="section-divider"></div>
        <h2 className="section-title">
          <AppstoreOutlined style={{ marginRight: 8 }} />
          {t('dashboard.my_favorites')}
        </h2>
      </div>

      {favoriteTools.length > 0 ? (
        <div className="card-grid">
          {favoriteTools.map((tool) => renderToolCard(tool, true))}
        </div>
      ) : (
        <div className="empty-state">
          <p>{t('dashboard.no_favorites')}</p>
        </div>
      )}

      <div className="section-header dashboard-section-break">
        <div className="section-divider"></div>
        <h2 className="section-title">
          <HistoryOutlined style={{ marginRight: 8 }} />
          {t('dashboard.recent_used')}
        </h2>
      </div>

      {historyTools.length > 0 ? (
        <div className="card-grid">
          {historyTools.map((tool) => renderToolCard(tool, favorites.includes(tool.name)))}
        </div>
      ) : (
        <div className="empty-state">
          <p>{t('dashboard.no_history')}</p>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
