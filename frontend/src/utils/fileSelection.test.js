import test from 'node:test';
import assert from 'node:assert/strict';
import {
  clearSelectedConversionResults,
  getSelectedFileQueue,
} from './fileSelection.js';

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
