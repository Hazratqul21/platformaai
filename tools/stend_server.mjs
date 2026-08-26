/* Dizayn stendi uchun eng oddiy statik server. Faqat local ko'rish uchun. */
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
const ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const TYPES = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8',
  '.js':'text/javascript; charset=utf-8','.json':'application/json','.svg':'image/svg+xml',
  '.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2'};
http.createServer(async (req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/static/_stend.html';
  const file = path.join(ROOT, p);
  if (!file.startsWith(ROOT)) { res.writeHead(403).end('no'); return; }
  try {
    const buf = await readFile(file);
    res.writeHead(200, {'content-type': TYPES[path.extname(file)] || 'application/octet-stream',
                        'cache-control': 'no-store'});
    res.end(buf);
  } catch { res.writeHead(404, {'content-type':'text/plain'}).end('404 ' + p); }
}).listen(8777, () => console.log('stend: http://localhost:8777/'));
