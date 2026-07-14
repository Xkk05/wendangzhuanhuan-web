import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { getAlternateLanguageLinks, getSitemapEntries, SITE_URL } from '../src/utils/seo.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const publicDir = path.resolve(__dirname, '../public');
const siteUrl = SITE_URL.replace(/\/+$/, '');

const uniqueEntries = new Map();
getSitemapEntries().forEach(({ path: pagePath }) => {
  getAlternateLanguageLinks(pagePath).forEach(({ href }) => {
    uniqueEntries.set(href, true);
  });
});

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${Array.from(uniqueEntries.keys())
  .map((href) => `  <url><loc>${href}</loc></url>`)
  .join('\n')}
</urlset>
`;

const robots = `User-agent: *
Allow: /

Sitemap: ${siteUrl}/sitemap.xml
`;

fs.mkdirSync(publicDir, { recursive: true });
fs.writeFileSync(path.join(publicDir, 'sitemap.xml'), sitemap, 'utf8');
fs.writeFileSync(path.join(publicDir, 'robots.txt'), robots, 'utf8');
