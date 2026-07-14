import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { categories } from '../data';
import ToolHeader from '../components/ToolHeader';
import ToolSidebar from '../components/ToolSidebar';
import ToolDetailContent from '../components/ToolDetailContent';
import '../App.css';

function DocxTools() {
  const navigate = useNavigate();
  const categoryData = categories['文档类'];
  const [activeSection, setActiveSection] = useState(
    categoryData ? categoryData.find(section => section.name === 'DOCX 转换器') || categoryData[0] : null
  );
  const [selectedTool, setSelectedTool] = useState(null);

  const handleToolClick = (tool) => {
    setSelectedTool(tool);
  };

  const handleBackToList = () => {
    setSelectedTool(null);
  };

  const handleSectionClick = (section) => {
    // Navigate to specific converter page based on section name
    const sectionRoutes = {
      'DOCX 转换器': '/tools/docx',
      'HTML 转换器': '/tools/html',
      'JSON 转换器': '/tools/json', 
      'PDF 转换器': '/tools/pdf',
      'TXT 转换器': '/tools/txt',
      'XML 转换器': '/tools/xml'
    };
    
    const route = sectionRoutes[section.name];
    if (route && route !== '/tools/docx') {
      navigate(route);
    } else {
      // Stay on current page but switch section
      setActiveSection(section);
      setSelectedTool(null);
    }
  };

  if (!activeSection) return null;

  return (
    <div className="app-container">
      <ToolHeader />
      <div className="main-layout">
        <ToolSidebar 
          sections={categoryData} 
          activeSection={activeSection} 
          onSectionClick={handleSectionClick} 
        />
        <main className="content-area">
          {selectedTool ? (
            <ToolDetailContent toolName={selectedTool} onBack={handleBackToList} />
          ) : (
            <div className="content-wrapper">
              <div className="section-header">
                <div className="section-divider"></div>
                <h2 className="section-title">{activeSection.name}</h2>
              </div>
              
              <div className="card-grid">
                {activeSection.tools.map((tool) => (
                  <div 
                    key={tool} 
                    className="tool-card"
                    onClick={() => handleToolClick(tool)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="card-icon-wrapper">
                      <div className="file-icon source">DOCX</div>
                      <div className="arrow-icon">→</div>
                      <div className="file-icon target">{tool.split(' To ')[1]}</div>
                    </div>
                    <div className="card-content">
                      <h3 className="card-title">{tool}</h3>
                      <div className="card-tags">
                        <span className="tag">DOCX 工具</span>
                      </div>
                      <p className="card-desc">
                        一款在线{tool}转换器，支持自定义参数，提供多种分辨率选项，助您轻松完成格式转换。
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default DocxTools;
