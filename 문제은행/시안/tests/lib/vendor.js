// 바깥 CDN 대신 같은 버전 로컬 사본을 넣는다.
// 클라우드 환경에서는 cdn.tailwindcss.com · cdnjs · jsdelivr 가 막혀 있다.
// QB_ONLINE=1 이면 아무것도 바꾸지 않고 진짜 CDN을 쓴다(PC에서 인터넷이 될 때).
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const TESTS = path.resolve(__dirname, '..');
const SIAN = path.resolve(TESTS, '..');
const PAGE = path.join(SIAN, '예시_화면시안.html');
const VENDOR = path.join(TESTS, '.vendor');
const NM = path.join(TESTS, 'node_modules');
const ONLINE = process.env.QB_ONLINE === '1';

// Tailwind Play CDN 대신: 같은 3.4 버전 CLI로 예시 화면에 쓰인 클래스만 CSS로 만든다.
function buildTailwind() {
  fs.mkdirSync(VENDOR, { recursive: true });
  const input = path.join(VENDOR, 'in.css');
  const out = path.join(VENDOR, 'tailwind.css');
  fs.writeFileSync(input, '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n');
  const cfg = path.join(VENDOR, 'tailwind.config.js');
  fs.writeFileSync(cfg, `module.exports={content:[${JSON.stringify(PAGE)}],theme:{extend:{}},plugins:[]};\n`);
  execFileSync(process.execPath, [path.join(NM, 'tailwindcss', 'lib', 'cli.js'), '-c', cfg, '-i', input, '-o', out, '--minify'], { stdio: 'pipe' });
  return out;
}

function tailwindShim() {
  const css = fs.readFileSync(path.join(VENDOR, 'tailwind.css'), 'utf8');
  // Play CDN 스크립트처럼 <head>에 <style>을 넣는다(동기 실행)
  return `(function(){var s=document.createElement('style');s.id='tw-local';s.textContent=${JSON.stringify(css)};(document.head||document.documentElement).appendChild(s)})();`;
}

const MIME = { '.css': 'text/css', '.js': 'application/javascript', '.woff2': 'font/woff2', '.woff': 'font/woff' };

async function installRoutes(context) {
  if (ONLINE) return;
  const tw = tailwindShim();
  await context.route('https://cdn.tailwindcss.com/**', r => r.fulfill({ status: 200, contentType: 'application/javascript', body: tw }));
  await context.route('https://cdn.tailwindcss.com', r => r.fulfill({ status: 200, contentType: 'application/javascript', body: tw }));
  await context.route('https://cdnjs.cloudflare.com/ajax/libs/qrcode-generator/1.4.4/qrcode.min.js', r =>
    r.fulfill({ status: 200, contentType: 'application/javascript', path: path.join(NM, 'qrcode-generator', 'qrcode.js') }));
  await context.route('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/**', r => {
    const rel = new URL(r.request().url()).pathname.split('/dist/web/')[1];
    let f = path.join(NM, 'pretendard', 'dist', 'web', decodeURIComponent(rel));
    if (!fs.existsSync(f)) f = f.replace(/\.min\.css$/, '.css');   // npm 꾸러미에는 .min.css 대신 .css
    if (fs.existsSync(f)) return r.fulfill({ status: 200, contentType: MIME[path.extname(f)] || 'application/octet-stream', path: f });
    return r.fulfill({ status: 404, body: '' });
  });
  // Google 글꼴은 시험에 필요 없다: 빈 CSS로 돌려준다(대체 글꼴로 그림)
  await context.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({ status: 200, contentType: 'text/css', body: '' }));
}

// 예시 화면은 file:// 대신 가짜 주소(http://qb.test/)로 연다. 그래야 icons/ 같은 곁 파일도 가로챌 수 있다.
const ORIGIN = 'http://qb.test';
const URL_PAGE = ORIGIN + '/' + encodeURIComponent('예시_화면시안.html');
// 1×1 투명 PNG
const BLANK_PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64');
const missingIcons = new Set();

async function installSite(context) {
  await context.route(ORIGIN + '/**', r => {
    const rel = decodeURIComponent(new URL(r.request().url()).pathname).replace(/^\//, '');
    const f = path.join(SIAN, rel);
    if (fs.existsSync(f) && fs.statSync(f).isFile()) {
      const ext = path.extname(f);
      return r.fulfill({ status: 200, contentType: ext === '.html' ? 'text/html; charset=utf-8' : (MIME[ext] || (ext === '.png' ? 'image/png' : ext === '.webp' ? 'image/webp' : 'application/octet-stream')), path: f });
    }
    // 3D 아이콘(icons/*.png)은 저장소에 올리지 않는 파일이다(.gitignore). 없으면 투명 그림으로 대신한다.
    if (/^icons\/.+\.png$/.test(rel)) { missingIcons.add(rel); return r.fulfill({ status: 200, contentType: 'image/png', body: BLANK_PNG }); }
    return r.fulfill({ status: 404, body: 'not found' });
  });
  await installRoutes(context);
}

module.exports = { TESTS, SIAN, PAGE, VENDOR, ONLINE, ORIGIN, URL_PAGE, missingIcons, buildTailwind, installRoutes, installSite };
