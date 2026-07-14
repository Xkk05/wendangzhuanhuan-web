import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import '../App.css';

const categories = ['docx', 'html', 'json', 'pdf', 'txt', 'xml'];

const icons = {
  'docx': '📝',
  'html': '🌐',
  'json': '🔢',
  'pdf': '📕',
  'txt': '📄',
  'xml': '🧩'
};

function Home() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <div className="app-container" style={{ background: '#f8fafc', minHeight: '100vh', height: 'auto', overflow: 'visible', padding: '60px 20px' }}>
      <div className="home-wrapper" style={{ maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        <h1 className="home-title">{t('home.title')}</h1>
        <p className="home-subtitle">{t('home.subtitle')}</p>
        
        <div className="home-grid">
          {categories.map((cat) => (
            <div 
              key={cat} 
              className="home-card"
              onClick={() => navigate(`/tools/${cat}`)}
            >
              <div className="home-card-icon">{icons[cat]}</div>
              <h2 className="home-card-title">{t(`home.categories.${cat}`)}</h2>
              <p className="home-card-desc">{t(`home.categories.${cat}_desc`)}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Home;
