// Builds deploy/api/page.js from ../index.html.
//
// The page is embedded in a serverless function rather than shipped as a static
// file: a static copy would be served by Vercel directly and the password gate
// could be bypassed by requesting that path.
//
//   node deploy/build-gate.mjs            # rebuild from ../index.html
//   node deploy/build-gate.mjs --check    # exit 1 if page.js is stale

import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, '..', 'index.html');
const target = join(here, 'api', '_page.js');

const html = readFileSync(source, 'utf8');

if (!/<html lang="ru"/.test(html)) throw new Error('index.html не похож на страницу ассистента');
if (!/rel="icon"/.test(html)) throw new Error('в index.html нет иконки — сборка остановлена');
// </script> is harmless here: this is a real .js module, not inline HTML.
// The characters that do break a JS string literal are the Unicode line
// separators, which JSON.stringify leaves untouched.
const literal = JSON.stringify(html).replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
if (/\u2028|\u2029/.test(literal)) {
  // the escapes above must have neutralised them; fail loudly if not
  throw new Error('не удалось экранировать разделители строк U+2028/U+2029');
}

const built =
  '// СГЕНЕРИРОВАНО из ../index.html — не править руками.\n' +
  '// Соберите заново:  node deploy/build-gate.mjs\n' +
  'module.exports = ' + literal + ';\n';

if (process.argv.includes('--check')) {
  let current = null;
  try { current = readFileSync(target, 'utf8'); } catch { /* нет файла */ }
  if (current !== built) {
    console.error('_page.js устарел: index.html изменился. Запустите node deploy/build-gate.mjs');
    process.exit(1);
  }
  console.log('_page.js актуален');
} else {
  writeFileSync(target, built);
  console.log(`page.js собран: ${(html.length / 1024).toFixed(0)} КБ страницы`);
}
