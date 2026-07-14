import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { SITE_NAME } from '../utils/seo';

function toTitle(value = '') {
  return String(value)
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b([a-z])/g, (match) => match.toUpperCase());
}

function buildLocalizedCopy({ selectedTool, effectiveSection, canonicalUrl, appTitle, t, localeCode }) {
  if (selectedTool) {
    const [source = 'Document', target = 'File'] = selectedTool.split(' To ');
    const sourceTitle = toTitle(source);
    const targetTitle = toTitle(target);
    const pageTitle = `${sourceTitle} to ${targetTitle}`;

    return {
      title: t('seoContent.tool_title', { pageTitle }),
      intro: t('seoContent.tool_intro', {
        siteName: SITE_NAME,
        source: sourceTitle,
        target: targetTitle,
      }),
      bullets: [
        t('seoContent.tool_bullet_1', { source: sourceTitle, target: targetTitle }),
        t('seoContent.tool_bullet_2'),
        t('seoContent.tool_bullet_3'),
      ],
      faq: [
        {
          q: t('seoContent.tool_faq_1_q', { source: sourceTitle, target: targetTitle }),
          a: t('seoContent.tool_faq_1_a', { pageTitle }),
        },
        {
          q: t('seoContent.tool_faq_2_q', { pageTitle }),
          a: t('seoContent.tool_faq_2_a'),
        },
        {
          q: t('seoContent.tool_faq_3_q', { pageTitle }),
          a: t('seoContent.tool_faq_3_a'),
        },
      ],
      breadcrumb: [
        { name: SITE_NAME, url: 'https://doc.kunqiongai.com' },
        { name: appTitle, url: 'https://doc.kunqiongai.com' },
        { name: pageTitle, url: canonicalUrl },
      ],
      schemaName: pageTitle,
      pageType: 'tool',
      featureList: [
        `${sourceTitle} to ${targetTitle}`,
        t('seoContent.schema_feature_multilingual'),
        t('seoContent.schema_feature_browser'),
      ],
      inLanguage: localeCode,
    };
  }

  if (effectiveSection?.name) {
    const sectionTitle = effectiveSection.displayName || effectiveSection.name;

    return {
      title: t('seoContent.section_title', { sectionTitle }),
      intro: t('seoContent.section_intro', { siteName: SITE_NAME, sectionTitle }),
      bullets: [
        t('seoContent.section_bullet_1', { sectionTitle }),
        t('seoContent.section_bullet_2'),
        t('seoContent.section_bullet_3'),
      ],
      faq: [
        {
          q: t('seoContent.section_faq_1_q', { sectionTitle }),
          a: t('seoContent.section_faq_1_a'),
        },
        {
          q: t('seoContent.section_faq_2_q', { sectionTitle }),
          a: t('seoContent.section_faq_2_a'),
        },
      ],
      breadcrumb: [
        { name: SITE_NAME, url: 'https://doc.kunqiongai.com' },
        { name: sectionTitle, url: canonicalUrl },
      ],
      schemaName: sectionTitle,
      pageType: 'section',
      inLanguage: localeCode,
    };
  }

  return {
    title: appTitle,
    intro: t('seoContent.home_intro', { siteName: SITE_NAME }),
    bullets: [
      t('seoContent.home_bullet_1'),
      t('seoContent.home_bullet_2'),
      t('seoContent.home_bullet_3'),
    ],
    faq: [
      {
        q: t('seoContent.home_faq_1_q', { siteName: SITE_NAME }),
        a: t('seoContent.home_faq_1_a', { siteName: SITE_NAME }),
      },
      {
        q: t('seoContent.home_faq_2_q'),
        a: t('seoContent.home_faq_2_a'),
      },
      {
        q: t('seoContent.home_faq_3_q'),
        a: t('seoContent.home_faq_3_a'),
      },
    ],
    breadcrumb: [{ name: SITE_NAME, url: canonicalUrl }],
    schemaName: SITE_NAME,
    pageType: 'home',
    inLanguage: localeCode,
  };
}

function SeoContent({ selectedTool, effectiveSection, canonicalUrl, locale }) {
  const { t } = useTranslation();

  const decoratedSection = useMemo(
    () => (effectiveSection ? { ...effectiveSection, displayName: t(`categories.${effectiveSection.name}`) } : null),
    [effectiveSection, t],
  );

  const content = useMemo(
    () =>
      buildLocalizedCopy({
        selectedTool,
        effectiveSection: decoratedSection,
        canonicalUrl,
        appTitle: t('header.app_title'),
        t,
        localeCode: locale?.htmlLang,
      }),
    [canonicalUrl, decoratedSection, locale?.htmlLang, selectedTool, t],
  );

  const schema = useMemo(() => {
    const appSchema = {
      '@context': 'https://schema.org',
      '@type': 'WebApplication',
      name: content.schemaName,
      applicationCategory: 'BusinessApplication',
      operatingSystem: 'Web',
      url: canonicalUrl,
      inLanguage: content.inLanguage,
      description: content.intro,
      isAccessibleForFree: true,
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD',
      },
    };

    if (content.pageType === 'tool') {
      appSchema.featureList = content.featureList;
      appSchema.softwareHelp = canonicalUrl;
    }

    return {
      breadcrumb: {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: content.breadcrumb.map((item, index) => ({
          '@type': 'ListItem',
          position: index + 1,
          name: item.name,
          item: item.url,
        })),
      },
      faq: {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: content.faq.map((item) => ({
          '@type': 'Question',
          name: item.q,
          acceptedAnswer: {
            '@type': 'Answer',
            text: item.a,
          },
        })),
      },
      app: appSchema,
    };
  }, [canonicalUrl, content]);

  return (
    <section className="seo-copy-block" aria-label={t('seoContent.aria_label')}>
      <div className="seo-copy-card">
        <div className="section-header">
          <div className="section-divider"></div>
          <h2 className="section-title">{content.title}</h2>
        </div>
        <p className="seo-copy-intro">{content.intro}</p>
        <div className="seo-copy-points">
          {content.bullets.map((item) => (
            <p key={item} className="seo-copy-point">{item}</p>
          ))}
        </div>
      </div>

      <div className="seo-copy-card">
        <div className="section-header">
          <div className="section-divider"></div>
          <h2 className="section-title">{t('seoContent.faq_title')}</h2>
        </div>
        <div className="seo-faq-list">
          {content.faq.map((item) => (
            <article key={item.q} className="seo-faq-item">
              <h3>{item.q}</h3>
              <p>{item.a}</p>
            </article>
          ))}
        </div>
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema.breadcrumb) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema.faq) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema.app) }}
      />
    </section>
  );
}

export default SeoContent;
