// 목차 줄의 '이전 문항·다음 문항' 단추가 실제로 앞뒤 문항의 첫 장으로 옮기는지, 폰에서 목차 줄이 이동한 장의 위쪽을 가리지 않는지 본다.
// 문항 9개짜리 가짜 회차(tests/make_many.py)를 연계 지도 있는 것과 없는 것 두 가지로 만들어 크롬으로 연다.
//   node nav_click.js [시험할.html]      (파일을 주지 않으면 가짜 회차 두 가지를 만들어 쓴다. 파일에 지도가 있는지는 저절로 알아본다)
const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const path = require('path');
const os = require('os');
const {execFileSync} = require('child_process');
const skeleton = require('../tools/skeleton');       // Artifact 와 같은 틀(표준 모드)을 씌워 연다

const files = process.argv[2]
  ? [path.resolve(process.argv[2])]
  : [false, true].map(nomap => {
      const f = path.join(os.tmpdir(), 'nav_many_' + process.pid + (nomap ? '_nomap' : '') + '.html');
      execFileSync('python3', ['-I', path.join(__dirname, 'make_many.py'), f, '9'].concat(nomap ? ['--nomap'] : []));
      return f;
    });

(async () => {
  const browser = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  const fails = [];
  const ok = [];

  async function open(file, w, h) {
    const pg = await browser.newPage({viewport: {width: w, height: h}});
    await pg.goto('file://' + file);
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(1800);
    return pg;
  }
  // 장 위쪽이 목차 줄 바로 아래에 오는지(가려지지 않는지): 장 위쪽 - 목차 줄 아래 = 여백
  const gap = (pg, id) => pg.evaluate(i => Math.round(document.getElementById(i).getBoundingClientRect().top - document.querySelector('nav').getBoundingClientRect().bottom), id);
  async function go(pg, dir) { await pg.click('nav [data-go=' + dir + ']'); await pg.waitForTimeout(1300); }
  async function expectAt(pg, label, id) {
    const g = await gap(pg, id);
    if (g < 0 || g > 40) fails.push(label + ': #' + id + ' 가 목차 줄 아래 ' + g + 'px (0~40px 이어야 함)');
    else ok.push(label);
  }
  const jump = async (pg, id, i = 0) => {          // id 문항의 i번째 장으로 곧바로 내려가 둔다
    await pg.evaluate(([id, i]) => { const S = [...document.querySelectorAll('.slide')]; S[S.findIndex(s => s.id === id) + i].scrollIntoView({block: 'start'}); }, [id, i]);
    await pg.waitForTimeout(500);
  };

  for (const src of files) {
    const prep = skeleton.prepared(src), file = prep.file;
    for (const [w, h] of [[1300, 800], [390, 844]]) {
      const pg = await open(file, w, h);
      const hasMap = await pg.evaluate(() => !!document.getElementById('map'));
      const tag = '폭 ' + w + (hasMap ? ' 지도 있음 ' : ' 지도 없음 ');
      // 지도가 있으면 맨 위는 지도라서 첫 '다음 문항'이 1번, 없으면 맨 위가 이미 1번이라 2번으로 간다
      const a = hasMap ? 1 : 2;
      await go(pg, 'next'); await expectAt(pg, tag + (hasMap ? '지도에서' : '1번에서') + ' 다음 문항 → ' + a + '번', 'q' + a);
      await go(pg, 'next'); await expectAt(pg, tag + a + '번에서 다음 문항 → ' + (a + 1) + '번', 'q' + (a + 1));
      await go(pg, 'next'); await expectAt(pg, tag + (a + 1) + '번에서 다음 문항 → ' + (a + 2) + '번', 'q' + (a + 2));
      // 한 문항의 세 번째 장(비교)으로 내려가 다음 문항을 누르면 그 다음 문항 첫 장이어야 한다(그 문항의 다음 장이 아니라)
      await jump(pg, 'q' + (a + 2), 2);
      await go(pg, 'next'); await expectAt(pg, tag + (a + 2) + '번 가운데 장에서 다음 문항 → ' + (a + 3) + '번', 'q' + (a + 3));
      await go(pg, 'prev'); await expectAt(pg, tag + (a + 3) + '번에서 이전 문항 → ' + (a + 2) + '번', 'q' + (a + 2));
      // 1번에서 이전 문항: 지도가 있으면 지도로, 없으면 1번에 그대로
      await jump(pg, 'q1');
      await go(pg, 'prev'); await expectAt(pg, tag + '1번에서 이전 문항 → ' + (hasMap ? '지도' : '1번 그대로'), hasMap ? 'map' : 'q1');
      // 맨 끝 문항에서 다음 문항: 움직이지 않는다
      await jump(pg, 'q9');
      const before = await pg.evaluate(() => Math.round(window.scrollY));
      await go(pg, 'next');
      const after = await pg.evaluate(() => Math.round(window.scrollY));
      if (Math.abs(after - before) > 2) fails.push(tag + '마지막 문항에서 다음 문항이 움직임 ' + before + ' → ' + after); else ok.push(tag + '마지막 문항에서 다음 문항은 가만히');
      // 번호 알약이 아닌 일반 목차 링크(연계 지도)도 가려지지 않는지
      if (hasMap) {
        await jump(pg, 'q5');
        await pg.click('nav a[href="#map"]'); await pg.waitForTimeout(1300); await expectAt(pg, tag + '목차 줄의 연계 지도 링크', 'map');
      }
      await pg.close();
    }
    prep.done();
  }
  await browser.close();
  ok.forEach(l => console.log('통과 ' + l));
  fails.forEach(l => console.log('실패 ' + l));
  console.log(fails.length ? '이전·다음 문항 시험 실패 ' + fails.length + '건' : '이전·다음 문항 시험 통과 (' + ok.length + '건)');
  process.exit(fails.length ? 1 : 0);
})();
