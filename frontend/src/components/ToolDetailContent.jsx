import { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import { motion } from 'framer-motion';
import { convertJSON, convertXML, convertGeneral, getApiBaseUrl, batchDownload } from '../services/api';
import { categories } from '../data';
import { useUserStore } from '../stores/useUserStore';
import { createSafeTranslator } from '../utils/safeTranslation';
import { persistCurrentToolSnapshot } from '../utils/authStorage';
import {
  clearSelectedConversionResults,
  getSelectedFileQueue,
} from '../utils/fileSelection';

// 文件类型映射表
const FILE_TYPE_MAP = {
  'PDF': ['.pdf'],
  'DOCX': ['.docx'],
  'DOC': ['.docx'],
  'HTML': ['.html', '.htm'],
  'JSON': ['.json'],
  'XML': ['.xml'],
  'TXT': ['.txt', '.text'],
  'CSV': ['.csv'],
  'XLSX': ['.xlsx', '.xls'],
  'YAML': ['.yaml', '.yml'],
  'YML': ['.yaml', '.yml'],
  'MD': ['.md', '.markdown'],
  'MARKDOWN': ['.md', '.markdown'],
  'RTF': ['.rtf'],
  'EPUB': ['.epub'],
  'PPT': ['.ppt', '.pptx'],
  'PPTX': ['.ppt', '.pptx'],
  'ODT': ['.odt'],
  'SVG': ['.svg'],
  'PNG': ['.png'],
  'JPG': ['.jpg', '.jpeg'],
  'JPEG': ['.jpg', '.jpeg'],
  'GIF': ['.gif'],
  'BMP': ['.bmp'],
  'WEBP': ['.webp'],
  'TIFF': ['.tiff', '.tif'],
  'EXCEL': ['.xlsx', '.xls'],
  'Excel': ['.xlsx', '.xls'],
  'WORD': ['.docx', '.doc'],
  'IMAGE': ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
};

function ToolDetailContent({ toolName, onBack }) {
  const { t: rawT, i18n } = useTranslation();
  const fallbackT = i18n.getFixedT('en');
  const t = createSafeTranslator(rawT, fallbackT, i18n.language);
  const MotionDiv = motion.div;
  const navigate = useNavigate();
  const location = useLocation();
  const requireFeatureAccess = useUserStore((state) => state.requireFeatureAccess);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionResults, setConversionResults] = useState({}); // Map of file index to result
  const [showDownloadModal, setShowDownloadModal] = useState(false);
  const [downloadingFileId, setDownloadingFileId] = useState(null); // 记录要下载的文件ID
  const [progress, setProgress] = useState({ current: 0, total: 0, percent: 0 });
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [estimatedTime, setEstimatedTime] = useState(null);
  const [currentStage, setCurrentStage] = useState('');
  const conversionStartRef = useRef(null);
  const abortControllerRef = useRef(null);
  const [isWatermarkExpanded, setIsWatermarkExpanded] = useState(false);
  const [isPdfPagesExpanded, setIsPdfPagesExpanded] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    preview: false,
    css: false,
    cleanup: false
  });

  // 监听 toolName 变化,切换功能时清空文件列表
  useEffect(() => {
    setFiles([]);
    setSelectedFiles(new Set());
    setConversionResults({});
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (folderInputRef.current) folderInputRef.current.value = '';

    // 持久化当前工具快照，以便账户中心显示
    persistCurrentToolSnapshot(location.pathname, toolName);
  }, [toolName, location.pathname]);
  const [watermarkOptions, setWatermarkOptions] = useState({
    text: '',
    font: 'Arial Bold',
    color: '#cccccc',
    size: 40,
    opacity: 30,
    angle: 45,
    position: 'center'
  });
  const [convertOptions, setConvertOptions] = useState({
    quality: 85,
    backgroundColor: '#ffffff',
    csvDelimiter: t('toolDetail.options.comma'),
    yamlIndent: 2,
    orientation: t('toolDetail.options.landscape'),
    pdfPageSelection: t('toolDetail.options.all_pages'),
    animationDelay: 100,
    loopAnimation: true,
    speechSpeed: 1.0,
    speechPitch: 1.0,
    pageSize: 'A4',
    excelOrientation: 'auto',
    excelScaleMode: 'fit_width',
    docxPdfPageRange: '',
    pdfCustomRange: ''
  });
  const [htmlOptions, setHtmlOptions] = useState({
    enablePreview: false,
    codeMode: false,  // 默认不勾选代码模式（即默认渲染模式）
    cssHandling: t('toolDetail.options.keep_all_css'),
    compressCss: false,
    customCss: '',
    removeScripts: true,
    removeComments: false,
    compressHtml: false,
    removeEmptyTags: false,
    pageSize: 'A4',
    orientation: t('toolDetail.options.portrait')
  });

  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [isToolDropdownOpen, setIsToolDropdownOpen] = useState(false);

  const toggleSection = useCallback((section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  }, []);

  const parseToolName = useCallback((name) => {
    const parts = name.split(' To ');
    if (parts.length === 2) {
      return { source: parts[0], target: parts[1] };
    }
    return { source: 'FILE', target: 'FILE' };
  }, []);

  const { source, target } = useMemo(() => parseToolName(toolName), [toolName, parseToolName]);

  // 获取允许的文件扩展名
  const allowedExtensions = useMemo(() => {
    return FILE_TYPE_MAP[source] || [];
  }, [source]);

  // 获取 accept 属性值（用于 input）
  const acceptAttribute = useMemo(() => {
    return allowedExtensions.join(',');
  }, [allowedExtensions]);

  // 验证文件类型
  const isValidFileType = useCallback((file) => {
    if (allowedExtensions.length === 0) return true; // 如果没有限制，允许所有文件
    const fileName = file.name.toLowerCase();
    return allowedExtensions.some(ext => fileName.endsWith(ext.toLowerCase()));
  }, [allowedExtensions]);

  const formatToolDisplayName = useCallback((name) => {
    const parts = name.split(' To ');
    if (parts.length === 2) {
      return t('toolDetail.breadcrumb_current', {
        source: parts[0],
        target: parts[1],
      });
    }
    return name;
  }, [t]);

  const { siblingTools } = useMemo(() => {
    const majorCategory = categories.major_functions || [];
    let section = null;
    for (const s of majorCategory) {
      if (s.tools && s.tools.some((t) => t.name === toolName)) {
        section = s;
        break;
      }
    }
    return {
      siblingTools: section ? section.tools.map((t) => t.name) : []
    };
  }, [toolName]);

  // Determine if the right sidebar should be shown
  let showSidebar = source === 'JSON' 
    ? ['CSV', 'JPG', 'YAML'].includes(target)
    : source === 'TXT'
    ? ['SPEECH', 'PDF', 'JPG', 'PNG'].includes(target)
    : source === 'XML'
    ? ['PDF', 'JPG', 'CSV', 'YAML'].includes(target)
    : source === 'Excel'
    ? ['PDF', 'PNG', 'JPG', 'JPEG', 'Image'].includes(target)
    : source === 'PPT'
    ? ['PNG', 'JPG', 'JPEG', 'Image'].includes(target)
    : true;

  if (source === 'DOCX' && (target === 'TXT' || target === 'EPUB' || target === 'PDF')) {
    showSidebar = false;
  }

  const handleToolBreadcrumbToggle = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!siblingTools.length) return;
    setIsToolDropdownOpen((prev) => !prev);
  };

  const handleBreadcrumbToolSelect = (name) => {
    setIsToolDropdownOpen(false);
    if (name === toolName) return;
    const parts = name.split(' To ');
    if (parts.length !== 2) return;
    const src = parts[0].toLowerCase();
    const tgt = parts[1].toLowerCase();
    navigate(`/tool/${src}/${tgt}`);
  };

  const handleHomeClick = () => {
    if (onBack) {
      onBack();
    } else {
      console.log('Navigating to home page');
      // Use setTimeout to ensure the click event is properly handled
      setTimeout(() => {
        navigate('/');
      }, 0);
    }
  };

  const handleConverterClick = () => {
    const formatRoutes = {
      'DOC': '/tools/docx',
      'DOCX': '/tools/docx',
      'HTML': '/tools/html',
      'JSON': '/tools/json',
      'PDF': '/tools/pdf',
      'PPT': '/tools/ppt',
      'PPTX': '/tools/ppt',
      'TXT': '/tools/txt',
      'XML': '/tools/xml',
      'XLS': '/tools/excel',
      'XLSX': '/tools/excel',
      'EXCEL': '/tools/excel'
    };

    const route = formatRoutes[source];
    if (route) {
      console.log(`Navigating to ${route} for source ${source}`);
      // Use setTimeout to ensure the click event is properly handled
      setTimeout(() => {
        navigate(route);
      }, 0);
    } else {
      console.warn(`No route found for source format: ${source}, falling back to home page`);
      setTimeout(() => {
        navigate('/');
      }, 0);
    }
  };

  const handlePreviewHtml = () => {
    if (!htmlOptions.enablePreview) {
      toast.error(t('toolDetail.messages.select_preview_first'));
      return;
    }

    if (files.length === 0) {
      toast.error(t('toolDetail.messages.upload_html_first'));
      return;
    }

    // Preview the first file
    const file = files[0].file;
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewContent(e.target.result);
      setShowPreviewModal(true);
    };
    reader.readAsText(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    if (e) {
      e.stopPropagation();
    }
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    
    // 验证文件类型
    const validFiles = droppedFiles.filter(isValidFileType);
    const invalidFiles = droppedFiles.filter(file => !isValidFileType(file));
    
    // 显示错误提示
    if (invalidFiles.length > 0) {
      const invalidNames = invalidFiles.map(f => f.name).join(', ');
      toast.error(
        t('toolDetail.messages.invalid_file_type', { format: source, extensions: allowedExtensions.join(', '), names: invalidNames }),
        { duration: 4000 }
      );
    }
    
    // 添加有效文件
    if (validFiles.length > 0) {
      const fileObjects = validFiles.map(file => ({
        id: Date.now() + Math.random().toString(36).substr(2, 9),
        file
      }));
      setFiles(prev => [...prev, ...fileObjects]);
      
      if (invalidFiles.length === 0) {
        toast.success(t('toolDetail.messages.files_added_success', { count: validFiles.length }));
      }
    }
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    
    // 验证文件类型
    const validFiles = selectedFiles.filter(isValidFileType);
    const invalidFiles = selectedFiles.filter(file => !isValidFileType(file));
    
    // 显示错误提示
    if (invalidFiles.length > 0) {
      const invalidNames = invalidFiles.map(f => f.name).join(', ');
      toast.error(
        t('toolDetail.messages.invalid_file_type', { format: source, extensions: allowedExtensions.join(', '), names: invalidNames }),
        { duration: 4000 }
      );
    }
    
    // 添加有效文件
    if (validFiles.length > 0) {
      const fileObjects = validFiles.map(file => ({
        id: Date.now() + Math.random().toString(36).substr(2, 9),
        file
      }));
      setFiles(prev => [...prev, ...fileObjects]);
      
      if (invalidFiles.length === 0) {
        toast.success(t('toolDetail.messages.files_added_success', { count: validFiles.length }));
      }
    }
    
    // Reset input
    e.target.value = '';
  };

  const handleFolderSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    
    // 验证文件类型
    const validFiles = selectedFiles.filter(isValidFileType);
    const invalidFiles = selectedFiles.filter(file => !isValidFileType(file));
    
    // 显示错误提示
    if (invalidFiles.length > 0) {
      toast.error(
        t('toolDetail.messages.folder_invalid_filtered', { count: invalidFiles.length }),
        { duration: 4000 }
      );
    }
    
    // 添加有效文件
    if (validFiles.length > 0) {
      const fileObjects = validFiles.map(file => ({
        id: Date.now() + Math.random().toString(36).substr(2, 9),
        file
      }));
      setFiles(prev => [...prev, ...fileObjects]);
      toast.success(t('toolDetail.messages.files_added_success', { count: validFiles.length }));
    } else if (selectedFiles.length > 0) {
      toast.error(t('toolDetail.messages.folder_no_valid_files', { source }));
    }
    
    // Reset input
    e.target.value = '';
  };

  const handleRemoveFile = (id) => {
    setFiles(prev => prev.filter(f => f.id !== id));
    setSelectedFiles(prev => {
      if (!prev.has(id)) return prev;
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    // Also remove from conversion results
    setConversionResults(prev => {
      const newResults = { ...prev };
      delete newResults[id];
      return newResults;
    });
  };

  const handleClearAll = () => {
    setFiles([]);
    setSelectedFiles(new Set());
    setConversionResults({});
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (folderInputRef.current) folderInputRef.current.value = '';
  };

  // ---- 选择态 & 批量操作 ----
  const handleSelectAll = useCallback(() => {
    setSelectedFiles(new Set(files.map(f => f.id)));
  }, [files]);

  const handleDeselectAll = useCallback(() => {
    setSelectedFiles(new Set());
  }, []);

  const handleToggleFileSelect = useCallback((fileId) => {
    setSelectedFiles(prev => {
      const next = new Set(prev);
      if (next.has(fileId)) next.delete(fileId);
      else next.add(fileId);
      return next;
    });
  }, []);

  const handleDeleteSelected = useCallback(() => {
    setFiles(prev => prev.filter(f => !selectedFiles.has(f.id)));
    setConversionResults(prev => { const n = { ...prev }; selectedFiles.forEach(id => delete n[id]); return n; });
    setSelectedFiles(new Set());
  }, [selectedFiles]);

  const handleDownloadAll = async (e) => {
    e.stopPropagation();
    const hasDownloadableFiles = Object.values(conversionResults).some(res => res && !res.error && res.download_url);
    if (!hasDownloadableFiles) {
      toast.error(t('toolDetail.messages.no_downloadable_files'));
      return;
    }
    // Single file download: skip modal, download directly
    const downloadable = Object.values(conversionResults).filter(
      res => res && !res.error && res.download_url && res.download_url !== '#' && !res.download_url.startsWith('#')
    );
    if (downloadable.length === 1) {
      setDownloadingFileId(null);
      // Direct download – build url and trigger save
      const apiBaseUrl = await getApiBaseUrl();
      const res = downloadable[0];
      const url = `${apiBaseUrl}${res.download_url}`;
      const filename = res.display_name || decodeURIComponent(res.download_url.split('/').pop()) || `file-${Date.now()}`;
      if (window.electronAPI) {
        const dirPath = await window.electronAPI.selectDirectory();
        if (dirPath) {
          await window.electronAPI.downloadFile(url, dirPath, filename);
          toast.success(t('toolDetail.messages.download_success'));
        }
      } else if (window.showSaveFilePicker) {
        try {
          const response = await fetch(url);
          const blob = await response.blob();
          const handle = await window.showSaveFilePicker({ suggestedName: filename });
          const writable = await handle.createWritable();
          await writable.write(blob);
          await writable.close();
        } catch (err) {
          if (err.name !== 'AbortError') saveAs(url, filename);
        }
      } else {
        saveAs(url, filename);
      }
      return;
    }
    setDownloadingFileId(null); // 清空单个文件ID，表示下载全部
    setShowDownloadModal(true);
  };

  const handleSingleFileDownload = async (e, fileId) => {
    e.preventDefault();
    e.stopPropagation();
    const result = conversionResults[fileId];
    if (!result || result.error || !result.download_url) return;
    setDownloadingFileId(fileId);
    const apiBaseUrl = await getApiBaseUrl();
    const url = `${apiBaseUrl}${result.download_url}`;
    const filename = result.display_name || decodeURIComponent(result.download_url.split('/').pop()) || `file-${Date.now()}`;
    if (window.electronAPI) {
      const dirPath = await window.electronAPI.selectDirectory();
      if (dirPath) {
        await window.electronAPI.downloadFile(url, dirPath, filename);
        toast.success(t('toolDetail.messages.download_success'));
      }
    } else if (window.showSaveFilePicker) {
      try {
        const response = await fetch(url);
        const blob = await response.blob();
        const handle = await window.showSaveFilePicker({ suggestedName: filename });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
      } catch (err) {
        if (err.name !== 'AbortError') saveAs(url, filename);
      }
    } else {
      saveAs(url, filename);
    }
  };

  const handleBatchDownload = async () => {
    // 如果是单个文件下载
    let downloadableFiles;
    if (downloadingFileId) {
      const result = conversionResults[downloadingFileId];
      if (result && !result.error && result.download_url) {
        downloadableFiles = [result];
      } else {
        downloadableFiles = [];
      }
    } else {
      // 下载全部文件
      downloadableFiles = Object.values(conversionResults)
        .filter(res => res && !res.error && res.download_url && res.download_url !== '#' && !res.download_url.startsWith('#'));
    }
      
    if (downloadableFiles.length === 0) return;
    
    setShowDownloadModal(false);
    const apiBaseUrl = await getApiBaseUrl();

            // 1. Electron Environment: Use IPC
            if (window.electronAPI) {
              try {
                const dirPath = await window.electronAPI.selectDirectory();
                if (!dirPath) return; // User cancelled

                const toastId = toast.loading(t('toolDetail.messages.saving_files'));
                let successCount = 0;
                let lastError = null;

                for (const res of downloadableFiles) {
                  try {
                    if (!res.download_url) {
                        console.error('[BatchDownload] Missing download_url in response', res);
                        continue; 
                    }
                    const url = `${apiBaseUrl}${res.download_url}`;
                    
                    // 使用 display_name（如果有），否则从 URL 提取
                    const filename = res.display_name || (res.download_url.split('/').pop() ? decodeURIComponent(res.download_url.split('/').pop()) : `file-${Date.now()}.dat`);
                    
                    // Use new main process download logic
                    try {
                      const result = await window.electronAPI.downloadFile(url, dirPath, filename);
                      if (!result.success) throw new Error(result.error);
                      successCount++;
                    } catch (ipcError) {
                      if (ipcError.message && ipcError.message.includes('No handler registered')) {
                         throw new Error(t('toolDetail.messages.restart_required'));
                      }
                      throw ipcError;
                    }
                  } catch (err) {
                    console.error('Electron save error:', err);
                    lastError = err;
                    // 如果是需要重启的错误，直接中断循环并抛出，让外层捕获显示
                    if (err.message === t('toolDetail.messages.restart_required')) {
                        throw err;
                    }
                  }
                }

                if (successCount > 0) {
                  toast.success(t('toolDetail.messages.save_success', { count: successCount }), { id: toastId });
                } else {
                  toast.error(t('toolDetail.messages.save_failed', { error: lastError ? lastError.message : t('toolDetail.messages.unknown_error') }), { id: toastId });
                }
                return;

              } catch (err) {
                 console.error('Electron dialog error:', err);
                 toast.error(t('toolDetail.messages.save_operation_failed'));
                 return;
              }
            }

            // 2. Web Environment: Try File System Access API
    if (window.showDirectoryPicker) {
      try {
        const dirHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
        const toastId = toast.loading(t('toolDetail.messages.saving_files'));
        
        let successCount = 0;
        let lastError = null;
        for (const res of downloadableFiles) {
          try {
            const url = `${apiBaseUrl}${res.download_url}`;
            console.log('Downloading from:', url);
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Fetch failed: ${response.status} for ${url}`);
            const blob = await response.blob();
            // 使用 display_name（如果有），否则从 URL 提取
            const filename = res.display_name || (res.download_url.split('/').pop() ? decodeURIComponent(res.download_url.split('/').pop()) : `file-${Date.now()}.dat`);
            
            console.log('Saving to file:', filename);
            const fileHandle = await dirHandle.getFileHandle(filename, { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(blob);
            await writable.close();
            successCount++;
          } catch (err) {
            console.error('File write error:', err);
            lastError = err;
          }
        }
        
        if (successCount > 0) {
            toast.success(t('toolDetail.messages.save_success', { count: successCount }), { id: toastId });
        } else {
            toast.error(t('toolDetail.messages.save_failed', { error: lastError ? `${lastError.name}: ${lastError.message}` : t('toolDetail.messages.unknown_error') }), { id: toastId });
        }
        return;
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Directory picker error:', err);
          toast.error(t('toolDetail.messages.cannot_access_folder'));
        } else {
            return; // User cancelled
        }
      }
    }
    
    // Fallback: Trigger downloads with a slight delay
    toast.success(t('toolDetail.messages.batch_download_started'));
    downloadableFiles.forEach((res, index) => {
      setTimeout(() => {
        const link = document.createElement('a');
        link.href = `${apiBaseUrl}${res.download_url}`;
        // 使用 display_name 作为下载文件名
        link.download = res.display_name || ''; 
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }, index * 500);
    });
  };

  const handleZipDownload = async () => {
    // 如果是单个文件下载
    let downloadableFiles;
    if (downloadingFileId) {
      const result = conversionResults[downloadingFileId];
      if (result && !result.error && result.download_url) {
        downloadableFiles = [result];
      } else {
        downloadableFiles = [];
      }
    } else {
      // 下载全部文件
      downloadableFiles = Object.values(conversionResults)
        .filter(res => res && !res.error && res.download_url && res.download_url !== '#' && !res.download_url.startsWith('#'));
    }
      
    if (downloadableFiles.length === 0) return;

    setShowDownloadModal(false);
    const toastId = toast.loading(t('toolDetail.messages.packaging_files'));
    
    try {
      // 收集所有文件名
      const filenames = downloadableFiles.map(res => {
        // 从 URL 中提取文件名
        return res.download_url.split('/').pop();
      });

      // 调用后端批量下载接口
      const blob = await batchDownload(filenames);
      
      const filename = `${toolName}-converted-${Date.now()}.zip`;

      // 1. Electron Environment
      if (window.electronAPI) {
        try {
          const filePath = await window.electronAPI.showSaveDialog({
            defaultPath: filename,
            filters: [{ name: 'ZIP Archive', extensions: ['zip'] }]
          });
          
          if (filePath) {
            const arrayBuffer = await blob.arrayBuffer();
            const result = await window.electronAPI.saveFile(filePath, arrayBuffer);
            if (result.success) {
               toast.success(t('toolDetail.messages.zip_download_success'), { id: toastId });
            } else {
               throw new Error(result.error);
            }
          } else {
            toast.dismiss(toastId); // User cancelled
          }
          return;
        } catch (err) {
          console.error('Electron zip save error:', err);
          toast.error(t('toolDetail.messages.save_failed', { error: err.message || t('toolDetail.messages.unknown_error') }), { id: toastId });
          return;
        }
      }

      // 2. Web Environment: Try File System Access API for Save
      if (window.showSaveFilePicker) {
          try {
              const handle = await window.showSaveFilePicker({
                  suggestedName: filename,
                  types: [{
                      description: 'ZIP Archive',
                      accept: {'application/zip': ['.zip']},
                  }],
              });
              const writable = await handle.createWritable();
              await writable.write(blob);
              await writable.close();
              toast.success(t('toolDetail.messages.zip_download_success'), { id: toastId });
              return;
          } catch (err) {
              if (err.name === 'AbortError') {
                  toast.dismiss(toastId);
                  return; 
              }
              // If error, fall through to saveAs
              console.error('Save picker error:', err);
          }
      }

      saveAs(blob, filename);
      
      toast.success(t('toolDetail.messages.zip_download_success'), { id: toastId });
    } catch (error) {
      console.error('Zip download error:', error);
      toast.error(t('toolDetail.messages.zip_download_failed'), { id: toastId });
    }
  };

  const validatePageRange = (range) => {
    if (!range || !range.trim()) return false;
    // Allow "1", "1,3", "1-5", "1,3-5", "1, 3, 5"
    // Remove spaces for regex check
    const cleanRange = range.replace(/\s/g, '');
    // Check for valid characters (digits, comma, hyphen)
    if (!/^[\d,-]+$/.test(cleanRange)) return false;
    
    // Check structure
    const parts = cleanRange.split(',');
    for (const part of parts) {
      if (!part) continue; // Handle trailing comma
      if (part.includes('-')) {
        const ranges = part.split('-');
        if (ranges.length !== 2) return false; // "1-2-3" is invalid
        const start = parseInt(ranges[0]);
        const end = parseInt(ranges[1]);
        if (isNaN(start) || isNaN(end)) return false;
        if (start > end) return false; // "5-1" is invalid (though backend might handle swap, better to enforce order)
      } else {
        if (isNaN(parseInt(part))) return false;
      }
    }
    return true;
  };

  const validateHexColor = (color) => {
    if (!color) return true; // Optional or default
    return /^#([0-9A-Fa-f]{3}){1,2}$/.test(color);
  };

  const handleCancelConversion = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsConverting(false);
      toast.error(t('toolDetail.messages.conversion_cancelled'));
    }
  }, [t]);

  const handleConvert = async () => {
    const filesToConvert = getSelectedFileQueue(files, selectedFiles);
    if (filesToConvert.length === 0) return;

    const totalEstimate = filesToConvert.reduce((sum, f) => {
      const sizeMB = f.file.size / (1024 * 1024);
      if (/PPT|Video|Excel/i.test(source)) return sum + Math.ceil(sizeMB * 3 + 5);
      if (/PDF/.test(source) && /PNG|JPG|Image/.test(target)) return sum + Math.ceil(sizeMB * 2 + 3);
      return sum + Math.ceil(sizeMB * 1.5 + 2);
    }, 0);
    setEstimatedTime(totalEstimate);
    setCurrentStage(t('toolDetail.stage_starting'));
    conversionStartRef.current = Date.now();

    // Validation
    // PDF/DOCX Page Range
    if (source === 'PDF' && convertOptions.pdfPageSelection !== t('toolDetail.options.all_pages')) {
      if (!validatePageRange(convertOptions.pdfCustomRange)) {
        toast.error(t('toolDetail.messages.pdf_page_range_invalid'));
        return;
      }
    }

    if (source === 'DOCX' && target === 'PDF' && convertOptions.docxPdfPageRange) {
      if (!validatePageRange(convertOptions.docxPdfPageRange)) {
        toast.error(t('toolDetail.messages.docx_page_range_invalid'));
        return;
      }
    }

    // GIF Delay
    if (target === 'GIF') {
      const delay = parseInt(convertOptions.animationDelay);
      if (isNaN(delay) || delay < 10 || delay > 5000) {
        toast.error(t('toolDetail.messages.animation_delay_invalid'));
        return;
      }
    }

    // Background Color (Global check if present in current options)
    if (convertOptions.backgroundColor && !validateHexColor(convertOptions.backgroundColor)) {
      toast.error(t('toolDetail.messages.background_color_invalid'));
      return;
    }

    // Watermark Color
    if (isWatermarkExpanded && watermarkOptions.color && !validateHexColor(watermarkOptions.color)) {
      toast.error(t('toolDetail.messages.watermark_color_invalid'));
      return;
    }

    const requiresNoWatermarkPermission = ['PDF', 'PNG', 'JPG', 'JPEG', 'GIF', 'SVG', 'BMP', 'TIFF', 'WEBP', 'Image'].includes(target)
      && !String(watermarkOptions.text || '').trim();

    const hasFeatureAccess = requireFeatureAccess({
      navigate,
      returnTo: `${location.pathname}${location.search}${location.hash}`,
      filesCount: filesToConvert.length,
      disableWatermark: requiresNoWatermarkPermission,
      t,
    });

    if (!hasFeatureAccess) {
      return;
    }

    setIsConverting(true);
    setConversionResults((previousResults) => (
      clearSelectedConversionResults(previousResults, selectedFiles)
    ));
    setProgress({ current: 0, total: filesToConvert.length, percent: 0 });
    
    // Create new AbortController
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;
    
    // 检查是否是PPT转视频，给出特殊提示
    const isPptToVideo = (source === 'PPT' || source === 'PPTX') && target === 'Video';
    if (isPptToVideo && filesToConvert.length > 0) {
      toast(t('toolDetail.messages.ppt_video_wait'), { 
        duration: 4000,
        icon: '⏱️'
      });
    }
    
    let successCount = 0;
    let failureCount = 0;
    const toastId = toast.loading(isPptToVideo ? t('toolDetail.messages.converting_video_wait') : t('toolDetail.messages.processing_files'));

    try {
      // Loop through the selected conversion queue
      for (let i = 0; i < filesToConvert.length; i++) {
        if (signal.aborted) {
          throw new Error(t('toolDetail.messages.operation_cancelled'));
        }

        setCurrentStage(t('toolDetail.stage_converting', { current: i + 1, total: filesToConvert.length }));
        const fileObj = filesToConvert[i];
        const file = fileObj.file;
        
        try {
          let result;
          if (source === 'JSON' && (target === 'YAML' || target === 'YML' || target === 'XML')) {
            const options = { signal };
            if (target === 'YAML' || target === 'YML') {
              options.indent = convertOptions.yamlIndent;
            }
            result = await convertJSON(file, target.toLowerCase(), options);
          } else if (source === 'XML' && (target === 'JSON' || target === 'YAML' || target === 'YML')) {
            const options = { signal };
            if (target === 'YAML' || target === 'YML') {
              options.indent = convertOptions.yamlIndent;
            }
            if (target === 'JSON') {
              options.indent = convertOptions.yamlIndent;
            }
            result = await convertXML(file, target.toLowerCase(), options);
          } else if (
            // DOCX 转换
            (source === 'DOCX' && ['TXT', 'PDF', 'PNG', 'JPG', 'EPUB', 'Excel', 'PPT'].includes(target)) ||
            // HTML 转换
            (source === 'HTML' && ['PDF', 'TXT', 'TEXT', 'MARKDOWN', 'MD', 'PNG', 'JPG', 'JPEG', 'DOCX', 'DOC', 'WORD', 'JSON', 'GIF', 'SVG'].includes(target)) ||
            // PDF 转换
            (source === 'PDF' && ['TXT', 'DOCX', 'DOC', 'HTML', 'PNG', 'JPG', 'JPEG', 'BMP', 'TIFF', 'JSON', 'BASE64', 'MD', 'SVG', 'EPUB', 'GIF', 'WEBP', 'PPT', 'PPTX', 'RTF', 'Excel'].includes(target)) ||
            // TXT 转换
            (source === 'TXT' && ['PDF', 'HTML', 'PNG', 'JPG', 'JPEG', 'MP3', 'WAV', 'SPEECH', 'ASCII', 'BINARY', 'BIN', 'CSV', 'HEX'].includes(target)) ||
            // JSON 转换
            (source === 'JSON' && ['CSV', 'HTML', 'PDF', 'BASE64', 'PNG', 'JPG', 'JPEG', 'SVG', 'Excel'].includes(target)) ||
            // XML 转换
            (source === 'XML' && ['CSV', 'HTML', 'TXT', 'TEXT', 'PDF', 'XLSX', 'PNG', 'JPG', 'JPEG', 'SVG'].includes(target)) ||
            // PPT 转换
            (source === 'PPT' && ['PDF', 'Excel', 'Image', 'Video', 'PNG', 'JPG', 'JPEG'].includes(target)) ||
            // Excel 转换
            (source === 'Excel' && ['PDF', 'Image', 'PPT', 'HTML', 'PNG', 'JPG', 'JPEG'].includes(target))
          ) {
            let targetFormat = target.toLowerCase();
            if (target === 'Excel') targetFormat = 'xlsx';
            if (target === 'Image') targetFormat = 'png'; // Default to png for Image generic
            if (target === 'Video') targetFormat = 'mp4';
            if (target === 'PPT') targetFormat = 'pptx';
            if (target === 'HTML') targetFormat = 'html';
            
            if (target === 'MARKDOWN') targetFormat = 'md';
            if (source === 'HTML' && target === 'TEXT') targetFormat = 'txt';
            if (source === 'XML' && target === 'TEXT') targetFormat = 'txt';
            if (target === 'WORD') targetFormat = 'docx';
            if (target === 'SPEECH') targetFormat = 'mp3';  // 默认转换为 MP3
            
            // Prepare options based on source format
            const options = { signal };
            
            if (source === 'DOCX') {
              if (['PNG', 'JPG', 'JPEG'].includes(target)) {
                options.quality = convertOptions.quality;
                options.backgroundColor = convertOptions.backgroundColor;
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
              if (target === 'PDF') {
                options.page_size = convertOptions.pageSize;
                options.orientation = convertOptions.orientation;
                options.page_range = convertOptions.docxPdfPageRange;
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
            }
            
            if (source === 'HTML') {
              options.enable_preview = htmlOptions.enablePreview;
              options.codeMode = htmlOptions.codeMode;  // 直接使用 codeMode
              options.css_handling = htmlOptions.cssHandling;
              options.compress_css = htmlOptions.compressCss;
              options.custom_css = htmlOptions.customCss;
              options.remove_scripts = htmlOptions.removeScripts;
              options.remove_comments = htmlOptions.removeComments;
              options.compress_html = htmlOptions.compressHtml;
              options.remove_empty_tags = htmlOptions.removeEmptyTags;
              options.page_size = htmlOptions.pageSize;
              options.orientation = htmlOptions.orientation;
              if (target === 'PDF') {
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
              
              // 图片输出选项
              if (['PNG', 'JPG', 'JPEG', 'GIF', 'SVG'].includes(target)) {
                options.quality = convertOptions.quality;
                options.backgroundColor = convertOptions.backgroundColor;
                // 水印选项
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
            }
            
            // PDF specific options
            if (source === 'PDF') {
              options.quality = convertOptions.quality;
              options.pdf_page_selection = convertOptions.pdfPageSelection;
              if (convertOptions.pdfPageSelection !== t('toolDetail.options.all_pages')) {
                options.pdf_page_range = convertOptions.pdfCustomRange;
              }
              // 图片输出选项
              if (['PNG', 'JPG', 'JPEG', 'BMP', 'WEBP', 'SVG'].includes(target)) {
                options.backgroundColor = convertOptions.backgroundColor;
                // 水印选项
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
              if (target === 'GIF') {
                options.animation_delay = convertOptions.animationDelay;
                options.loop_animation = convertOptions.loopAnimation;
                options.backgroundColor = convertOptions.backgroundColor;
                // 水印选项
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
            }
            
            // TXT specific options
            if (source === 'TXT') {
              options.page_size = convertOptions.pageSize;
              options.orientation = convertOptions.orientation;
              // 图片输出选项
              if (['PNG', 'JPG', 'JPEG'].includes(target)) {
                options.quality = convertOptions.quality;
                options.backgroundColor = convertOptions.backgroundColor;
                // 水印选项
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
              if (target === 'SPEECH' || target === 'MP3' || target === 'WAV') {
                options.rate = Math.round(convertOptions.speechSpeed * 150);
                options.volume = 1.0;
                options.pitch = convertOptions.speechPitch;
              }
            }
            
            // JSON specific options
            if (source === 'JSON') {
              // 图片输出选项
              if (['PNG', 'JPG', 'JPEG', 'SVG'].includes(target)) {
                options.quality = convertOptions.quality;
                options.backgroundColor = convertOptions.backgroundColor;
                // 水印选项
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
              // PDF 输出选项
              if (target === 'PDF') {
                options.quality = convertOptions.quality;
                options.backgroundColor = convertOptions.backgroundColor;
              }
            }
            
            // XML specific options
            if (source === 'XML') {
              // 图片输出选项
              if (['PNG', 'JPG', 'JPEG', 'SVG'].includes(target)) {
                options.quality = convertOptions.quality;
                options.backgroundColor = convertOptions.backgroundColor;
                // 水印选项
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
              }
              // PDF 输出选项
              if (target === 'PDF') {
                options.quality = convertOptions.quality;
                options.backgroundColor = convertOptions.backgroundColor;
              }
            }
            
            // PPT specific options
            if (source === 'PPT') {
              if (['PNG', 'JPG', 'JPEG', 'Image'].includes(target)) {
                options.quality = convertOptions.quality;
                options.backgroundColor = convertOptions.backgroundColor;
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
            }

            // Excel specific options
            if (source === 'Excel') {
              if (['PDF', 'PNG', 'JPG', 'JPEG', 'Image'].includes(target)) {
                options.page_size = convertOptions.pageSize;
                options.excel_orientation = convertOptions.excelOrientation;
                options.excel_scale_mode = convertOptions.excelScaleMode;
              }
              if (['PNG', 'JPG', 'JPEG', 'Image'].includes(target)) {
                options.quality = convertOptions.quality;
                options.backgroundColor = convertOptions.backgroundColor;
                options.watermark_text = watermarkOptions.text;
                options.watermark_opacity = watermarkOptions.opacity;
                options.watermark_size = watermarkOptions.size;
                options.watermark_color = watermarkOptions.color;
                options.watermark_angle = watermarkOptions.angle;
                options.watermark_position = watermarkOptions.position;
              }
            }
            
            // CSV options (通用)
            if (target === 'CSV') {
              options.csv_delimiter = convertOptions.csvDelimiter;
            }
            
            console.log(`[Frontend] Converting ${file.name} to ${targetFormat} with options:`, options);
            result = await convertGeneral(file, targetFormat, options);
          } else {
            await new Promise(resolve => setTimeout(resolve, 500));
            throw new Error(t('toolDetail.messages.not_implemented'));
          }
          
          setConversionResults(prev => ({ ...prev, [fileObj.id]: result }));
          successCount++;
        } catch (err) {
          if (err.name === 'AbortError' || err.message === t('toolDetail.messages.operation_cancelled')) {
             throw err; // Re-throw cancellation to stop outer loop
          }
          console.error(`Error converting file ${file.name}:`, err);
          setConversionResults(prev => ({ ...prev, [fileObj.id]: { error: err.message } }));
          failureCount++;
        }
        
        // Update progress
        setProgress(prev => ({
          ...prev,
          current: i + 1,
          percent: Math.round(((i + 1) / filesToConvert.length) * 100)
        }));
      }
      
      if (failureCount === 0) {
        toast.success(t('toolDetail.messages.conversion_success', { count: successCount }), { id: toastId });
      } else {
        toast.error(t('toolDetail.messages.conversion_completed_mixed', { success: successCount, failed: failureCount }), { id: toastId });
      }
    } catch (err) {
      if (err.name === 'AbortError' || err.message === t('toolDetail.messages.operation_cancelled')) {
        console.log('Conversion cancelled');
        toast.dismiss(toastId);
        // 不显示错误，因为是用户取消
      } else {
        console.error(err);
        toast.error(t('toolDetail.messages.conversion_process_error', { error: err.message }), { id: toastId });
      }
    } finally {
      setIsConverting(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <MotionDiv
      className="feature-container"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
    >
      <div className="detail-header">
        <button className="back-button-circle detail-back-button" onClick={handleHomeClick}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5"/>
            <path d="M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <div className="header-left">
          <div className="breadcrumbs">
            <span className="breadcrumb-item" onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleHomeClick(); }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '4px', verticalAlign: 'middle' }}>
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
              {t('toolDetail.breadcrumb_home')}
            </span>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-item" onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleConverterClick(); }}>
              {t('toolDetail.breadcrumb_tools', { source })}
            </span>
            <span className="breadcrumb-separator">/</span>
            <span
              className={`breadcrumb-item active breadcrumb-item-dropdown ${isToolDropdownOpen ? 'open' : ''}`}
              onClick={handleToolBreadcrumbToggle}
            >
              <span>{t('toolDetail.breadcrumb_current', { source, target })}</span>
              {siblingTools.length > 0 && (
                <svg
                  className="breadcrumb-caret"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              )}
              {isToolDropdownOpen && siblingTools.length > 0 && (
                <div className="breadcrumb-dropdown-menu">
                  {siblingTools.map((name) => (
                    <button
                      key={name}
                      className={`breadcrumb-dropdown-item ${name === toolName ? 'active' : ''}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleBreadcrumbToolSelect(name);
                      }}
                    >
                      {formatToolDisplayName(name)}
                    </button>
                  ))}
                </div>
              )}
            </span>
          </div>
          
          <div className="detail-title-section">
            <h1 className="detail-title">{t('toolDetail.title', { source, target })}</h1>
            <p className="detail-desc">
              {t('toolDetail.description', { source, target })}
            </p>
          </div>
        </div>
      </div>

      <div className={`main-content ${!showSidebar ? 'no-sidebar' : ''}`}>
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileSelect} 
          style={{ display: 'none' }} 
          multiple 
          accept={acceptAttribute}
        />
        <input 
          type="file" 
          ref={folderInputRef} 
          onChange={handleFolderSelect} 
          style={{ display: 'none' }} 
          webkitdirectory=""
          directory=""
          multiple
        />

        <div 
          className={`upload-area ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current.click()}
        >
          <div className="upload-content">
            <div className="upload-icon-wrapper">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#00a3ff" strokeWidth="1.5">
                <path d="M17.5 19c2.5 0 4.5-2 4.5-4.5 0-2.3-1.7-4.1-3.9-4.5-.5-3.1-3.1-5.5-6.1-5.5-2.5 0-4.6 1.6-5.4 3.9C4.3 8.1 2 9.8 2 12.5 2 15 4 17 6.5 17h1" strokeLinecap="round" strokeLinejoin="round"/>
                <polyline points="12 12 12 16" strokeLinecap="round" strokeLinejoin="round"/>
                <polyline points="9 13 12 10 15 13" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="upload-text-row">
              <span className="upload-main-text">{t('toolDetail.upload_main_text', { source })}</span>
            </div>
            <p className="upload-sub-text">
              {t('toolDetail.upload_sub_text')} {allowedExtensions.length > 0 ? `(${allowedExtensions.join(', ')})` : ''}
            </p>
            <div className="upload-buttons-container">
              <button 
                className="select-file-btn" 
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current.click();
                }}
              >
                + {t('toolDetail.select_files')}
              </button>
              <button
                type="button"
                className="select-file-btn select-folder-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  folderInputRef.current?.click();
                }}
              >
                {t('toolDetail.select_upload_folder')}
              </button>
            </div>
          </div>
        </div>

        {showSidebar && (
          <div className="config-box-wrapper">
            <div className="config-header">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
              <span>{t('toolDetail.options.title')}</span>
            </div>
            
            <div className="options-list">
              {source === 'HTML' ? (
                <div className="html-specific-options">
                  {/* Preview Options */}
                  <div className={`option-group ${expandedSections.preview ? 'expanded' : ''}`}>
                    <button type="button" className="option-group-header" onClick={() => toggleSection('preview')} aria-expanded={expandedSections.preview}>
                      <span>{t('toolDetail.options.preview_options')}</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transform: expandedSections.preview ? 'rotate(180deg)' : 'rotate(0)' }}>
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </button>
                  {expandedSections.preview && (
                    <div className="option-group-content">
                      <label className="checkbox-label">
                        <input 
                          type="checkbox" 
                          checked={htmlOptions.enablePreview}
                          onChange={(e) => setHtmlOptions({...htmlOptions, enablePreview: e.target.checked})}
                        />
                        <span>{t('toolDetail.options.enable_preview')}</span>
                      </label>
                      <label className="checkbox-label">
                        <input 
                          type="checkbox" 
                          checked={htmlOptions.codeMode}
                          onChange={(e) => setHtmlOptions({...htmlOptions, codeMode: e.target.checked})}
                        />
                        <span>{t('toolDetail.options.convert_to_code')}</span>
                      </label>
                      <button className="preview-html-btn" onClick={handlePreviewHtml}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                        {t('toolDetail.options.preview_html')}
                      </button>
                    </div>
                  )}
                </div>

                {/* CSS Options */}
                <div className={`option-group ${expandedSections.css ? 'expanded' : ''}`}>
                  <button type="button" className="option-group-header" onClick={() => toggleSection('css')} aria-expanded={expandedSections.css}>
                    <span>{t('toolDetail.options.css_options')}</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transform: expandedSections.css ? 'rotate(180deg)' : 'rotate(0)' }}>
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </button>
                  {expandedSections.css && (
                    <div className="option-group-content">
                      <div className="sub-option">
                        <label className="custom-theme-label">{t('toolDetail.options.css_handling')}</label>
                        <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                          <select 
                            value={htmlOptions.cssHandling}
                            onChange={(e) => setHtmlOptions({...htmlOptions, cssHandling: e.target.value})}
                            className="custom-theme-select"
                          >
                            <option>{t('toolDetail.options.keep_all_css')}</option>
                            <option>{t('toolDetail.options.inline_css')}</option>
                            <option>{t('toolDetail.options.remove_css')}</option>
                          </select>
                          <svg 
                            width="12" 
                            height="12" 
                            viewBox="0 0 16 16" 
                            fill="currentColor" 
                            className="custom-select-icon"
                          >
                            <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                          </svg>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Cleanup Options */}
                <div className={`option-group ${expandedSections.cleanup ? 'expanded' : ''}`}>
                  <button type="button" className="option-group-header" onClick={() => toggleSection('cleanup')} aria-expanded={expandedSections.cleanup}>
                    <span>{t('toolDetail.options.cleanup_options')}</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transform: expandedSections.cleanup ? 'rotate(180deg)' : 'rotate(0)' }}>
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </button>
                  {expandedSections.cleanup && (
                    <div className="option-group-content">
                      <div className="cleanup-checkboxes">
                        <label className="checkbox-label">
                          <input 
                            type="checkbox" 
                            checked={htmlOptions.removeScripts}
                            onChange={(e) => setHtmlOptions({...htmlOptions, removeScripts: e.target.checked})}
                          />
                          <span>{t('toolDetail.options.remove_scripts')}</span>
                        </label>
                        <label className="checkbox-label">
                          <input 
                            type="checkbox" 
                            checked={htmlOptions.compressHtml}
                            onChange={(e) => setHtmlOptions({...htmlOptions, compressHtml: e.target.checked})}
                          />
                          <span>{t('toolDetail.options.compress_html')}</span>
                        </label>
                      </div>
                    </div>
                  )}
                </div>

                {/* PDF Specific Options */}
                {target === 'PDF' && (
                  <div className="option-group expanded">
                    <div className="option-group-header">
                      <span>{t('toolDetail.options.page_settings')}</span>
                    </div>
                    <div className="option-group-content">
                      <div className="sub-option">
                        <label className="custom-theme-label">{t('toolDetail.options.page_size')}</label>
                        <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                          <select 
                            value={htmlOptions.pageSize}
                            onChange={(e) => setHtmlOptions({...htmlOptions, pageSize: e.target.value})}
                            className="custom-theme-select"
                          >
                            <option>A4</option>
                            <option>Letter</option>
                            <option>A3</option>
                          </select>
                          <svg 
                            width="12" 
                            height="12" 
                            viewBox="0 0 16 16" 
                            fill="currentColor" 
                            className="custom-select-icon"
                          >
                            <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                          </svg>
                        </div>
                      </div>
                      <div className="sub-option">
                        <label className="custom-theme-label">{t('toolDetail.options.orientation')}</label>
                        <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                          <select 
                            value={htmlOptions.orientation}
                            onChange={(e) => setHtmlOptions({...htmlOptions, orientation: e.target.value})}
                            className="custom-theme-select"
                          >
                            <option>{t('toolDetail.options.portrait')}</option>
                            <option>{t('toolDetail.options.landscape')}</option>
                          </select>
                          <svg 
                            width="12" 
                            height="12" 
                            viewBox="0 0 16 16" 
                            fill="currentColor" 
                            className="custom-select-icon"
                          >
                            <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                          </svg>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Image Specific Options */}
                {['GIF', 'JPG', 'PNG', 'WEBP'].includes(target) && (
                  <div className="option-group expanded">
                    <div className="option-group-header">
                      <span>{t('toolDetail.options.image_options')}</span>
                    </div>
                    <div className="option-group-content">
                      <div className="sub-option">
                        <label>{t('toolDetail.options.quality')} (1-100)</label>
                        <input 
                          type="range" 
                          min="1" 
                          max="100" 
                          value={convertOptions.quality}
                          onChange={(e) => setConvertOptions({...convertOptions, quality: parseInt(e.target.value)})}
                        />
                        <span className="value-label-center">{convertOptions.quality}%</span>
                      </div>
                      
                      <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
                        <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.background_color')}</label>
                        <input 
                          type="color" 
                          value={convertOptions.backgroundColor}
                          onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                          style={{ width: '60px', height: '32px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
                        />
                        <input 
                          type="text" 
                          value={convertOptions.backgroundColor}
                          onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                          placeholder="#ffffff"
                          style={{ flex: 1, fontFamily: 'monospace' }}
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : source === 'PDF' ? (
              <div className="pdf-specific-options">
                {/* 页面选择组 */}
                <div className={`option-group ${isPdfPagesExpanded ? 'expanded' : ''}`}>
                  <div 
                    className="option-group-header" 
                    onClick={() => setIsPdfPagesExpanded(!isPdfPagesExpanded)}
                  >
                    <div className="option-group-title">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00a3ff" strokeWidth="2" style={{ marginRight: '8px' }}>
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="9" y1="15" x2="15" y2="15"/>
                      </svg>
                      <span>{t('toolDetail.options.page_selection')}</span>
                    </div>
                    <svg 
                      width="16" 
                      height="16" 
                      viewBox="0 0 24 24" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="2"
                      style={{ transform: isPdfPagesExpanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>

                  {isPdfPagesExpanded && (
                    <div className="option-group-content">
                      <div className="sub-option">
                        <label className="custom-theme-label">{t('toolDetail.options.select_pages')}</label>
                        <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                          <select 
                            value={convertOptions.pdfPageSelection}
                            onChange={(e) => setConvertOptions({...convertOptions, pdfPageSelection: e.target.value})}
                            className="custom-theme-select"
                          >
                            <option>{t('toolDetail.options.all_pages')}</option>
                            <option>{t('toolDetail.options.page_range')}</option>
                            <option>{t('toolDetail.options.specific_pages')}</option>
                          </select>
                          <svg 
                            width="12" 
                            height="12" 
                            viewBox="0 0 16 16" 
                            fill="currentColor" 
                            className="custom-select-icon"
                          >
                            <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                          </svg>
                        </div>
                      </div>

                      {convertOptions.pdfPageSelection === t('toolDetail.options.page_range') && (
                        <div className="sub-option" style={{ marginTop: '12px' }}>
                          <input 
                            type="text" 
                            placeholder={t('toolDetail.options.page_range_placeholder')}
                            value={convertOptions.pdfCustomRange}
                            onChange={(e) => setConvertOptions({...convertOptions, pdfCustomRange: e.target.value})}
                            onClick={(e) => e.stopPropagation()}
                            onKeyDown={(e) => e.stopPropagation()}
                            style={{ 
                              width: '100%', 
                              padding: '8px 12px', 
                              borderRadius: '6px', 
                              border: '1px solid #e2e8f0',
                              fontSize: '14px',
                              outline: 'none',
                              transition: 'all 0.2s',
                              color: '#1e293b',
                              backgroundColor: '#ffffff',
                              zIndex: 10,
                              position: 'relative'
                            }}
                          />
                        </div>
                      )}
                      
                      {convertOptions.pdfPageSelection === t('toolDetail.options.specific_pages') && (
                        <div className="sub-option" style={{ marginTop: '12px' }}>
                          <input 
                            type="text" 
                            placeholder={t('toolDetail.options.specific_pages_placeholder')}
                            value={convertOptions.pdfCustomRange}
                            onChange={(e) => setConvertOptions({...convertOptions, pdfCustomRange: e.target.value})}
                            onClick={(e) => e.stopPropagation()}
                            onKeyDown={(e) => e.stopPropagation()}
                            style={{ 
                              width: '100%', 
                              padding: '8px 12px', 
                              borderRadius: '6px', 
                              border: '1px solid #e2e8f0',
                              fontSize: '14px',
                              outline: 'none',
                              transition: 'all 0.2s',
                              color: '#1e293b',
                              backgroundColor: '#ffffff',
                              zIndex: 10,
                              position: 'relative'
                            }}
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* 图片质量选项 */}
                {['PNG', 'JPG', 'JPEG', 'BMP', 'WEBP'].includes(target) && (
                  <div className="option-group expanded">
                    <div className="option-group-header">
                      <div className="option-group-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00a3ff" strokeWidth="2" style={{ marginRight: '8px' }}>
                          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                          <circle cx="8.5" cy="8.5" r="1.5"/>
                          <polyline points="21 15 16 10 5 21"/>
                        </svg>
                        <span>{t('toolDetail.options.image_quality')}</span>
                      </div>
                    </div>
                    <div className="option-group-content">
                      <div className="sub-option">
                        <label>{t('toolDetail.options.quality_range')}</label>
                        <input 
                          type="range" 
                          min="1" 
                          max="100" 
                          value={convertOptions.quality}
                          onChange={(e) => setConvertOptions({...convertOptions, quality: parseInt(e.target.value)})}
                        />
                        <span className="value-label-center">{convertOptions.quality}%</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* GIF 动画选项 */}
                {target === 'GIF' && (
                  <div className="option-group expanded">
                    <div className="option-group-header">
                      <div className="option-group-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00a3ff" strokeWidth="2" style={{ marginRight: '8px' }}>
                          <circle cx="12" cy="12" r="10"/>
                          <polygon points="10 8 16 12 10 16 10 8"/>
                        </svg>
                        <span>{t('toolDetail.options.animation_settings')}</span>
                      </div>
                    </div>
                    <div className="option-group-content">
                      <div className="sub-option">
                        <label>{t('toolDetail.options.animation_delay')}</label>
                        <input 
                          type="number" 
                          value={convertOptions.animationDelay}
                          onChange={(e) => setConvertOptions({...convertOptions, animationDelay: parseInt(e.target.value)})}
                          min="10"
                          max="5000"
                          step="10"
                        />
                      </div>
                      <label className="checkbox-label">
                        <input 
                          type="checkbox" 
                          checked={convertOptions.loopAnimation}
                          onChange={(e) => setConvertOptions({...convertOptions, loopAnimation: e.target.checked})}
                        />
                        <span>{t('toolDetail.options.loop_animation')}</span>
                      </label>
                    </div>
                  </div>
                )}
              </div>
            ) : source === 'TXT' ? (
              <div className="txt-specific-options" style={{ padding: '0 20px 20px' }}>
                {target === 'SPEECH' && (
                  <>
                    <div className="sub-option" style={{ marginTop: '20px' }}>
                      <label style={{ color: '#334155', fontWeight: '500', marginBottom: '12px', display: 'block', fontSize: '15px' }}>{t('toolDetail.options.speech_speed')}</label>
                      <input 
                        type="range" 
                        min="0.5" 
                        max="2.0" 
                        step="0.1"
                        value={convertOptions.speechSpeed}
                        onChange={(e) => setConvertOptions({...convertOptions, speechSpeed: parseFloat(e.target.value)})}
                        style={{ width: '100%', marginBottom: '8px' }}
                      />
                      <div className="value-label-center" style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                        {convertOptions.speechSpeed}x
                      </div>
                    </div>

                    <div className="sub-option" style={{ marginTop: '20px' }}>
                      <label style={{ color: '#334155', fontWeight: '500', marginBottom: '12px', display: 'block', fontSize: '15px' }}>{t('toolDetail.options.speech_pitch')}</label>
                      <input 
                        type="range" 
                        min="0.5" 
                        max="2.0" 
                        step="0.1"
                        value={convertOptions.speechPitch}
                        onChange={(e) => setConvertOptions({...convertOptions, speechPitch: parseFloat(e.target.value)})}
                        style={{ width: '100%', marginBottom: '8px' }}
                      />
                      <div className="value-label-center" style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                        {convertOptions.speechPitch}
                      </div>
                    </div>


                  </>
                )}
                
                {target === 'PDF' && (
                  <>
                    <div className="sub-option" style={{ marginTop: '20px' }}>
                      <label className="custom-theme-label">{t('toolDetail.options.page_size')}</label>
                      <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                        <select 
                          value={convertOptions.pageSize}
                          onChange={(e) => setConvertOptions({...convertOptions, pageSize: e.target.value})}
                          className="custom-theme-select"
                        >
                          <option>A4</option>
                          <option>Letter</option>
                          <option>A3</option>
                          <option>Legal</option>
                        </select>
                        <svg 
                          width="12" 
                          height="12" 
                          viewBox="0 0 16 16" 
                          fill="currentColor" 
                          className="custom-select-icon"
                        >
                          <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                        </svg>
                      </div>
                    </div>

                    <div className="sub-option" style={{ marginTop: '20px' }}>
                      <label className="custom-theme-label">{t('toolDetail.options.orientation')}</label>
                      <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                        <select 
                          value={convertOptions.orientation}
                          onChange={(e) => setConvertOptions({...convertOptions, orientation: e.target.value})}
                          className="custom-theme-select"
                        >
                          <option>{t('toolDetail.options.portrait')}</option>
                          <option>{t('toolDetail.options.landscape')}</option>
                        </select>
                        <svg 
                          width="12" 
                          height="12" 
                          viewBox="0 0 16 16" 
                          fill="currentColor" 
                          className="custom-select-icon"
                        >
                          <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                        </svg>
                      </div>
                    </div>
                  </>
                )}

                {['JPG', 'PNG'].includes(target) && (
                  <>
                    <div className="sub-option" style={{ marginTop: '20px' }}>
                      <label style={{ color: '#334155', fontWeight: '500', marginBottom: '12px', display: 'block', fontSize: '15px' }}>{t('toolDetail.options.quality_range')}</label>
                      <input 
                        type="range" 
                        min="1" 
                        max="100" 
                        value={convertOptions.quality}
                        onChange={(e) => setConvertOptions({...convertOptions, quality: parseInt(e.target.value)})}
                        style={{ width: '100%', marginBottom: '8px' }}
                      />
                      <div className="value-label-center" style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                        {convertOptions.quality}%
                      </div>
                    </div>

                    <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px', marginTop: '20px' }}>
                      <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.background_color')}</label>
                      <input 
                        type="color" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        style={{ width: '60px', height: '32px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
                      />
                      <input 
                        type="text" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        placeholder="#ffffff"
                        style={{ flex: 1, fontFamily: 'monospace' }}
                      />
                    </div>
                  </>
                )}
              </div>
            ) : source === 'JSON' ? (
              <div className="json-specific-options">
                {target === 'CSV' && (
                  <div className="option-group-content" style={{ padding: '20px' }}>
                    <div className="sub-option">
                      <label className="custom-theme-label">{t('toolDetail.options.csv_delimiter')}</label>
                      <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                        <select 
                          value={convertOptions.csvDelimiter}
                          onChange={(e) => setConvertOptions({...convertOptions, csvDelimiter: e.target.value})}
                          className="custom-theme-select"
                        >
                          <option>{t('toolDetail.options.comma')}</option>
                          <option>{t('toolDetail.options.semicolon')}</option>
                          <option>{t('toolDetail.options.tab')}</option>
                          <option>{t('toolDetail.options.pipe')}</option>
                        </select>
                        <svg 
                          width="12" 
                          height="12" 
                          viewBox="0 0 16 16" 
                          fill="currentColor" 
                          className="custom-select-icon"
                        >
                          <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                        </svg>
                      </div>
                    </div>
                  </div>
                )}

                {target === 'JPG' && (
                  <div className="option-group-content static-options" style={{ padding: '20px' }}>
                    <div className="sub-option">
                      <label>{t('toolDetail.options.image_quality')}</label>
                      <input 
                        type="range" 
                        min="1" 
                        max="100" 
                        value={convertOptions.quality}
                        onChange={(e) => setConvertOptions({...convertOptions, quality: parseInt(e.target.value)})}
                      />
                      <div className="value-label-center" style={{ marginTop: '8px', color: '#94a3b8' }}>
                        {convertOptions.quality}%
                      </div>
                    </div>
                    
                    <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px', marginTop: '20px' }}>
                      <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.background_color')}</label>
                      <input 
                        type="color" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        style={{ width: '60px', height: '32px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
                      />
                      <input 
                        type="text" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        placeholder="#ffffff"
                        style={{ flex: 1, fontFamily: 'monospace' }}
                      />
                    </div>
                  </div>
                )}

                {target === 'YAML' && (
                  <div className="option-group-content static-options" style={{ padding: '20px' }}>
                    <div className="sub-option">
                      <label>{t('toolDetail.options.yaml_indent')}</label>
                      <input 
                        type="range" 
                        min="1" 
                        max="8" 
                        step="1"
                        value={convertOptions.yamlIndent}
                        onChange={(e) => setConvertOptions({...convertOptions, yamlIndent: parseInt(e.target.value)})}
                      />
                      <div className="value-label-center" style={{ marginTop: '8px', color: '#94a3b8' }}>
                        {convertOptions.yamlIndent}
                      </div>
                    </div>
                  </div>
                )}

              </div>
            ) : ['PPT', 'Excel'].includes(source) ? (
              <div className="ppt-excel-specific-options" style={{ padding: '0 20px 20px' }}>
                {source === 'Excel' && ['PDF', 'PNG', 'JPG', 'JPEG', 'Image'].includes(target) && (
                  <>
                    <div className="sub-option" style={{ marginTop: '20px' }}>
                      <label className="custom-theme-label">{t('toolDetail.options.page_size')}</label>
                      <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                        <select
                          value={convertOptions.pageSize}
                          onChange={(e) => setConvertOptions({ ...convertOptions, pageSize: e.target.value })}
                          className="custom-theme-select"
                        >
                          <option value="A4">A4</option>
                          <option value="A3">A3</option>
                          <option value="Letter">Letter</option>
                          <option value="Legal">Legal</option>
                        </select>
                      </div>
                    </div>
                    <div className="sub-option" style={{ marginTop: '16px' }}>
                      <label className="custom-theme-label">{t('toolDetail.options.orientation')}</label>
                      <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                        <select
                          value={convertOptions.excelOrientation}
                          onChange={(e) => setConvertOptions({ ...convertOptions, excelOrientation: e.target.value })}
                          className="custom-theme-select"
                        >
                          <option value="auto">{t('toolDetail.options.auto')}</option>
                          <option value="portrait">{t('toolDetail.options.portrait')}</option>
                          <option value="landscape">{t('toolDetail.options.landscape')}</option>
                        </select>
                      </div>
                    </div>
                    <div className="sub-option" style={{ marginTop: '16px' }}>
                      <label className="custom-theme-label">{t('toolDetail.options.page_scaling')}</label>
                      <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                        <select
                          value={convertOptions.excelScaleMode}
                          onChange={(e) => setConvertOptions({ ...convertOptions, excelScaleMode: e.target.value })}
                          className="custom-theme-select"
                        >
                          <option value="fit_width">{t('toolDetail.options.fit_page_width')}</option>
                          <option value="actual_size">{t('toolDetail.options.actual_size')}</option>
                          <option value="auto">{t('toolDetail.options.auto')}</option>
                        </select>
                      </div>
                    </div>
                  </>
                )}
                {['JPG', 'PNG', 'JPEG', 'Image'].includes(target) && (
                  <>
                    <div className="sub-option" style={{ marginTop: '20px' }}>
                      <label style={{ color: '#334155', fontWeight: '500', marginBottom: '12px', display: 'block', fontSize: '15px' }}>{t('toolDetail.options.quality_range')}</label>
                      <input 
                        type="range" 
                        min="1" 
                        max="100" 
                        value={convertOptions.quality}
                        onChange={(e) => setConvertOptions({...convertOptions, quality: parseInt(e.target.value)})}
                        style={{ width: '100%', marginBottom: '8px' }}
                      />
                      <div className="value-label-center" style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                        {convertOptions.quality}%
                      </div>
                    </div>

                    <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px', marginTop: '20px' }}>
                      <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.background_color')}</label>
                      <input 
                        type="color" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        style={{ width: '60px', height: '32px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
                      />
                      <input 
                        type="text" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        placeholder="#ffffff"
                        style={{ flex: 1, fontFamily: 'monospace' }}
                      />
                    </div>
                  </>
                )}
              </div>
            ) : source === 'XML' ? (
              <div className="xml-specific-options" style={{ padding: '0 20px 20px' }}>
                {target === 'PDF' && (
                  <>
                    <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px', marginTop: '10px' }}>
                      <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.background_color')}</label>
                      <input 
                        type="color" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        style={{ width: '60px', height: '32px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
                      />
                      <input 
                        type="text" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        placeholder="#ffffff"
                        style={{ flex: 1, fontFamily: 'monospace' }}
                      />
                    </div>
                    <div className="sub-option" style={{ marginTop: '20px' }}>
                      <label className="custom-theme-label">{t('toolDetail.options.page_size')}</label>
                      <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                        <select 
                          value={convertOptions.pageSize}
                          onChange={(e) => setConvertOptions({...convertOptions, pageSize: e.target.value})}
                          className="custom-theme-select"
                        >
                          <option>A4</option>
                          <option>Letter</option>
                          <option>A3</option>
                          <option>Legal</option>
                        </select>
                        <svg 
                          width="12" 
                          height="12" 
                          viewBox="0 0 16 16" 
                          fill="currentColor" 
                          className="custom-select-icon"
                        >
                          <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                        </svg>
                      </div>
                    </div>
                  </>
                )}
                {target === 'JPG' && (
                  <>
                    <div className="sub-option" style={{ marginTop: '20px' }}>
                      <label style={{ color: '#334155', fontWeight: '500', marginBottom: '12px', display: 'block', fontSize: '15px' }}>{t('toolDetail.options.quality_range')}</label>
                      <input 
                        type="range" 
                        min="1" 
                        max="100" 
                        value={convertOptions.quality}
                        onChange={(e) => setConvertOptions({...convertOptions, quality: parseInt(e.target.value)})}
                        style={{ width: '100%', marginBottom: '8px' }}
                      />
                      <div className="value-label-center" style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                        {convertOptions.quality}%
                      </div>
                    </div>
                    <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px', marginTop: '20px' }}>
                      <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.background_color')}</label>
                      <input 
                        type="color" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        style={{ width: '60px', height: '32px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
                      />
                      <input 
                        type="text" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        placeholder="#ffffff"
                        style={{ flex: 1, fontFamily: 'monospace' }}
                      />
                    </div>
                  </>
                )}
                {target === 'CSV' && (
                  <div className="sub-option" style={{ marginTop: '20px' }}>
                    <label className="custom-theme-label">{t('toolDetail.options.csv_delimiter')}</label>
                    <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                      <select 
                        value={convertOptions.csvDelimiter}
                        onChange={(e) => setConvertOptions({...convertOptions, csvDelimiter: e.target.value})}
                        className="custom-theme-select"
                      >
                        <option>{t('toolDetail.options.comma')}</option>
                        <option>{t('toolDetail.options.semicolon')}</option>
                        <option>{t('toolDetail.options.tab')}</option>
                        <option>{t('toolDetail.options.pipe')}</option>
                      </select>
                      <svg 
                        width="12" 
                        height="12" 
                        viewBox="0 0 16 16" 
                        fill="currentColor" 
                        className="custom-select-icon"
                      >
                        <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                      </svg>
                    </div>
                  </div>
                )}
                {target === 'YAML' && (
                  <div className="sub-option" style={{ marginTop: '20px' }}>
                    <label style={{ color: '#334155', fontWeight: '500', marginBottom: '12px', display: 'block', fontSize: '15px' }}>{t('toolDetail.options.yaml_indent')}</label>
                    <input 
                      type="range" 
                      min="1" 
                      max="8" 
                      step="1"
                      value={convertOptions.yamlIndent}
                      onChange={(e) => setConvertOptions({...convertOptions, yamlIndent: parseInt(e.target.value)})}
                      style={{ width: '100%', marginBottom: '8px' }}
                    />
                    <div className="value-label-center" style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                      {convertOptions.yamlIndent}
                    </div>
                  </div>
                )}
                {target === 'JSON' && (
                  <div className="sub-option" style={{ marginTop: '20px' }}>
                    <label style={{ color: '#334155', fontWeight: '500', marginBottom: '12px', display: 'block', fontSize: '15px' }}>{t('toolDetail.options.json_indent')}</label>
                    <input 
                      type="range" 
                      min="1" 
                      max="8" 
                      step="1"
                      value={convertOptions.yamlIndent}
                      onChange={(e) => setConvertOptions({...convertOptions, yamlIndent: parseInt(e.target.value)})}
                      style={{ width: '100%', marginBottom: '8px' }}
                    />
                    <div className="value-label-center" style={{ textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
                      {convertOptions.yamlIndent}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <>
                {source === 'DOCX' && target === 'PDF' && (
                  <div className="option-group-content static-options">
                    <div className="sub-option">
                      <label>{t('toolDetail.options.page_range')}</label>
                      <input
                        type="text"
                        value={convertOptions.docxPdfPageRange}
                        onChange={(e) => setConvertOptions({...convertOptions, docxPdfPageRange: e.target.value})}
                        placeholder={t('toolDetail.options.docx_page_range_placeholder')}
                        style={{ width: '100%', fontFamily: 'monospace' }}
                      />
                    </div>
                    <div className="sub-option" style={{ marginTop: '16px' }}>
                      <label className="custom-theme-label">{t('toolDetail.options.page_size')}</label>
                      <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                        <select
                          value={convertOptions.pageSize}
                          onChange={(e) => setConvertOptions({...convertOptions, pageSize: e.target.value})}
                          className="custom-theme-select"
                        >
                          <option>A4</option>
                          <option>Letter</option>
                          <option>A3</option>
                          <option>Legal</option>
                        </select>
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 16 16"
                          fill="currentColor"
                          className="custom-select-icon"
                        >
                          <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                        </svg>
                      </div>
                    </div>
                    <div className="sub-option" style={{ marginTop: '16px' }}>
                      <label className="custom-theme-label">{t('toolDetail.options.orientation')}</label>
                      <div className="custom-select-wrapper" style={{ position: 'relative' }}>
                        <select
                          value={convertOptions.orientation}
                          onChange={(e) => setConvertOptions({...convertOptions, orientation: e.target.value})}
                          className="custom-theme-select"
                        >
                          <option>{t('toolDetail.options.portrait')}</option>
                          <option>{t('toolDetail.options.landscape')}</option>
                        </select>
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 16 16"
                          fill="currentColor"
                          className="custom-select-icon"
                        >
                          <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
                        </svg>
                      </div>
                    </div>
                  </div>
                )}

                {!['TXT', 'EPUB'].includes(target) && ['PNG', 'JPG', 'JPEG', 'GIF', 'WEBP', 'SVG'].includes(target) && (
                  <div className="option-group-content static-options">
                    <div className="sub-option">
                      <label>{t('toolDetail.options.quality_range')}</label>
                      <input 
                        type="range" 
                        min="1" 
                        max="100" 
                        value={convertOptions.quality}
                        onChange={(e) => setConvertOptions({...convertOptions, quality: e.target.value})}
                      />
                      <span className="value-label-center">{convertOptions.quality}%</span>
                    </div>
                    
                    <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
                      <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.background_color')}</label>
                      <input 
                        type="color" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        style={{ width: '60px', height: '32px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
                      />
                      <input 
                        type="text" 
                        value={convertOptions.backgroundColor}
                        onChange={(e) => setConvertOptions({...convertOptions, backgroundColor: e.target.value})}
                        placeholder="#ffffff"
                        style={{ flex: 1, fontFamily: 'monospace' }}
                      />
                    </div>
                  </div>
                )}

                <div className={`option-group ${isWatermarkExpanded ? 'expanded' : ''}`}>
                  <div 
                    className="option-group-header" 
                    onClick={() => setIsWatermarkExpanded(!isWatermarkExpanded)}
                  >
                    <span>{t('toolDetail.options.watermark_info')}</span>
                    <svg 
                      width="16" 
                      height="16" 
                      viewBox="0 0 24 24" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="2"
                      style={{ transform: isWatermarkExpanded ? 'rotate(180deg)' : 'rotate(0)' }}
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  
                  {isWatermarkExpanded && (
                    <div className="option-group-content">
                      {!['TXT', 'EPUB'].includes(target) && (
                        <>
                          <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
                            <label style={{ minWidth: 'auto', marginBottom: 0 }}>{t('toolDetail.options.watermark_text')}</label>
                            <input 
                              type="text" 
                              placeholder=""
                              value={watermarkOptions.text}
                              onChange={(e) => setWatermarkOptions({...watermarkOptions, text: e.target.value})}
                              style={{ flex: 1 }}
                            />
                          </div>
                          
                          <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
                            <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.watermark_size')}</label>
                            <input 
                              type="range" 
                              min="10" 
                              max="100" 
                              value={watermarkOptions.size}
                              onChange={(e) => setWatermarkOptions({...watermarkOptions, size: e.target.value})}
                              style={{ flex: 1 }}
                            />
                            <span className="value-label-center" style={{ minWidth: '40px', textAlign: 'right' }}>{watermarkOptions.size}</span>
                          </div>
                          
                          <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
                            <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.watermark_opacity')}</label>
                            <input 
                              type="range" 
                              min="0" 
                              max="100" 
                              value={watermarkOptions.opacity}
                              onChange={(e) => setWatermarkOptions({...watermarkOptions, opacity: e.target.value})}
                              style={{ flex: 1 }}
                            />
                            <span className="value-label-center" style={{ minWidth: '40px', textAlign: 'right' }}>{watermarkOptions.opacity}%</span>
                          </div>
                          
                          <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
                            <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.watermark_angle')}</label>
                            <input 
                              type="range" 
                              min="0" 
                              max="360" 
                              value={watermarkOptions.angle}
                              onChange={(e) => setWatermarkOptions({...watermarkOptions, angle: e.target.value})}
                              style={{ flex: 1 }}
                            />
                            <span className="value-label-center" style={{ minWidth: '40px', textAlign: 'right' }}>{watermarkOptions.angle}°</span>
                          </div>
                          
                          <div className="sub-option" style={{ flexDirection: 'row', alignItems: 'center', gap: '12px' }}>
                            <label style={{ minWidth: '60px', marginBottom: 0 }}>{t('toolDetail.options.watermark_color')}</label>
                            <input 
                              type="color" 
                              value={watermarkOptions.color}
                              onChange={(e) => setWatermarkOptions({...watermarkOptions, color: e.target.value})}
                              style={{ width: '60px', height: '32px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer' }}
                            />
                            <input 
                              type="text" 
                              value={watermarkOptions.color}
                              onChange={(e) => setWatermarkOptions({...watermarkOptions, color: e.target.value})}
                              placeholder="#cccccc"
                              style={{ flex: 1, fontFamily: 'monospace' }}
                            />
                          </div>
                        </>
                      )}
                      
                      <div className="sub-option">
                        <label>{t('toolDetail.options.watermark_position')}</label>
                        <div className="position-grid">
                          {[
                            { pos: 'top-left', icon: <path d="M7 17l10-10M7 7h10v10" style={{ transform: 'rotate(-90deg)', transformOrigin: 'center' }} /> },
                            { pos: 'top', icon: <path d="M12 19V5M5 12l7-7 7 7" /> },
                            { pos: 'top-right', icon: <path d="M7 17l10-10M7 7h10v10" /> },
                            { pos: 'left', icon: <path d="M19 12H5M12 5l-7 7 7 7" /> },
                            { pos: 'center', icon: <g><circle cx="12" cy="12" r="3" strokeWidth="2" /><circle cx="12" cy="12" r="6" strokeWidth="1" /></g> },
                            { pos: 'right', icon: <path d="M5 12h14M12 5l7 7-7 7" /> },
                            { pos: 'bottom-left', icon: <path d="M17 7L7 17M17 17H7V7" /> },
                            { pos: 'bottom', icon: <path d="M12 5v14M5 12l7 7 7-7" /> },
                            { pos: 'bottom-right', icon: <path d="M7 7l10 10M17 7v10H7" /> }
                          ].map(item => (
                            <button 
                              type="button"
                              key={item.pos}
                              className={`pos-btn ${watermarkOptions.position === item.pos ? 'active' : ''}`}
                              onClick={() => setWatermarkOptions({...watermarkOptions, position: item.pos})}
                              title={t(`toolDetail.options.watermark_positions.${item.pos}`)}
                              aria-label={t(`toolDetail.options.watermark_positions.${item.pos}`)}
                            >
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                {item.icon}
                              </svg>
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <div className="file-list-container">
        <div className="file-list-header">
          <h3 className="file-list-title">{t('toolDetail.file_list')} ({files.length})</h3>
          <div className="file-list-actions">
            <button className="file-action-btn" onClick={handleSelectAll} disabled={files.length === 0 || isConverting}>{t('toolDetail.select_all')}</button>
            <button className="file-action-btn" onClick={handleDeselectAll} disabled={files.length === 0 || isConverting || selectedFiles.size === 0}>{t('toolDetail.deselect_all')}</button>
            {selectedFiles.size > 0 && !isConverting && (
              <button className="file-action-btn file-action-btn-danger" onClick={handleDeleteSelected}>
                {t('toolDetail.delete_selected')} ({selectedFiles.size})
              </button>
            )}
            {isConverting ? (
              <button 
                className="file-action-btn file-action-btn-danger"
                onClick={handleCancelConversion}
              >
                {t('toolDetail.cancel_conversion')}
              </button>
            ) : (
              <button 
                className="file-action-btn file-action-btn-primary"
                onClick={handleConvert}
                disabled={selectedFiles.size === 0}
              >
                {t('toolDetail.convert_selected', { count: selectedFiles.size })}
              </button>
            )}
            <button className="file-action-btn" onClick={handleClearAll} disabled={files.length === 0 || isConverting}>
              {t('toolDetail.clear_all')}
            </button>
            <button
              className="file-action-btn"
              disabled={isConverting || !Object.values(conversionResults).some((result) => result && !result.error && result.download_url)}
              onClick={handleDownloadAll}
            >
              {t('toolDetail.download_all')}
            </button>
          </div>
        </div>
        
        {isConverting && (
          <div className="progress-bar-container">
            <div className="progress-info">
              <span>{t('toolDetail.progress_processing', { current: progress.current, total: progress.total })}</span>
              <span>{progress.percent}%</span>
            </div>
            <div className="progress-track">
              <div 
                className="progress-fill" 
                style={{ width: `${progress.percent}%` }}
              ></div>
            </div>
            {estimatedTime && (
              <div className="progress-estimate">
                <span>{t('toolDetail.estimated_time')}: ~{estimatedTime}s</span>
                {estimatedTime > 30 && (
                  <span className="progress-bg-hint"> · {t('toolDetail.can_background')}</span>
                )}
              </div>
            )}
            {currentStage && (
              <div className="progress-stage">{currentStage}</div>
            )}
          </div>
        )}
        
        <div className="file-list-body">
          {files.length > 0 ? (
            <div className="file-list-content">
              {files.map((fileObj) => (
                <div key={fileObj.id} className="file-item-card">
                  <div className="file-item-checkbox" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedFiles.has(fileObj.id)}
                      onChange={() => handleToggleFileSelect(fileObj.id)}
                      disabled={isConverting}
                      className="file-checkbox-input"
                    />
                  </div>
                  <div className="file-item-left">
                    <div className={`file-icon-circle ${isConverting && selectedFiles.has(fileObj.id) ? 'loading' : ''}`}>
                      <span className="file-type-text">{source}</span>
                      {isConverting && selectedFiles.has(fileObj.id) && <div className="loading-ring"></div>}
                    </div>
                    <div className="file-info">
                      <div className="file-name" title={fileObj.file.name}>
                        {fileObj.file.name}
                        {selectedFiles.has(fileObj.id) && <span className="selected-badge" style={{marginLeft:6,fontSize:11,color:'#00a3ff'}}>✓</span>}
                      </div>
                      <div className="file-size">{(fileObj.file.size / 1024).toFixed(2)} KB</div>
                    </div>
                  </div>

                  <div className="file-item-right">
                    {conversionResults[fileObj.id] && !conversionResults[fileObj.id].error && (
                      <button
                        onClick={(e) => handleSingleFileDownload(e, fileObj.id)}
                        className="status-btn finish"
                        title={t('toolDetail.download_file')}
                      >
                        {t('toolDetail.download')}
                      </button>
                    )}
                    {conversionResults[fileObj.id] && conversionResults[fileObj.id].error && (
                      <span className="status-btn error">{t('toolDetail.error')}</span>
                    )}
                    {!conversionResults[fileObj.id] && isConverting && selectedFiles.has(fileObj.id) && (
                      <span className="status-btn converting">{t('toolDetail.status_converting')}</span>
                    )}
                    <button 
                      onClick={() => handleRemoveFile(fileObj.id)}
                      className="btn-delete"
                      title={t('toolDetail.delete')}
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="file-list-empty">
              <p>{t('toolDetail.no_files')}</p>
            </div>
          )}
        </div>
      </div>
    </div>

      {showDownloadModal && (
        <div className="modal-overlay" onClick={() => setShowDownloadModal(false)}>
          <div className="download-modal" onClick={e => e.stopPropagation()}>
            <div className="download-modal-header">
              <h3>{t('toolDetail.download_all')}</h3>
              <button className="modal-close-btn" onClick={() => setShowDownloadModal(false)}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="download-modal-content">
              <button className="download-option-btn" onClick={handleZipDownload}>
                <div className="download-option-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                    <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                    <line x1="12" y1="22.08" x2="12" y2="12"></line>
                  </svg>
                </div>
                <div className="download-option-text">
                  <h4>{t('toolDetail.zip_download_title')}</h4>
                  <p>{t('toolDetail.zip_download_desc')}</p>
                </div>
              </button>
              
              <button className="download-option-btn" onClick={handleBatchDownload}>
                <div className="download-option-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                  </svg>
                </div>
                <div className="download-option-text">
                  <h4>{t('toolDetail.download_to_folder_title')}</h4>
                  <p>{t('toolDetail.select_folder')}</p>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}

      {showPreviewModal && (
        <div className="modal-overlay" onClick={() => setShowPreviewModal(false)}>
          <div className="preview-modal" onClick={e => e.stopPropagation()}>
            <div className="preview-modal-header">
              <h3>{t('toolDetail.html_preview')}</h3>
              <button className="preview-close-btn" onClick={() => setShowPreviewModal(false)}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="preview-modal-content">
              <iframe 
                srcDoc={previewContent} 
                title={t('toolDetail.html_preview')}
                style={{ width: '100%', height: '100%', border: 'none', backgroundColor: '#fff' }}
                sandbox="allow-scripts"
              />
            </div>
          </div>
        </div>
      )}
    </MotionDiv>
  );
}

export default ToolDetailContent;
