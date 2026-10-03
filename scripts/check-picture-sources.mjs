// Regression check for GitHub's themed-picture behavior in fixed color modes.
// Observed vendor implementation: chunk-lazy-element-themed-picture-d247b2d8d9ad6894.js
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const documents = [
  { file: 'README.md', locale: 'en' },
  { file: 'README.zh-CN.md', locale: 'zh-CN' },
];
const pictures = documents.flatMap(({ file, locale }) => {
  const readme = fs.readFileSync(path.join(root, file), 'utf8');
  const content = readme.slice(readme.indexOf('<picture>'));
  assert.equal(/[\u3400-\u9fff]/u.test(content), locale === 'zh-CN', `${file}: wrong content language`);
  assert(readme.includes(locale === 'en'
    ? 'https://github.com/xwtaidev/xwtaidev/blob/main/README.zh-CN.md'
    : '[English](https://github.com/xwtaidev)'), `${file}: missing language link`);
  const result = [...readme.matchAll(/<picture>([\s\S]*?)<\/picture>/g)].map(match => {
    const sources = [...match[1].matchAll(/<source\s+media="([^"]+)"\s+srcset="([^"]+)"/g)]
      .map(source => ({ media: source[1], srcset: source[2] }));
    const fallback = match[1].match(/<img[^>]*\ssrc="([^"]+)"/)[1];
    for (const ref of [...sources.map(source => source.srcset), fallback]) {
      const svg = fs.readFileSync(path.join(root, ref), 'utf8');
      const description = svg.match(/<desc[^>]*>([\s\S]*?)<\/desc>/)[1];
      assert.equal(/[\u3400-\u9fff]/u.test(description), locale === 'zh-CN', `${file}: wrong image language: ${ref}`);
    }
    return { sources, fallback };
  });
  assert.equal(result.length, 4, file);
  return result;
});

function githubSources(sources, colorMode) {
  return sources.map(source => {
    const theme = source.media.includes('prefers-color-scheme: light') ? 'light'
      : source.media.includes('prefers-color-scheme: dark') ? 'dark' : null;
    if (colorMode === 'auto' || theme === null) return source;
    return { ...source, media: theme === colorMode
      ? '(prefers-color-scheme: light),(prefers-color-scheme: dark)' : 'not all' };
  });
}

function matches(media, width, systemTheme) {
  if (media === 'not all') return false;
  return media.split(',').some(clause => {
    const max = clause.match(/max-width:\s*(\d+)px/);
    const min = clause.match(/min-width:\s*(\d+)px/);
    const theme = clause.match(/prefers-color-scheme:\s*(light|dark)/);
    return (!max || width <= Number(max[1])) && (!min || width >= Number(min[1]))
      && (!theme || theme[1] === systemTheme);
  });
}

assert.equal(pictures.length, 8);
for (const { sources } of pictures) {
  const mobile = sources.find(source => source.media === '(max-width: 600px)');
  assert(mobile, 'Viewport selection must be independent of GitHub theme selection.');
  assert(mobile.srcset.endsWith('-mobile.svg'));
  const svg = fs.readFileSync(path.join(root, mobile.srcset), 'utf8');
  assert(svg.includes('@media (prefers-color-scheme: dark)'));
  assert(svg.includes('var(--text)'));
}
let checked = 0;
for (const width of [1440, 375, 600, 601]) {
  for (const mode of ['auto', 'light', 'dark']) {
    for (const systemTheme of ['light', 'dark']) {
      for (const picture of pictures) {
        const selected = githubSources(picture.sources, mode)
          .find(source => matches(source.media, width, systemTheme))?.srcset || picture.fallback;
        assert.equal(selected.includes('-mobile'), width <= 600,
          `Wrong SVG at ${width}px, GitHub=${mode}, system=${systemTheme}: ${selected}`);
        if (width > 600) {
          assert(selected.endsWith(`-${mode === 'auto' ? systemTheme : mode}.svg`), selected);
        }
        assert(fs.existsSync(path.join(root, selected)), selected);
        checked++;
      }
    }
  }
}
console.log(`Passed ${checked} GitHub picture selections across both languages, viewport and theme modes.`);
