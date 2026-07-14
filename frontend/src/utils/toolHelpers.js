import { categories } from '../data.js';

const CATEGORY_SLUG_TO_SECTION_NAME = {
  doc: 'docx_converter',
  docx: 'docx_converter',
  html: 'html_converter',
  json: 'json_converter',
  pdf: 'pdf_converter',
  ppt: 'ppt_converter',
  excel: 'excel_converter',
  txt: 'txt_converter',
  xml: 'xml_converter',
};

const SECTION_NAME_TO_CATEGORY_SLUG = {
  docx_converter: 'docx',
  html_converter: 'html',
  json_converter: 'json',
  pdf_converter: 'pdf',
  ppt_converter: 'ppt',
  excel_converter: 'excel',
  txt_converter: 'txt',
  xml_converter: 'xml',
};

export const getAllTools = () => {
  return Object.values(categories).flat().flatMap(section => 
    section.tools.map(tool => ({ ...tool, sectionName: section.name }))
  );
};

export const findToolByName = (name) => {
  const allTools = getAllTools();
  return allTools.find(tool => tool.name === name);
};

export const findSectionByToolName = (toolName) => {
  const sections = Object.values(categories).flat();
  for (const section of sections) {
    if (section.tools.some(t => t.name === toolName)) {
      return section;
    }
  }
  return null;
};

export const getSectionByCategorySlug = (slug) => {
  if (!slug) {
    return null;
  }

  const sectionName = CATEGORY_SLUG_TO_SECTION_NAME[slug.toLowerCase()];
  if (!sectionName) {
    return null;
  }

  return categories.major_functions.find((section) => section.name === sectionName) || null;
};

export const getCategorySlugBySectionName = (sectionName) =>
  SECTION_NAME_TO_CATEGORY_SLUG[sectionName] || null;

export const getCategoryByExtension = (ext) => {
  const extension = ext.toLowerCase().replace('.', '');
  const map = {
    'docx': 'docx_converter',
    'doc': 'docx_converter',
    'html': 'html_converter',
    'htm': 'html_converter',
    'json': 'json_converter',
    'pdf': 'pdf_converter',
    'ppt': 'ppt_converter',
    'pptx': 'ppt_converter',
    'xls': 'excel_converter',
    'xlsx': 'excel_converter',
    'txt': 'txt_converter',
    'xml': 'xml_converter'
  };
  return map[extension];
};
