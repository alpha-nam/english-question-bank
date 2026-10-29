const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const path = require('path');
const fs = require('fs');
const dir = __dirname;
fs.mkdirSync(path.join(dir, 'shots'), {recursive: true});
(async () => {
  const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  async function open(file, w, h) {
    const pg = await b.newPage({viewport: {width: w, height: h}});
    await pg.goto('file://' + path.join(dir, file));
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(2500);
    return pg;
  }
  // 1. 회차 파일 첫 장 (PC)
  let pg = await open('slide_mock.html', 1300, 900);
  await pg.addStyleTag({content: 'nav{position:static!important}'});
  let r = await pg.evaluate(() => { const m = document.querySelector('#map').getBoundingClientRect(); return {bottom: m.bottom + scrollY, w: m.width, h: m.height}; });
  console.log('map slide', r);
  await pg.screenshot({path: path.join(dir, 'shots/slide_pc.png'), clip: {x: 0, y: 0, width: 1300, height: Math.ceil(r.bottom + 14)}});
  await pg.close();
  // 2. 전체 첫 화면 (PC) 기본 탭과 다른 탭
  pg = await open('index_mock.html', 1300, 900);
  await pg.screenshot({path: path.join(dir, 'shots/index_pc.png'), fullPage: true});
  await pg.click('.tabs button[data-r="2025.09"]');
  await pg.waitForTimeout(300);
  await pg.screenshot({path: path.join(dir, 'shots/index_pc_other.png'), fullPage: true});
  await pg.close();
  // 3. 폰
  pg = await open('slide_mock.html', 390, 844);
  await pg.addStyleTag({content: 'nav{position:static!important}'});
  r = await pg.evaluate(() => { const m = document.querySelector('#map').getBoundingClientRect(); return {bottom: m.bottom + scrollY, w: m.width, h: m.height, sw: document.documentElement.scrollWidth}; });
  console.log('phone map', r);
  await pg.screenshot({path: path.join(dir, 'shots/slide_phone.png'), fullPage: true, clip: {x: 0, y: 0, width: 390, height: Math.ceil(r.bottom + 14)}});
  await pg.close();
  pg = await open('index_mock.html', 390, 844);
  r = await pg.evaluate(() => ({sw: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight}));
  console.log('phone index', r);
  await pg.screenshot({path: path.join(dir, 'shots/index_phone.png'), fullPage: true});
  await pg.close();
  await b.close();
})();
