// 두 HTML 이 화면에서 똑같은지 본다.
// 스크립트가 다 돈 뒤의 본문 조각(스크립트 제외)과, 장마다 모든 칸의 자리·크기를 PC 폭과 폰 폭에서 비교한다.
// 글꼴을 내려받는 시간 때문에 생기는 차이를 없애려고 구글 글꼴 요청은 막고 두 파일 모두 같은 대체 글꼴로 그린다.
//   node dom_identity.js 기준.html 새것.html
const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const path = require('path');
const skeleton = require('../tools/skeleton');       // Artifact 와 같은 틀(표준 모드)을 씌워 연다
const [A, B] = process.argv.slice(2).map(f => path.resolve(f));
if (!A || !B) { console.log('사용: node dom_identity.js 기준.html 새것.html'); process.exit(2); }
const norm = h => h.replace(/c\d+-(exam|book)/g, "c-$1");   // 도표 id 의 문항 번호는 다를 수 있다(생성기는 c25-exam, 기준본은 c-exam)

async function grab(browser, file, w) {
  const pg = await browser.newPage({viewport: {width: w, height: 800}});
  pg.on('pageerror', e => console.log('페이지 오류', path.basename(file), e.message));
  await pg.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  const prep = skeleton.prepared(file);
  await pg.goto('file://' + prep.file);
  await pg.waitForTimeout(2500);
  const r = await pg.evaluate(() => {
    const body = document.body.cloneNode(true);
    body.querySelectorAll('script').forEach(s => s.remove());
    const rects = [];
    document.querySelectorAll('.slide').forEach((s, i) => {
      const o = s.getBoundingClientRect();
      s.querySelectorAll('*').forEach(e => {
        const r = e.getBoundingClientRect();
        rects.push(i + ' ' + e.tagName + '.' + (typeof e.className === 'string' ? e.className : '') + ' ' +
          [r.left - o.left, r.top - o.top, r.width, r.height].map(v => Math.round(v * 10) / 10).join(','));
      });
    });
    return {html: body.innerHTML, rects, slides: document.querySelectorAll('.slide').length};
  });
  await pg.close();
  prep.done();
  return r;
}

(async () => {
  const browser = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  let bad = 0;
  for (const w of [1200, 390]) {
    const a = await grab(browser, A, w), b = await grab(browser, B, w);
    const ah = norm(a.html), bh = norm(b.html);
    const sameHtml = ah === bh;
    let diffRects = 0, first = '';
    const ar = a.rects.map(norm), br = b.rects.map(norm);
    if (ar.length !== br.length) { diffRects = -1; first = '칸 수가 다름 ' + ar.length + ' / ' + br.length; }
    else ar.forEach((x, i) => { if (x !== br[i]) { diffRects++; if (!first) first = x + '  <->  ' + br[i]; } });
    console.log('폭 ' + w + ': 장 ' + a.slides + '/' + b.slides + ', 본문 ' + (sameHtml ? '같음' : '다름') + ', 칸 자리·크기 ' + (diffRects === 0 ? '같음 (' + ar.length + '칸)' : '다름 ' + diffRects + '곳, 첫 차이: ' + first));
    if (!sameHtml) {
      let i = 0; while (i < ah.length && ah[i] === bh[i]) i++;
      console.log('   본문 첫 차이 위치 ' + i + ': ' + JSON.stringify(ah.slice(Math.max(0, i - 60), i + 80)) + ' <-> ' + JSON.stringify(bh.slice(Math.max(0, i - 60), i + 80)));
    }
    if (!sameHtml || diffRects !== 0) bad++;
  }
  await browser.close();
  console.log(bad ? '결과: 차이 있음' : '결과: 화면이 똑같음');
  process.exit(bad ? 1 : 0);
})();
