import { useEffect } from 'react';

function ensureMeta(selector, attributes) {
  let node = document.head.querySelector(selector);
  if (!node) {
    node = document.createElement('meta');
    document.head.appendChild(node);
  }

  Object.entries(attributes).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      node.setAttribute(key, value);
    }
  });

  return node;
}

function ensureLink(selector, attributes) {
  let node = document.head.querySelector(selector);
  if (!node) {
    node = document.createElement('link');
    document.head.appendChild(node);
  }

  Object.entries(attributes).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      node.setAttribute(key, value);
    }
  });

  return node;
}

function SeoHead({
  title,
  description,
  canonicalUrl,
  robots = 'index,follow',
  imageUrl,
  keywords,
  locale,
  alternateLinks = [],
}) {
  useEffect(() => {
    if (title) {
      document.title = title;
    }

    if (locale?.htmlLang) {
      document.documentElement.lang = locale.htmlLang;
    }
    if (locale?.dir) {
      document.documentElement.dir = locale.dir;
    }

    ensureMeta('meta[name="description"]', { name: 'description', content: description });
    ensureMeta('meta[name="keywords"]', { name: 'keywords', content: keywords });
    ensureMeta('meta[name="robots"]', { name: 'robots', content: robots });
    ensureMeta('meta[name="googlebot"]', { name: 'googlebot', content: robots });
    ensureMeta('meta[property="og:title"]', { property: 'og:title', content: title });
    ensureMeta('meta[property="og:description"]', { property: 'og:description', content: description });
    ensureMeta('meta[property="og:type"]', { property: 'og:type', content: 'website' });
    ensureMeta('meta[property="og:url"]', { property: 'og:url', content: canonicalUrl });
    ensureMeta('meta[property="og:image"]', { property: 'og:image', content: imageUrl });
    ensureMeta('meta[property="og:site_name"]', { property: 'og:site_name', content: 'KunqiongAI Doc' });
    ensureMeta('meta[property="og:locale"]', { property: 'og:locale', content: locale?.ogLocale || 'zh_CN' });
    ensureMeta('meta[name="twitter:site"]', { name: 'twitter:site', content: '@kunqiongai' });
    ensureMeta('meta[name="twitter:card"]', { name: 'twitter:card', content: 'summary_large_image' });
    ensureMeta('meta[name="twitter:title"]', { name: 'twitter:title', content: title });
    ensureMeta('meta[name="twitter:description"]', { name: 'twitter:description', content: description });
    ensureMeta('meta[name="twitter:image"]', { name: 'twitter:image', content: imageUrl });
    ensureLink('link[rel="canonical"]', { rel: 'canonical', href: canonicalUrl });

    document.head.querySelectorAll('link[data-seo="alternate"]').forEach((node) => node.remove());
    alternateLinks.forEach((item) => {
      const node = document.createElement('link');
      node.setAttribute('rel', 'alternate');
      node.setAttribute('hreflang', item.hreflang);
      node.setAttribute('href', item.href);
      node.setAttribute('data-seo', 'alternate');
      document.head.appendChild(node);
    });

    let jsonLdNode = document.head.querySelector('script[data-seo="json-ld"]');
    if (!jsonLdNode) {
      jsonLdNode = document.createElement('script');
      jsonLdNode.setAttribute('type', 'application/ld+json');
      jsonLdNode.setAttribute('data-seo', 'json-ld');
      document.head.appendChild(jsonLdNode);
    }

    jsonLdNode.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: 'KunqiongAI Doc',
      url: canonicalUrl,
      description,
      image: imageUrl,
      inLanguage: locale?.htmlLang || 'zh-CN',
      potentialAction: {
        '@type': 'SearchAction',
        target: 'https://doc.kunqiongai.com/?q={search_term_string}',
        'query-input': 'required name=search_term_string',
      },
    });
  }, [alternateLinks, canonicalUrl, description, imageUrl, keywords, locale, robots, title]);

  return null;
}

export default SeoHead;
