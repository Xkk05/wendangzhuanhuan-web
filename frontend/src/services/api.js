// frontend/src/services/api.js
import { getPersistedToken } from '../utils/authStorage';

let cachedApiBaseUrl = null;

const resolveFallbackBaseUrl = () => {
  const envBaseUrl = import.meta?.env?.VITE_API_BASE_URL;
  if (envBaseUrl) {
    return envBaseUrl;
  }

  const origin = window?.location?.origin;
  if (origin && /^https?:/i.test(origin)) {
    const { hostname } = window.location;
    const isLocalDevHost = hostname === 'localhost' || hostname === '127.0.0.1';
    if (isLocalDevHost) {
      return 'http://127.0.0.1:8002';
    }
    return origin;
  }

  return 'http://127.0.0.1:8002';
};

const fallbackBaseUrl = resolveFallbackBaseUrl();

const resolveApiBaseUrl = async () => {
  if (cachedApiBaseUrl) {
    return cachedApiBaseUrl;
  }
  
  if (window?.electronAPI?.getBackendBaseUrl) {
    try {
      const url = await window.electronAPI.getBackendBaseUrl();
      if (url) {
        cachedApiBaseUrl = url;
        return cachedApiBaseUrl;
      }
    } catch (error) {
      console.error('[API] Failed to get backend URL from Electron:', error);
      cachedApiBaseUrl = fallbackBaseUrl;
      return cachedApiBaseUrl;
    }
  }
  
  cachedApiBaseUrl = fallbackBaseUrl;
  return cachedApiBaseUrl;
};

export const getApiBaseUrl = async () => resolveApiBaseUrl();

let backendReadyPromise = null;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const ensureBackendReady = async (baseUrl) => {
  if (backendReadyPromise) return backendReadyPromise;
  backendReadyPromise = (async () => {
    const maxAttempts = 20;
    const delayMs = 300;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      try {
        const response = await fetch(`${baseUrl}/api/health`, { method: 'GET' });
        if (response.ok) {
          return true;
        }
      } catch {
        await sleep(delayMs);
      }
    }
    console.error('[API] Backend failed to become ready after', maxAttempts, 'attempts');
    return false;
  })();
  const ready = await backendReadyPromise;
  if (!ready) backendReadyPromise = null;
  return ready;
};

const handleResponse = async (response, apiBaseUrl, file) => {
  if (!response.ok) {
    let errorDetail = '转换失败';
    let errorCode = '';
    let paymentUrl = '';
    try {
      const errorData = await response.json();
      const detail = errorData?.detail;
      if (typeof detail === 'string') {
        errorDetail = detail;
      } else if (detail && typeof detail === 'object') {
        errorDetail = detail.message || errorDetail;
        errorCode = detail.code || '';
        paymentUrl = detail.payment_url || '';
      } else if (typeof errorData?.message === 'string') {
        errorDetail = errorData.message;
      }
    } catch {
      errorDetail = `转换失败 (${response.status}: ${response.statusText})`;
    }

    if (response.status === 403 && errorCode === 'membership_required') {
      window.dispatchEvent(
        new CustomEvent('membership-required', {
          detail: {
            message: errorDetail,
            paymentUrl,
          },
        })
      );
    }
    
    // 尝试获取诊断信息
    try {
      const diagResponse = await fetch(`${apiBaseUrl}/api/diagnostics`);
      if (diagResponse.ok) {
        const diagData = await diagResponse.json();
        
        // 针对不同文件类型给出更具体的错误建议
        if (file) {
          const fileName = file.name.toLowerCase();
          if ((fileName.endsWith('.doc') || fileName.endsWith('.docx') || fileName.endsWith('.ppt') || fileName.endsWith('.pptx') || fileName.endsWith('.xls') || fileName.endsWith('.xlsx'))) {
            if (diagData.office && !diagData.office.word && !diagData.office.excel && !diagData.office.ppt && !diagData.office.wps) {
              errorDetail += '。请确保电脑已安装 Microsoft Office 或 WPS Office。';
            }
          }
          if (fileName.endsWith('.html') || fileName.endsWith('.htm')) {
            if (diagData.browsers && !diagData.browsers.chrome && !diagData.browsers.edge) {
              errorDetail += '。请确保电脑已安装 Chrome 或 Edge 浏览器。';
            }
          }
        }
      }
    } catch (diagError) {
      void diagError;
    }
    
    const error = new Error(errorDetail);
    error.status = response.status;
    error.code = errorCode;
    error.paymentUrl = paymentUrl;
    throw error;
  }
  return await response.json();
};

const buildAuthHeaders = () => {
  const token = getPersistedToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

/**
 * 转换 JSON 文件
 * @param {File} file - JSON 文件
 * @param {string} targetFormat - 目标格式 (yaml 或 yml)
 * @param {Object} options - 转换选项
 * @returns {Promise<Object>} 转换结果
 */
export const convertJSON = async (file, targetFormat, options = {}) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_format', targetFormat);
    
    // Add optional parameters
    if (options.indent) formData.append('indent', options.indent);
    if (options.sortKeys) formData.append('sort_keys', options.sortKeys);

    const apiBaseUrl = await getApiBaseUrl();
    const ready = await ensureBackendReady(apiBaseUrl);
    if (!ready) {
      throw new Error('后端服务未启动');
    }
    const response = await fetch(`${apiBaseUrl}/api/convert/json`, {
      method: 'POST',
      body: formData,
      signal: options.signal,
      headers: buildAuthHeaders(),
    });

    return await handleResponse(response, apiBaseUrl, file);
  } catch (error) {
    console.error('Conversion error:', error);
    throw error;
  }
};

export const convertXML = async (file, targetFormat, options = {}) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_format', targetFormat);
    
    // Add optional parameters (same as JSON)
    if (options.indent) formData.append('indent', options.indent);
    if (options.sortKeys) formData.append('sort_keys', options.sortKeys);

    const apiBaseUrl = await getApiBaseUrl();
    const ready = await ensureBackendReady(apiBaseUrl);
    if (!ready) {
      throw new Error('后端服务未启动');
    }
    const response = await fetch(`${apiBaseUrl}/api/convert/xml`, {
      method: 'POST',
      body: formData,
      signal: options.signal,
      headers: buildAuthHeaders(),
    });

    return await handleResponse(response, apiBaseUrl, file);
  } catch (error) {
    console.error('Conversion error:', error);
    throw error;
  }
};

export const convertGeneral = async (file, targetFormat, options = {}) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_format', targetFormat);
    
    // Add optional parameters
    if (options.encoding) formData.append('encoding', options.encoding);
    
    // HTML specific options
    if (options.enable_preview !== undefined) formData.append('enable_preview', options.enable_preview);
    if (options.codeMode !== undefined) formData.append('code_mode', options.codeMode);
    if (options.css_handling) formData.append('css_handling', options.css_handling);
    if (options.compress_css !== undefined) formData.append('compress_css', options.compress_css);
    if (options.custom_css) formData.append('custom_css', options.custom_css);
    if (options.remove_scripts !== undefined) formData.append('remove_scripts', options.remove_scripts);
    if (options.remove_comments !== undefined) formData.append('remove_comments', options.remove_comments);
    if (options.compress_html !== undefined) formData.append('compress_html', options.compress_html);
    if (options.remove_empty_tags !== undefined) formData.append('remove_empty_tags', options.remove_empty_tags);
    if (options.page_size) formData.append('page_size', options.page_size);
    if (options.orientation) formData.append('orientation', options.orientation);
    
    // Image quality options
    if (options.quality !== undefined) formData.append('quality', options.quality);
    if (options.backgroundColor) formData.append('background_color', options.backgroundColor);
    
    // Watermark options
    if (options.watermark_text) formData.append('watermark_text', options.watermark_text);
    if (options.watermark_opacity !== undefined) formData.append('watermark_opacity', options.watermark_opacity);
    if (options.watermark_size !== undefined) formData.append('watermark_size', options.watermark_size);
    if (options.watermark_color) formData.append('watermark_color', options.watermark_color);
    if (options.watermark_angle !== undefined) formData.append('watermark_angle', options.watermark_angle);
    if (options.watermark_position) formData.append('watermark_position', options.watermark_position);
    
    // CSV options
    if (options.csv_delimiter) formData.append('csv_delimiter', options.csv_delimiter);
    
    // PDF page selection
    if (options.pdf_page_selection) formData.append('pdf_page_selection', options.pdf_page_selection);
    if (options.pdf_page_range) formData.append('pdf_page_range', options.pdf_page_range);
    
    // GIF animation options
    if (options.animation_delay !== undefined) formData.append('animation_delay', options.animation_delay);
    if (options.loop_animation !== undefined) formData.append('loop_animation', options.loop_animation);

    const apiBaseUrl = await getApiBaseUrl();
    const ready = await ensureBackendReady(apiBaseUrl);
    if (!ready) {
      throw new Error('后端服务未启动');
    }
    
    // 创建一个带超时的 AbortController
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15 * 60 * 1000); // 15分钟超时
    
    // 如果提供了外部 signal，则监听其 abort 事件
    let externalAbortHandler = null;
    if (options.signal) {
      externalAbortHandler = () => controller.abort();
      options.signal.addEventListener('abort', externalAbortHandler);
    }
    
    try {
      const response = await fetch(`${apiBaseUrl}/api/convert/general`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        headers: buildAuthHeaders(),
      });

      clearTimeout(timeoutId);
      return await handleResponse(response, apiBaseUrl, file);
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('转换超时，请稍后重试或联系管理员');
      }
      throw error;
    } finally {
      if (options.signal && externalAbortHandler) {
        try { options.signal.removeEventListener('abort', externalAbortHandler); } catch {}
      }
    }
  } catch (error) {
    console.error('Conversion error:', error);
    throw error;
  }
};

/**
 * 批量打包下载
 * @param {string[]} files - 文件名列表
 * @returns {Promise<Blob>} ZIP 文件 Blob
 */
export const batchDownload = async (files) => {
  try {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    const apiBaseUrl = await getApiBaseUrl();
    const ready = await ensureBackendReady(apiBaseUrl);
    if (!ready) {
      throw new Error('后端服务未启动');
    }
    
    const response = await fetch(`${apiBaseUrl}/api/batch-download`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error('Batch download failed');
    }
    
    return await response.blob();
  } catch (error) {
    console.error('Batch download error:', error);
    throw error;
  }
};

/**
 * 健康检查
 */
export const healthCheck = async () => {
  try {
    const apiBaseUrl = await getApiBaseUrl();
    const ready = await ensureBackendReady(apiBaseUrl);
    if (!ready) {
      throw new Error('后端服务未启动');
    }
    const response = await fetch(`${apiBaseUrl}/api/health`);
    return await response.json();
  } catch (error) {
    console.error('Health check error:', error);
    throw error;
  }
};
