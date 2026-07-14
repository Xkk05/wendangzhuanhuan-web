import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import zhCNTranslation from './locales/zh_CN.json';
import zhTWTranslation from './locales/zh_TW.json';
import enTranslation from './locales/en.json';
import arTranslation from './locales/ar.json';
import bnTranslation from './locales/bn.json';
import deTranslation from './locales/de.json';
import esTranslation from './locales/es.json';
import faTranslation from './locales/fa.json';
import frTranslation from './locales/fr.json';
import heTranslation from './locales/he.json';
import hiTranslation from './locales/hi.json';
import idTranslation from './locales/id.json';
import itTranslation from './locales/it.json';
import jaTranslation from './locales/ja.json';
import koTranslation from './locales/ko.json';
import msTranslation from './locales/ms.json';
import nlTranslation from './locales/nl.json';
import plTranslation from './locales/pl.json';
import ptTranslation from './locales/pt.json';
import ptBRTranslation from './locales/pt_BR.json';
import ruTranslation from './locales/ru.json';
import swTranslation from './locales/sw.json';
import taTranslation from './locales/ta.json';
import thTranslation from './locales/th.json';
import tlTranslation from './locales/tl.json';
import trTranslation from './locales/tr.json';
import ukTranslation from './locales/uk.json';
import urTranslation from './locales/ur.json';
import viTranslation from './locales/vi.json';
import { isSuspiciousTranslation } from './utils/safeTranslation';

const resources = {
  zh_CN: zhCNTranslation,
  zh_TW: zhTWTranslation,
  en: enTranslation,
  ar: arTranslation,
  bn: bnTranslation,
  de: deTranslation,
  es: esTranslation,
  fa: faTranslation,
  fr: frTranslation,
  he: heTranslation,
  hi: hiTranslation,
  id: idTranslation,
  it: itTranslation,
  ja: jaTranslation,
  ko: koTranslation,
  ms: msTranslation,
  nl: nlTranslation,
  pl: plTranslation,
  pt: ptTranslation,
  pt_BR: ptBRTranslation,
  ru: ruTranslation,
  sw: swTranslation,
  ta: taTranslation,
  th: thTranslation,
  tl: tlTranslation,
  tr: trTranslation,
  uk: ukTranslation,
  ur: urTranslation,
  vi: viTranslation,
};

function sanitizeLocale(locale, fallback, localeName) {
  if (!locale || typeof locale !== 'object') {
    return locale;
  }

  if (Array.isArray(locale)) {
    return locale.map((item, index) => sanitizeLocale(item, fallback?.[index], localeName));
  }

  const result = {};

  for (const [key, value] of Object.entries(locale)) {
    const fallbackValue = fallback?.[key];

    if (value && typeof value === 'object') {
      result[key] = sanitizeLocale(value, fallbackValue, localeName);
      continue;
    }

    result[key] =
      isSuspiciousTranslation(value, localeName) && typeof fallbackValue === 'string'
        ? fallbackValue
        : value;
  }

  return result;
}

const sanitizedResources = Object.fromEntries(
  Object.entries(resources).map(([localeName, localeValue]) => [
    localeName,
    localeName === 'en' || localeName === 'zh_CN' || localeName === 'zh_TW'
      ? localeValue
      : sanitizeLocale(localeValue, enTranslation, localeName),
  ]),
);

i18n.use(LanguageDetector).use(initReactI18next).init({
  resources: Object.fromEntries(
    Object.entries(sanitizedResources).map(([localeName, translation]) => [
      localeName,
      { translation },
    ]),
  ),
  fallbackLng: 'zh_CN',
  debug: false,
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
