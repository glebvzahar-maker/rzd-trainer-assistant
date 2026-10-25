// Builds the GitHub Pages artefact from ../index.html.
//
// Why this exists: GitHub Pages serves static files and nothing else, so it
// cannot check a password on the server. The Vercel deployment does check it
// for real (deploy/api/gate.js never hands out the page without a valid
// session cookie), but there the page lives inside a serverless function and
// depends on that function staying up.
//
// For Pages the gate runs in the browser instead: the whole catalogue is hidden
// behind a password form, and the password is checked with PBKDF2-SHA256
// against a salted hash that is baked into the built page.
//
// Be clear about what this is: a courtesy lock, not a security boundary.
// The catalogue travels in the same file as the page, so anyone who can fetch
// the file can read it without entering the password. Use the Vercel deployment
// when the content has to stay secret.
//
//   node deploy/build-pages.mjs                       # password from GATE_PASSWORD
//   node deploy/build-pages.mjs --password 3321
//   node deploy/build-pages.mjs --out ../docs

import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { pbkdf2Sync, randomBytes } from 'node:crypto';

const here = dirname(fileURLToPath(import.meta.url));
const source = join(here, '..', 'index.html');

const args = process.argv.slice(2);
const argValue = (name) => {
  const i = args.indexOf(name);
  return i === -1 ? undefined : args[i + 1];
};

const password = argValue('--password') ?? process.env.GATE_PASSWORD;
const outDir = resolve(here, '..', argValue('--out') ?? 'docs');

// enough to make an offline search expensive without making the phone wait
// for seconds on every attempt
const ITERATIONS = 210000;

if (!password) {
  console.error('Пароль не задан: передайте --password или задайте GATE_PASSWORD.');
  process.exit(1);
}

const html = readFileSync(source, 'utf8');

const CONFIG_RE = /window\.__GATE__\s*=\s*\{[^}]*\};/;
if (!CONFIG_RE.test(html)) {
  throw new Error('в index.html нет блока window.__GATE__ — сборка остановлена');
}

const salt = randomBytes(16).toString('base64');
const sessionSalt = randomBytes(16).toString('base64');
const hash = pbkdf2Sync(password, Buffer.from(salt, 'base64'), ITERATIONS, 32, 'sha256').toString('base64');

const config =
  `window.__GATE__ = { enabled: true, salt: ${JSON.stringify(salt)}, ` +
  `sessionSalt: ${JSON.stringify(sessionSalt)}, iterations: ${ITERATIONS}, ` +
  `hash: ${JSON.stringify(hash)}, days: 30 };`;

const built = html.replace(CONFIG_RE, config);

if (!/rel="icon"/.test(built)) throw new Error('в index.html нет иконки — сборка остановлена');
if (built === html) throw new Error('конфигурация гейта не подставилась — сборка остановлена');

rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });
writeFileSync(join(outDir, 'index.html'), built, 'utf8');

// the catalogue in markdown is handy for reading the site without a browser
try {
  writeFileSync(join(outDir, 'Активности_для_лендинга.md'),
    readFileSync(join(here, '..', 'Активности_для_лендинга.md')), 'utf8');
} catch { /* каталога нет — не страшно */ }

console.log(`страница для Pages собрана: ${outDir}`);
console.log(`  гейт включён, итераций PBKDF2: ${ITERATIONS}`);
console.log(`  пароль в файле не хранится — только соль и хеш`);
