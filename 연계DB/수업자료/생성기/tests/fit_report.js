// 자동 맞춤(fit)이 장마다 글자를 얼마나 키우거나 줄였는지 보고한다.
//   node fit_report.js 파일.html                  # 폭 4가지에서 장별 배율을 한 줄씩
//   node fit_report.js 기준.html 새것.html        # 두 파일의 배율을 비교해, 새것에서 글자가 줄어든 장만 보여 준다
// 문항 장(.q)은 zoom(1이 기본, 줄면 글자가 작아짐), 교사 분석 장(.rows)은 --rs(1이 기본)를 본다.
const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const path = require('path');
const skeleton = require('../tools/skeleton');       // Artifact 와 같은 틀(표준 모드)을 씌워 연다
const files = process.argv.slice(2).map(f => path.resolve(f));
if (!files.length || files.length > 2) { console.log('사용: node fit_report.js 파일.html [새것.html]'); process.exit(2); }
const WIDTHS = [1300, 1000, 820, 710];

async function grab(browser, file, w) {
  const pg = await browser.newPage({viewport: {width: w, height: 800}});
  const prep = skeleton.prepared(file);
  await pg.goto('file://' + prep.file);                  // 구글 글꼴을 그대로 내려받아 실제 화면과 같게 잰다
  await pg.evaluate(() => document.fonts.ready);
  await pg.waitForTimeout(2500);                         // 글꼴 도착 뒤 fit() 이 다시 도는 시간
  const r = await pg.evaluate(() => [...document.querySelectorAll('.slide')].map((s, i) => {
    const q = s.querySelector('.q:not(.twofig)'), rows = s.querySelector('.rows');
    const z = q && q.children[0] ? parseFloat(q.children[0].style.zoom || 1) : null;
    const rs = rows ? parseFloat(rows.style.getPropertyValue('--rs') || 1) : null;
    return {i, z, rs};
  }));
  await pg.close();
  prep.done();
  return r;
}

(async () => {
  const browser = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  const res = files.map(() => ({}));
  for (let k = 0; k < files.length; k++) for (const w of WIDTHS) res[k][w] = await grab(browser, files[k], w);
  await browser.close();
  if (files.length === 1) {
    for (const w of WIDTHS) {
      const row = res[0][w].map(x => x.z != null ? x.z.toFixed(2) : (x.rs != null ? 'r' + x.rs.toFixed(2) : '-'));
      console.log(w + ': ' + row.join(' '));
    }
    return;
  }
  let shrunk = 0, grew = 0;
  for (const w of WIDTHS) {
    res[0][w].forEach((a, i) => {
      const b = res[1][w][i];
      const va = a.z != null ? a.z : a.rs, vb = b.z != null ? b.z : b.rs;
      if (va == null || vb == null || Math.abs(va - vb) < 0.005) return;
      const pct = ((vb / va - 1) * 100).toFixed(1);
      if (vb < va) shrunk++; else grew++;
      console.log('폭 ' + w + ' 장 ' + (i + 1) + ': ' + va.toFixed(2) + ' -> ' + vb.toFixed(2) + ' (' + pct + '%)' + (vb < va ? '  줄어듦' : '  커짐'));
    });
  }
  console.log('줄어든 곳 ' + shrunk + ', 커진 곳 ' + grew + ' (장 × 폭 ' + res[0][WIDTHS[0]].length * WIDTHS.length + '곳 중)');
})();
