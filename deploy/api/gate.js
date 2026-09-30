// Password gate for the RZD trainer assistant landing.
//
// Vercel's built-in Password Protection is Pro-only ($20/month/project), and the
// account is on Hobby, so access control is implemented here instead. The page
// is embedded in this function rather than shipped as a static file: a static
// copy would be served directly and the gate could be walked around.
//
// What this does:
//   - serves a login form until a valid session cookie is presented
//   - compares the password in constant time against GATE_PASSWORD
//   - issues an HMAC-signed, HttpOnly, SameSite=Strict cookie with a fixed TTL
//   - throttles repeated failures per IP (best effort: in-memory, per instance)
//
// Limits worth knowing: rate limiting is per instance and resets when the
// instance recycles, and the secret lives in a Vercel env var, so rotating the
// password is a redeploy.

const crypto = require('crypto');
const PAGE_HTML = require('./_page');

const COOKIE = 'gate';
const TTL_MS = 12 * 60 * 60 * 1000; // 12 hours

// module-level so a warm instance keeps counting between requests
const attempts = new Map();
const MAX_ATTEMPTS = 8;
const WINDOW_MS = 10 * 60 * 1000;
const BLOCK_MS = 5 * 60 * 1000;

function secret() {
  return process.env.GATE_PASSWORD || '';
}

function sign(payload) {
  return crypto.createHmac('sha256', secret()).update(payload).digest('hex');
}

function safeEqual(a, b) {
  const ba = Buffer.from(String(a));
  const bb = Buffer.from(String(b));
  if (ba.length !== bb.length) {
    // still burn a comparison so the timing does not reveal the length
    crypto.timingSafeEqual(ba, ba);
    return false;
  }
  return crypto.timingSafeEqual(ba, bb);
}

function clientIp(req) {
  const fwd = req.headers['x-forwarded-for'];
  if (typeof fwd === 'string' && fwd) return fwd.split(',')[0].trim();
  return req.socket?.remoteAddress || 'unknown';
}

function throttle(ip) {
  const now = Date.now();
  const rec = attempts.get(ip);
  if (!rec) return { blocked: false };
  if (rec.blockedUntil && rec.blockedUntil > now) {
    return { blocked: true, retryAfter: Math.ceil((rec.blockedUntil - now) / 1000) };
  }
  if (now - rec.first > WINDOW_MS) {
    attempts.delete(ip);
  }
  return { blocked: false };
}

function noteFailure(ip) {
  const now = Date.now();
  const rec = attempts.get(ip) || { count: 0, first: now, blockedUntil: 0 };
  if (now - rec.first > WINDOW_MS) { rec.count = 0; rec.first = now; }
  rec.count += 1;
  if (rec.count >= MAX_ATTEMPTS) {
    rec.blockedUntil = now + BLOCK_MS;
  }
  attempts.set(ip, rec);
  return rec.count;
}

function clearFailures(ip) {
  attempts.delete(ip);
}

function readCookie(req, name) {
  const raw = req.headers.cookie;
  if (!raw) return null;
  for (const part of raw.split(';')) {
    const idx = part.indexOf('=');
    if (idx === -1) continue;
    if (part.slice(0, idx).trim() === name) return part.slice(idx + 1).trim();
  }
  return null;
}

function tokenValid(token) {
  if (!token) return false;
  const dot = token.indexOf('.');
  if (dot === -1) return false;
  const exp = token.slice(0, dot);
  const mac = token.slice(dot + 1);
  if (!/^\d+$/.test(exp)) return false;
  if (Number(exp) < Date.now()) return false;
  return safeEqual(mac, sign(exp));
}

function issueCookie() {
  const exp = String(Date.now() + TTL_MS);
  return `${COOKIE}=${exp}.${sign(exp)}; Path=/; Max-Age=${Math.floor(TTL_MS / 1000)}; ` +
         'HttpOnly; SameSite=Strict; Secure';
}

const LOGIN_PAGE = `<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ассистент тренера РЖД — вход</title>
<style>
  :root { color-scheme: light dark; }
  body { margin:0; min-height:100vh; display:grid; place-items:center;
         background:#f5f7fa; color:#1a1a1a;
         font-family:'Segoe UI',Tahoma,system-ui,sans-serif; }
  form { background:#fff; border:2px solid #1a3a5c; border-radius:14px;
         padding:2rem 1.6rem; width:min(360px,90vw); }
  h1 { font-size:1.1rem; margin:0 0 1.2rem; color:#1a3a5c; }
  label { display:block; font-size:.85rem; margin-bottom:.4rem; color:#444; }
  input { width:100%; padding:.7rem .8rem; font-size:1rem; border:2px solid #888;
          border-radius:8px; box-sizing:border-box; }
  input:focus { outline:3px solid #1c6ea4; outline-offset:1px; }
  button { margin-top:1rem; width:100%; padding:.8rem; font-size:1rem; font-weight:600;
           background:#1a3a5c; color:#fff; border:0; border-radius:8px; cursor:pointer; }
  .err { color:#a3000f; font-size:.88rem; margin-top:.9rem; }
  @media (prefers-color-scheme: dark) {
    body { background:#11171d; color:#e4eaf0; }
    form { background:#1a222b; border-color:#7fb2e5; }
    h1 { color:#7fb2e5; } label { color:#b9c6d2; }
    input { background:#0e141a; color:#e4eaf0; border-color:#5a6b7a; }
  }
</style></head>
<body><form method="post" action="/">
  <h1>🚂 Ассистент тренера РЖД</h1>
  <label for="p">Пароль</label>
  <input id="p" name="p" type="password" autocomplete="current-password" autofocus required>
  <button type="submit">Войти</button>
  <!--ERR-->
</form></body></html>`;

function loginPage(message) {
  const block = message
    ? `<div class="err">${message}</div>`
    : '';
  return LOGIN_PAGE.replace('<!--ERR-->', block);
}

// Standard ServerResponse only. Express-style res.status()/res.send() are not
// guaranteed on every Vercel runtime, and the local test must exercise exactly
// the same code path as production.
function reply(res, status, headers, body) {
  res.statusCode = status;
  for (const [k, v] of Object.entries(headers || {})) res.setHeader(k, v);
  res.end(body);
}

const HTML = { 'Content-Type': 'text/html; charset=utf-8' };

module.exports = async function handler(req, res) {
  // no-store on everything: a shared cache must never hold the page
  res.setHeader('Cache-Control', 'no-store, max-age=0, must-revalidate');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('X-Robots-Tag', 'noindex, nofollow');

  if (!secret()) {
    return reply(res, 500, HTML,
      loginPage('Сервер не настроен: не задана переменная GATE_PASSWORD.'));
  }

  const ip = clientIp(req);
  const gate = throttle(ip);
  if (gate.blocked) {
    res.setHeader('Retry-After', String(gate.retryAfter));
    return reply(res, 429, HTML, loginPage(
      `Слишком много попыток. Подождите ${Math.ceil(gate.retryAfter / 60)} мин.`));
  }

  if (req.method === 'POST') {
    const given = (req.body && typeof req.body.p === 'string') ? req.body.p : '';
    if (safeEqual(given, secret())) {
      clearFailures(ip);
      res.setHeader('Set-Cookie', issueCookie());
      res.setHeader('Location', '/');
      return reply(res, 303, {}, '');
    }
    noteFailure(ip);
    return reply(res, 401, HTML, loginPage('Неверный пароль.'));
  }

  if (req.method === 'GET' || req.method === 'HEAD') {
    if (tokenValid(readCookie(req, COOKIE))) {
      // the page lives in ./page, injected at build time from ../index.html;
      // there is no static copy, so there is nothing to reach around the gate
      const body = req.method === 'HEAD' ? '' : PAGE_HTML;
      return reply(res, 200, { ...HTML, 'Content-Length': Buffer.byteLength(PAGE_HTML) }, body);
    }
    const body = loginPage('');
    return reply(res, 401, { ...HTML, 'Content-Length': Buffer.byteLength(body) }, body);
  }

  res.setHeader('Allow', 'GET, HEAD, POST');
  return reply(res, 405, HTML, loginPage(''));
};
