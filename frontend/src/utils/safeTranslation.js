const MOJIBAKE_PATTERN = /\?{2,}|锟|婕|閿|涓|鍙|鍔|鐧|绗|璇|璩|喈|喙|袪|袧|賱|丕|啶|鞀|鞂|雽|頃|艧|茫|峄|鑴|||/;

export function isSuspiciousTranslation(value, locale) {
  if (typeof value !== 'string') {
    return false;
  }

  if (locale === 'zh_CN' || locale === 'zh_TW') {
    return false;
  }

  return MOJIBAKE_PATTERN.test(value);
}

export function createSafeTranslator(rawT, fallbackT, locale) {
  return function safeT(key, options) {
    const result = rawT(key, options);

    if (result === key || isSuspiciousTranslation(result, locale)) {
      return fallbackT(key, options);
    }

    return result;
  };
}
