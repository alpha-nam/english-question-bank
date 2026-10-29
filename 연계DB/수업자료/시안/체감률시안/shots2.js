const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const path = require('path');
const fs = require('fs');
const dir = __dirname;
fs.mkdirSync(path.join(dir, 'shots2'), {recursive: true});
const STYLES = ['sq', 'pct', 'bar'];
(async () => {
  const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  async function open(style, w, h) {
    const pg = await b.newPage({viewport: {width: w, height: h || 900}});
    await pg.goto('file://' + path.join(dir, 'v_' + style + '.html'));
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(2200);
    await pg.addStyleTag({content: 'nav{position:static!important}'});
    return pg;
  }
  const report = {};
  for (const st of STYLES) {
    // PC 1300: 지도 전체, 듣기 띠, 비교 장 머리글 3개
    let pg = await open(st, 1300);
    const map = await pg.$('#map');
    await map.screenshot({path: path.join(dir, `shots2/map_${st}.png`)});
    const band = await pg.$('#map .band');
    await band.screenshot({path: path.join(dir, `shots2/band_${st}.png`)});
    const hds = await pg.$$('.slide:has(.fl) .hd');
    for (let i = 0; i < hds.length; i++) await hds[i].screenshot({path: path.join(dir, `shots2/hd_${st}_${i}.png`)});
    const mm = await pg.evaluate(() => { const m = document.querySelector('#map'); const bb = m.getBoundingClientRect(); return {w: Math.round(bb.width), h: Math.round(bb.height), over: m.scrollHeight - m.clientHeight}; });
    report[st + ' map1300'] = mm;
    await pg.close();
    // 폭마다: 지도 16:9, 머리글 여유
    for (const w of [1500, 1000, 820, 710]) {
      pg = await open(st, w);
      const r = await pg.evaluate(() => {
        const m = document.querySelector('#map'); const bb = m.getBoundingClientRect();
        const mf = m.querySelector('.mf').getBoundingClientRect(); const last = m.querySelector('.band:nth-last-child(2) .mg').getBoundingClientRect();
        const hs = [...document.querySelectorAll('.slide .hd')].map(h => { const k = h.querySelector('.kd'); const last = [...h.children].filter(c => c !== k).pop();
          const gap = parseFloat(getComputedStyle(h).columnGap) || 0; return Math.round(k.getBoundingClientRect().left - last.getBoundingClientRect().right - gap); });
        const hh = [...new Set([...document.querySelectorAll('.slide .hd')].map(h => Math.round(h.getBoundingClientRect().height)))];
        return {mapW: Math.round(bb.width), mapH: Math.round(bb.height), over: m.scrollHeight - m.clientHeight, legendGap: Math.round(mf.top - last.bottom), minSlack: Math.min(...hs), hdHeights: hh.join('/')};
      });
      report[st + ' w' + w] = r;
      await pg.close();
    }
    // 폰 390: 지도, 비교 장 머리글
    pg = await open(st, 390, 844);
    const pm = await pg.$('#map');
    await pm.screenshot({path: path.join(dir, `shots2/map_phone_${st}.png`)});
    const phd = await pg.$$('.slide:has(.fl) .hd');
    await phd[2].screenshot({path: path.join(dir, `shots2/hd_phone_${st}.png`)});
    report[st + ' phone'] = await pg.evaluate(() => ({sw: document.documentElement.scrollWidth}));
    await pg.close();
  }
  console.log(JSON.stringify(report, null, 1));
  await b.close();
})();
