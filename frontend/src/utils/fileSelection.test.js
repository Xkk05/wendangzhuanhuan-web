import test from 'node:test';
import assert from 'node:assert/strict';
import {
  clearSelectedConversionResults,
  getSelectedFileQueue,
} from './fileSelection.js';
import {
  isHtmlImageAsset,
  isPortableHtmlAssetTarget,
} from './htmlAssetInlining.js';

const files = [
  { id: 'first', file: { name: 'first.docx' } },
  { id: 'second', file: { name: 'second.docx' } },
  { id: 'third', file: { name: 'third.docx' } },
];

test('returns an empty conversion queue when no files are selected', () => {
  assert.deepEqual(getSelectedFileQueue(files, new Set()), []);
});

test('returns only explicitly selected files in list order', () => {
  const queue = getSelectedFileQueue(files, new Set(['third', 'first']));

  assert.deepEqual(queue.map((item) => item.id), ['first', 'third']);
});

test('clears results only for files in the selected conversion queue', () => {
  const results = {
    first: { download_url: '/first.pdf' },
    second: { download_url: '/second.pdf' },
  };

  assert.deepEqual(clearSelectedConversionResults(results, new Set(['first'])), {
    second: { download_url: '/second.pdf' },
  });
  assert.equal(results.first.download_url, '/first.pdf');
});

test('recognizes image files as HTML folder assets', () => {
  assert.equal(isHtmlImageAsset({ name: 'cover.PNG', type: '' }), true);
  assert.equal(isHtmlImageAsset({ name: 'avatar', type: 'image/webp' }), true);
  assert.equal(isHtmlImageAsset({ name: 'style.css', type: 'text/css' }), false);
});

test('limits portable HTML asset inlining to Word and Markdown targets', () => {
  assert.equal(isPortableHtmlAssetTarget('HTML', 'WORD'), true);
  assert.equal(isPortableHtmlAssetTarget('HTML', 'MARKDOWN'), true);
  assert.equal(isPortableHtmlAssetTarget('HTML', 'PDF'), false);
  assert.equal(isPortableHtmlAssetTarget('PDF', 'WORD'), false);
});
