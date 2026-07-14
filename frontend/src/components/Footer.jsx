import { useState, useEffect } from 'react';
import './Footer.css';

function Footer() {
  const [logoUrl, setLogoUrl] = useState('');

  useEffect(() => {
    const loadLogo = async () => {
      try {
        // 检查是否在Electron环境中
        if (window.electronAPI) {
          const url = await window.electronAPI.getResourceUrl('logo.ico');
          if (url) {
            setLogoUrl(url);
          }
        } else {
          // Web环境，使用public路径
          setLogoUrl('/logo.ico');
        }
      } catch (e) {
        console.error('Failed to load footer logo', e);
        // 降级到public路径
        setLogoUrl('/logo.ico');
      }
    };
    loadLogo();
  }, []);

  return (
    <footer className="app-footer">
      <div className="footer-content">
        {logoUrl && <img src={logoUrl} alt="Logo" className="footer-logo" />}
        <span className="footer-text">鲲穹AI旗下产品</span>
      </div>
    </footer>
  );
}

export default Footer;
