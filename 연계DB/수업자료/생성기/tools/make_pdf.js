// 수업용 HTML 한 파일을 PDF 로 만든다. 장 하나 = 쪽 하나(1280×720px), 마지막에 아이콘 저작권 표시 쪽이 하나 붙는다.
//   node make_pdf.js 입력.html 출력.pdf
// PDF 에서만 아이콘 그림자(filter)를 끈다: 크롬이 filter 가 걸린 요소를 쪽마다 300ppi 그림으로 새로 만들어 넣어서
// 120쪽이 15.9MB 가 되는데, 끄면 5.7MB 로 줄어든다(2026-10-23 실측). 화면용 HTML 은 그대로다.
const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const path = require('path');
const fs = require('fs');
const {execFileSync} = require('child_process');
const skeleton = require('./skeleton');       // Artifact 와 같은 틀(표준 모드)을 씌워 연다. 안 그러면 괴상 모드로 읽혀 PDF 배치가 화면과 다르다
const [inFile, outFile] = process.argv.slice(2);
if (!inFile || !outFile) { console.log('사용: node make_pdf.js 입력.html 출력.pdf'); process.exit(2); }

const PRINT_CSS = `
  @page{size:1280px 720px;margin:0}
  html,body{margin:0!important;padding:0!important;background:#14241f!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  nav{display:none!important}
  .slide{width:1280px!important;max-width:none!important;margin:0!important;border-radius:0!important;box-shadow:none!important;break-after:page;page-break-after:always;break-inside:avoid}
  .slide:last-of-type{break-after:auto;page-break-after:auto}
  .ic{filter:none!important}
  body.chalk .i-cap,body.chalk .i-magnify{filter:drop-shadow(0 0 1px rgba(255,255,255,.8))!important}
  .credit{display:flex!important;align-items:center;justify-content:center;width:1280px;height:720px;margin:0!important;padding:0!important;
    color:#b8c9bd;font-size:18px;text-align:center;break-before:page;page-break-before:always}
`;

(async () => {
  const browser = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  const pg = await browser.newPage({viewport: {width: 1280, height: 720}});
  pg.setDefaultTimeout(900000);
  const t0 = Date.now();
  const prep = skeleton.prepared(inFile);
  await pg.goto('file://' + prep.file, {waitUntil: 'load'});
  await pg.evaluate(() => document.fonts.ready);
  await pg.waitForTimeout(3000);
  await pg.addStyleTag({content: PRINT_CSS});
  const slides = await pg.evaluate(() => { fit(); return document.querySelectorAll('.slide').length; });
  await pg.waitForTimeout(800);
  await pg.evaluate(() => document.fonts.ready);
  const t1 = Date.now();
  await pg.pdf({path: outFile, width: '1280px', height: '720px', printBackground: true, preferCSSPageSize: true});
  await browser.close();
  prep.done();
  const bytes = fs.statSync(outFile).size;
  let pages = null;
  try {
    const info = execFileSync('pdfinfo', [outFile], {encoding: 'utf8'});
    pages = +(info.match(/^Pages:\s+(\d+)/m) || [])[1];
  } catch (e) { /* pdfinfo 가 없으면 쪽 수 확인은 건너뜀 */ }
  const expect = slides + 1;
  const ok = pages === null || pages === expect;
  console.log(JSON.stringify({file: path.basename(inFile), out: path.basename(outFile), slides, pages, expectPages: expect, MB: +(bytes / 1048576).toFixed(2), loadSec: +((t1 - t0) / 1000).toFixed(1), pdfSec: +((Date.now() - t1) / 1000).toFixed(1)}));
  if (!ok) { console.log('쪽 수가 다릅니다: 장 ' + slides + '개 + 저작권 쪽 1개 = ' + expect + '쪽이어야 하는데 ' + pages + '쪽'); process.exit(1); }
  if (bytes > 8 * 1048576 * Math.max(1, slides / 120)) console.log('주의: 용량이 큼 (120장당 8MB 넘음). 아이콘 그림자(filter)가 다시 켜졌는지 확인');
})();
