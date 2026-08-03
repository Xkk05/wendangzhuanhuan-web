const INLINE_IMAGE_EXTENSIONS = /\.(avif|bmp|gif|ico|jpe?g|png|svg|webp)$/i;
const MAX_INLINE_IMAGE_BYTES = 10 * 1024 * 1024;

const normalizePath = (path) => String(path || '').replace(/\\/g, '/').replace(/^\.\/+/, '');

const stripUrlSuffix = (src) => String(src || '').split('#', 1)[0].split('?', 1)[0];

const decodePath = (path) => {
  try {
    return decodeURIComponent(path);
  } catch {
    return path;
  }
};

const getDirectoryName = (path) => {
  const normalized = normalizePath(path);
  const index = normalized.lastIndexOf('/');
  return index >= 0 ? normalized.slice(0, index) : '';
};

const resolveRelativePath = (src, baseDirectory) => {
  const trimmed = String(src || '').trim();
  if (
    !trimmed ||
    trimmed.startsWith('#') ||
    trimmed.startsWith('//') ||
    /^(?:[a-z][a-z\d+.-]*:)/i.test(trimmed)
  ) {
    return null;
  }

  const decodedPath = normalizePath(decodePath(stripUrlSuffix(trimmed)));
  const isRootRelative = decodedPath.startsWith('/');
  const cleaned = decodedPath.replace(/^\/+/, '');
  const combined = isRootRelative
    ? cleaned
    : normalizePath(`${baseDirectory ? `${baseDirectory}/` : ''}${cleaned}`);
  const parts = [];

  for (const part of combined.split('/')) {
    if (!part || part === '.') continue;
    if (part === '..') {
      parts.pop();
    } else {
      parts.push(part);
    }
  }

  return parts.join('/');
};

const collectAssetKeys = (file) => {
  const keys = new Set();
  if (file?.webkitRelativePath) keys.add(normalizePath(file.webkitRelativePath));
  if (file?.name) keys.add(normalizePath(file.name));
  return keys;
};

const readAsDataUrl = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(reader.result);
  reader.onerror = () => reject(reader.error);
  reader.readAsDataURL(file);
});

export const isHtmlImageAsset = (file) => (
  Boolean(file)
  && (String(file.type || '').startsWith('image/') || INLINE_IMAGE_EXTENSIONS.test(file.name || ''))
);

export const isPortableHtmlAssetTarget = (source, target) => (
  source === 'HTML'
  && ['DOC', 'DOCX', 'WORD', 'MD', 'MARKDOWN'].includes(target)
);

export const createHtmlFileWithInlinedImages = async (htmlFile, assetFiles = []) => {
  if (!htmlFile || !assetFiles.length || typeof DOMParser === 'undefined' || typeof File === 'undefined') {
    return htmlFile;
  }

  const assetMap = new Map();
  for (const assetFile of assetFiles) {
    if (!isHtmlImageAsset(assetFile) || assetFile.size > MAX_INLINE_IMAGE_BYTES) continue;
    for (const key of collectAssetKeys(assetFile)) {
      assetMap.set(key, assetFile);
    }
  }

  if (!assetMap.size) return htmlFile;

  const htmlText = await htmlFile.text();
  const document = new DOMParser().parseFromString(htmlText, 'text/html');
  const htmlPath = normalizePath(htmlFile.webkitRelativePath || htmlFile.name || '');
  const baseDirectory = getDirectoryName(htmlPath);
  let changed = false;

  for (const image of Array.from(document.querySelectorAll('img[src]'))) {
    const src = image.getAttribute('src');
    const resolvedPath = resolveRelativePath(src, baseDirectory);
    const assetFile = resolvedPath ? assetMap.get(resolvedPath) || assetMap.get(normalizePath(resolvedPath.split('/').pop())) : null;
    if (!assetFile) continue;

    image.setAttribute('src', await readAsDataUrl(assetFile));
    changed = true;
  }

  if (!changed) return htmlFile;

  const doctype = htmlText.match(/^\s*<!doctype[^>]*>/i)?.[0] || '<!doctype html>';
  const inlinedHtml = `${doctype}\n${document.documentElement.outerHTML}`;
  return new File([inlinedHtml], htmlFile.name, {
    type: htmlFile.type || 'text/html',
    lastModified: htmlFile.lastModified,
  });
};
