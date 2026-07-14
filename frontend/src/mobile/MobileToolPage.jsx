import { useEffect, useMemo, useState } from 'react';
import { convertGeneral, convertJSON, convertXML, getApiBaseUrl } from '../services/api';

const FILE_TYPE_MAP = {
  PDF: '.pdf',
  DOCX: '.doc,.docx',
  DOC: '.doc,.docx',
  HTML: '.html,.htm',
  JSON: '.json',
  XML: '.xml',
  TXT: '.txt,.text',
  XLS: '.xls,.xlsx',
  XLSX: '.xls,.xlsx',
  PPT: '.ppt,.pptx',
  PPTX: '.ppt,.pptx',
};

function MobileToolPage({ toolName, onBack }) {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState({});
  const [isConverting, setIsConverting] = useState(false);
  const [pageError, setPageError] = useState('');
  const [apiBaseUrl, setApiBaseUrl] = useState('');

  const { source, target } = useMemo(() => {
    const parts = toolName.split(' To ');
    return {
      source: parts[0] || 'FILE',
      target: (parts[1] || 'FILE').toLowerCase(),
    };
  }, [toolName]);

  useEffect(() => {
    let isMounted = true;

    const loadApiBaseUrl = async () => {
      try {
        const url = await getApiBaseUrl();
        if (isMounted) {
          setApiBaseUrl(url);
        }
      } catch (error) {
        if (isMounted) {
          setPageError(error.message || '接口地址获取失败');
        }
      }
    };

    loadApiBaseUrl();

    return () => {
      isMounted = false;
    };
  }, []);

  const accept = FILE_TYPE_MAP[source] || '';

  const handleFileSelect = (event) => {
    const nextFiles = Array.from(event.target.files || []).map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).slice(2, 8)}`,
      file,
    }));

    setFiles((prev) => [...prev, ...nextFiles]);
    event.target.value = '';
  };

  const handleRemoveFile = (id) => {
    setFiles((prev) => prev.filter((item) => item.id !== id));
    setResults((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const runConversion = async (file) => {
    if (source === 'JSON') {
      return convertJSON(file, target);
    }

    if (source === 'XML') {
      return convertXML(file, target);
    }

    return convertGeneral(file, target);
  };

  const handleConvert = async () => {
    if (!files.length || isConverting) return;

    setIsConverting(true);
    setPageError('');
    setResults({});

    const nextResults = {};

    for (const item of files) {
      try {
        const data = await runConversion(item.file);
        nextResults[item.id] = { status: 'success', data };
      } catch (error) {
        nextResults[item.id] = {
          status: 'error',
          error: error.message || '转换失败',
        };
      }

      setResults({ ...nextResults });
    }

    setIsConverting(false);
  };

  return (
    <main className="mobile-tool-page">
      <div className="mobile-tool-topbar">
        <button type="button" className="mobile-back-button" onClick={onBack}>
          返回
        </button>
        <div>
          <h2>{toolName}</h2>
          <p>移动端基础流程独立维护，避免影响当前桌面端页面结构。</p>
        </div>
      </div>

      <section className="mobile-panel mobile-note-panel">
        <strong>当前移动端范围</strong>
        <p>先支持基础上传、转换、下载链路。桌面端里的复杂参数区和 Electron 交互继续保留在原来的页面中。</p>
      </section>

      <section className="mobile-panel">
        <div className="mobile-panel-header">
          <h3>上传文件</h3>
          <span>{files.length} 个</span>
        </div>

        <label className="mobile-upload-card">
          <input type="file" accept={accept} multiple onChange={handleFileSelect} />
          <span>选择 {source} 文件</span>
          <small>支持多文件，转换完成后可直接下载结果。</small>
        </label>

        {files.length > 0 && (
          <div className="mobile-selected-list">
            {files.map((item) => (
              <div key={item.id} className="mobile-file-row">
                <div className="mobile-file-meta">
                  <strong>{item.file.name}</strong>
                  <span>{(item.file.size / 1024).toFixed(1)} KB</span>
                </div>
                <button type="button" onClick={() => handleRemoveFile(item.id)}>
                  删除
                </button>
              </div>
            ))}
          </div>
        )}

        <button
          type="button"
          className="mobile-primary-button"
          onClick={handleConvert}
          disabled={!files.length || isConverting}
        >
          {isConverting ? '转换中...' : `开始转换为 ${target.toUpperCase()}`}
        </button>

        {pageError ? <p className="mobile-error-text">{pageError}</p> : null}
      </section>

      {Object.keys(results).length > 0 && (
        <section className="mobile-panel">
          <div className="mobile-panel-header">
            <h3>转换结果</h3>
            <span>{Object.keys(results).length} 条</span>
          </div>
          <div className="mobile-result-list">
            {files.map((item) => {
              const result = results[item.id];
              if (!result) return null;

              return (
                <div
                  key={item.id}
                  className={`mobile-result-card ${result.status === 'error' ? 'error' : 'success'}`}
                >
                  <strong>{item.file.name}</strong>
                  {result.status === 'success' ? (
                    <>
                      <p>转换完成，可以直接下载。</p>
                      <a
                        href={`${apiBaseUrl}${result.data.download_url}`}
                        download={result.data.display_name || ''}
                        className="mobile-link-button"
                      >
                        下载 {result.data.display_name || '结果文件'}
                      </a>
                    </>
                  ) : (
                    <p>{result.error}</p>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}
    </main>
  );
}

export default MobileToolPage;
