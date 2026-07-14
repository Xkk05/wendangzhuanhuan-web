import { categories } from '../data.js';
import { getCategorySlugBySectionName } from './toolHelpers.js';

export const SITE_URL = import.meta?.env?.VITE_SITE_URL || 'https://doc.kunqiongai.com';
export const SITE_NAME = 'KunqiongAI Doc';
export const DEFAULT_OG_IMAGE = `${SITE_URL}/logo.ico`;
const WEB_DISABLED_SECTION_NAMES = new Set(['ppt_converter']);
export const DEFAULT_LANGUAGE = 'zh_CN';
export const SEO_LANGUAGE_MAP = {
  zh_CN: { hreflang: 'zh-CN', ogLocale: 'zh_CN', htmlLang: 'zh-CN', dir: 'ltr' },
  zh_TW: { hreflang: 'zh-TW', ogLocale: 'zh_TW', htmlLang: 'zh-TW', dir: 'ltr' },
  en: { hreflang: 'en', ogLocale: 'en_US', htmlLang: 'en', dir: 'ltr' },
  ar: { hreflang: 'ar', ogLocale: 'ar_AR', htmlLang: 'ar', dir: 'rtl' },
  bn: { hreflang: 'bn', ogLocale: 'bn_BD', htmlLang: 'bn', dir: 'ltr' },
  de: { hreflang: 'de', ogLocale: 'de_DE', htmlLang: 'de', dir: 'ltr' },
  es: { hreflang: 'es', ogLocale: 'es_ES', htmlLang: 'es', dir: 'ltr' },
  fa: { hreflang: 'fa', ogLocale: 'fa_IR', htmlLang: 'fa', dir: 'rtl' },
  fr: { hreflang: 'fr', ogLocale: 'fr_FR', htmlLang: 'fr', dir: 'ltr' },
  he: { hreflang: 'he', ogLocale: 'he_IL', htmlLang: 'he', dir: 'rtl' },
  hi: { hreflang: 'hi', ogLocale: 'hi_IN', htmlLang: 'hi', dir: 'ltr' },
  id: { hreflang: 'id', ogLocale: 'id_ID', htmlLang: 'id', dir: 'ltr' },
  it: { hreflang: 'it', ogLocale: 'it_IT', htmlLang: 'it', dir: 'ltr' },
  ja: { hreflang: 'ja', ogLocale: 'ja_JP', htmlLang: 'ja', dir: 'ltr' },
  ko: { hreflang: 'ko', ogLocale: 'ko_KR', htmlLang: 'ko', dir: 'ltr' },
  ms: { hreflang: 'ms', ogLocale: 'ms_MY', htmlLang: 'ms', dir: 'ltr' },
  nl: { hreflang: 'nl', ogLocale: 'nl_NL', htmlLang: 'nl', dir: 'ltr' },
  pl: { hreflang: 'pl', ogLocale: 'pl_PL', htmlLang: 'pl', dir: 'ltr' },
  pt: { hreflang: 'pt', ogLocale: 'pt_PT', htmlLang: 'pt', dir: 'ltr' },
  pt_BR: { hreflang: 'pt-BR', ogLocale: 'pt_BR', htmlLang: 'pt-BR', dir: 'ltr' },
  ru: { hreflang: 'ru', ogLocale: 'ru_RU', htmlLang: 'ru', dir: 'ltr' },
  sw: { hreflang: 'sw', ogLocale: 'sw_KE', htmlLang: 'sw', dir: 'ltr' },
  ta: { hreflang: 'ta', ogLocale: 'ta_IN', htmlLang: 'ta', dir: 'ltr' },
  th: { hreflang: 'th', ogLocale: 'th_TH', htmlLang: 'th', dir: 'ltr' },
  tl: { hreflang: 'tl', ogLocale: 'tl_PH', htmlLang: 'tl', dir: 'ltr' },
  tr: { hreflang: 'tr', ogLocale: 'tr_TR', htmlLang: 'tr', dir: 'ltr' },
  uk: { hreflang: 'uk', ogLocale: 'uk_UA', htmlLang: 'uk', dir: 'ltr' },
  ur: { hreflang: 'ur', ogLocale: 'ur_PK', htmlLang: 'ur', dir: 'rtl' },
  vi: { hreflang: 'vi', ogLocale: 'vi_VN', htmlLang: 'vi', dir: 'ltr' },
};

const normalizeSiteUrl = (url) => url.replace(/\/+$/, '');
const normalizeText = (value = '') => String(value).replace(/\s+/g, ' ').trim();
const toTitleCase = (value = '') => normalizeText(value)
  .toLowerCase()
  .replace(/\b([a-z])/g, (match) => match.toUpperCase());
const isChineseLanguage = (language) => language === 'zh_CN' || language === 'zh_TW';

const SECTION_SEO_TERMS = {
  docx_converter: {
    en: ['DOCX converter', 'Word to PDF', 'Word to image', 'DOCX online tools'],
    zh: ['DOCX转换器', 'Word转PDF', 'Word转图片', '文档转换工具'],
  },
  html_converter: {
    en: ['HTML converter', 'HTML to PDF', 'HTML to image', 'HTML online tools'],
    zh: ['HTML转换器', 'HTML转PDF', 'HTML转图片', '网页转换工具'],
  },
  json_converter: {
    en: ['JSON converter', 'JSON to YAML', 'JSON to XML', 'JSON online tools'],
    zh: ['JSON转换器', 'JSON转YAML', 'JSON转XML', '数据格式转换'],
  },
  pdf_converter: {
    en: ['PDF converter', 'PDF to Word', 'PDF to image', 'PDF online tools'],
    zh: ['PDF转换器', 'PDF转Word', 'PDF转图片', 'PDF在线工具'],
  },
  excel_converter: {
    en: ['Excel converter', 'Excel to PDF', 'Excel to image', 'spreadsheet converter'],
    zh: ['Excel转换器', 'Excel转PDF', 'Excel转图片', '表格转换工具'],
  },
  txt_converter: {
    en: ['TXT converter', 'text converter', 'TXT to PDF', 'TXT online tools'],
    zh: ['TXT转换器', '文本转换器', 'TXT转PDF', '文本处理工具'],
  },
  xml_converter: {
    en: ['XML converter', 'XML to JSON', 'XML to YAML', 'XML online tools'],
    zh: ['XML转换器', 'XML转JSON', 'XML转YAML', 'XML在线工具'],
  },
};

const TOOL_DESCRIPTION_MAP = {
  'DOCX To PDF': {
    en: 'Convert DOCX to PDF online for contracts, resumes, reports, and printable documents.',
    zh: '在线将 DOCX 转换为 PDF，适合合同、简历、报告和可打印文档。',
  },
  'PDF To DOCX': {
    en: 'Convert PDF to editable DOCX online for document reuse and office workflows.',
    zh: '在线将 PDF 转换为可编辑 DOCX，适合文档复用和办公流程。',
  },
  'XML To JSON': {
    en: 'Convert XML to JSON online for APIs, structured data, and developer workflows.',
    zh: '在线将 XML 转换为 JSON，适合接口、结构化数据和开发场景。',
  },
  'JSON To YAML': {
    en: 'Convert JSON to YAML online for config files, developer tooling, and readable data output.',
    zh: '在线将 JSON 转换为 YAML，适合配置文件、开发工具和可读性更高的数据输出。',
  },
  'HTML To PDF': {
    en: 'Convert HTML to PDF online for web page archiving, reports, and shareable documents.',
    zh: '在线将 HTML 转换为 PDF，适合网页存档、报告导出和分享文档。',
  },
  'PDF To JPG': {
    en: 'Convert PDF to JPG online for previews, image extraction, and visual sharing.',
    zh: '在线将 PDF 转换为 JPG，适合预览图、图片提取和视觉分享。',
  },
};

function buildToolKeywords(sourceTitle, targetTitle, language) {
  if (isChineseLanguage(language)) {
    return [
      `${sourceTitle}转${targetTitle}`,
      `${sourceTitle} 转 ${targetTitle}`,
      `${sourceTitle}转换器`,
      `${targetTitle}转换器`,
      '在线文件转换',
      '文档格式转换',
    ].join(', ');
  }

  return [
    `${sourceTitle} to ${targetTitle}`,
    `${sourceTitle} to ${targetTitle} converter`,
    `${sourceTitle} converter`,
    `${targetTitle} converter`,
    'online file converter',
    'document converter',
  ].join(', ');
}

function buildSectionKeywords(sectionName, sectionTitle, language) {
  const terms = SECTION_SEO_TERMS[sectionName];
  const extraTerms = isChineseLanguage(language) ? terms?.zh : terms?.en;
  const base = isChineseLanguage(language)
    ? [sectionTitle, `${sectionTitle}在线工具`, '在线文档转换', SITE_NAME]
    : [sectionTitle, `online ${sectionTitle}`, 'document conversion tools', SITE_NAME];
  return [...base, ...(extraTerms || [])].join(', ');
}

export function getWebSeoCategories() {
  return (categories.major_functions || [])
    .filter((section) => !WEB_DISABLED_SECTION_NAMES.has(section.name))
    .map((section) => ({
      ...section,
      tools: (section.tools || []).filter((tool) => {
        const toolName = tool.name || '';
        return !/^PPT\s+To\s+/i.test(toolName) && !/\s+To\s+PPT$/i.test(toolName);
      }),
    }))
    .filter((section) => (section.tools || []).length > 0);
}

export function getCanonicalUrl(pathname = '/') {
  const base = normalizeSiteUrl(SITE_URL);
  const path = pathname.startsWith('/') ? pathname : `/${pathname}`;
  return `${base}${path === '/' ? '' : path}`;
}

export function getLocalizedPath(pathname = '/', language = DEFAULT_LANGUAGE) {
  const path = pathname.startsWith('/') ? pathname : `/${pathname}`;
  if (!language || language === DEFAULT_LANGUAGE) {
    return path;
  }
  return `${path}?lng=${encodeURIComponent(language)}`;
}

export function getLocalizedUrl(pathname = '/', language = DEFAULT_LANGUAGE) {
  const canonical = getCanonicalUrl(pathname);
  if (!language || language === DEFAULT_LANGUAGE) {
    return canonical;
  }
  return `${canonical}?lng=${encodeURIComponent(language)}`;
}

export function getSeoLocaleMeta(language = DEFAULT_LANGUAGE) {
  return SEO_LANGUAGE_MAP[language] || SEO_LANGUAGE_MAP[DEFAULT_LANGUAGE];
}

export function getAlternateLanguageLinks(pathname = '/') {
  const links = Object.entries(SEO_LANGUAGE_MAP).map(([language, meta]) => ({
    language,
    hreflang: meta.hreflang,
    href: getLocalizedUrl(pathname, language),
  }));

  links.push({
    language: 'x-default',
    hreflang: 'x-default',
    href: getCanonicalUrl(pathname),
  });

  return links;
}

export function getSeoData({ pathname = '/', selectedTool, effectiveSection, t, language = DEFAULT_LANGUAGE }) {
  const localeMeta = getSeoLocaleMeta(language);
  const localizedCanonicalUrl = getLocalizedUrl(pathname, language);
  const alternateLinks = getAlternateLanguageLinks(pathname);
  const chinese = isChineseLanguage(language);

  if (selectedTool) {
    const [source = 'Document', target = 'File'] = selectedTool.split(' To ');
    const sourceTitle = toTitleCase(source);
    const targetTitle = toTitleCase(target);
    const mappedDescription = TOOL_DESCRIPTION_MAP[selectedTool]?.[chinese ? 'zh' : 'en'];
    return {
      title: chinese
        ? `${sourceTitle}转${targetTitle}在线转换器 | ${SITE_NAME}`
        : `${sourceTitle} to ${targetTitle} Converter Online Free | ${SITE_NAME}`,
      description: mappedDescription || (chinese
        ? `使用 ${SITE_NAME} 在线将 ${sourceTitle} 转换为 ${targetTitle}。支持浏览器直接转换、下载清晰、适合文档与数据格式处理。`
        : `Convert ${sourceTitle} to ${targetTitle} online at ${SITE_NAME}. Free, fast, browser-based document conversion with multilingual support and clean downloads.`),
      canonicalUrl: localizedCanonicalUrl,
      keywords: buildToolKeywords(sourceTitle, targetTitle, language),
      alternateLinks,
      locale: localeMeta,
    };
  }

  if (effectiveSection?.name) {
    const sectionTitle = normalizeText(t(`categories.${effectiveSection.name}`));
    return {
      title: chinese
        ? `${sectionTitle}在线工具大全 | ${SITE_NAME}`
        : `${sectionTitle} Online Tools | ${SITE_NAME}`,
      description: chinese
        ? `浏览 ${SITE_NAME} 的 ${sectionTitle} 页面，快速找到对应格式转换工具。支持文档、文本、图片、PDF、JSON、XML、HTML 和 Excel 等常见在线转换场景。`
        : `Explore ${sectionTitle} on ${SITE_NAME}. Convert files online with fast, multilingual tools for documents, text, images, PDF, JSON, XML, HTML, and Excel.`,
      canonicalUrl: localizedCanonicalUrl,
      keywords: buildSectionKeywords(effectiveSection.name, sectionTitle, language),
      alternateLinks,
      locale: localeMeta,
    };
  }

  return {
    title: chinese
      ? `${SITE_NAME} - 在线文档转换工具网站`
      : `${SITE_NAME} | Online Document Conversion Tools`,
    description: chinese
      ? `${SITE_NAME} 提供免费的在线文档转换工具，覆盖 DOCX、PDF、HTML、JSON、XML、TXT、Excel 和图片相关流程，适合搜索和直接使用。`
      : 'Free online document converter for DOCX, PDF, HTML, JSON, XML, TXT, Excel and image workflows. Fast, SEO-friendly, multilingual conversion tools for the web.',
    canonicalUrl: localizedCanonicalUrl,
    keywords: chinese
      ? '在线文档转换, 文件格式转换, DOCX转PDF, XML转JSON, JSON转YAML, HTML转换器, PDF转换器, Excel转换器'
      : 'online document converter, file converter, DOCX to PDF, XML to JSON, JSON to YAML, HTML converter, PDF converter, Excel converter',
    alternateLinks,
    locale: localeMeta,
  };
}

export function getSitemapEntries() {
  const entries = [{ path: '/' }];

  getWebSeoCategories().forEach((section) => {
    const sectionSlug = getCategorySlugBySectionName(section.name);
    if (sectionSlug) {
      entries.push({ path: `/tools/${sectionSlug}` });
    }

    (section.tools || []).forEach((tool) => {
      const [source, target] = tool.name.split(' To ');
      if (source && target) {
        entries.push({ path: `/tool/${source.toLowerCase()}/${target.toLowerCase()}` });
      }
    });
  });

  return entries;
}
