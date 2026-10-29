// 전체 첫 화면(완성본/index.html)을 자동으로 검사한다.
//   node qa_index.js index.html [--out 보고서.md]
// 종료 코드: 0 = 고칠 문제 없음, 1 = 고칠 문제 있음, 2 = 사용법 오류
// 검사 폭은 qa_deck.js 와 같다(PC 1300·1000·820·710, 폰 390·360). 폭마다 회차 탭을 하나씩 눌러 보며 지도와 칸을 본다.
// 보는 것: 탭 구조와 순서(최근 회차가 왼쪽), 탭 누르기·화살표 키·주소 끝 #회차, 지도 45칸과 머리 줄 숫자, 눌리는 칸이 가리키는 수업 자료 파일과 문항,
//          PDF 파일, 칸과 글자의 넘침, 폰 가로 넘침. 눌리는 칸의 링크는 index.html 이 있는 폴더 기준으로 실제 파일을 열어 본다.
const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const fs = require('fs');
const path = require('path');
const skeleton = require('./skeleton');

const DESKTOP = [1300, 1000, 820, 710], PHONE = [390, 360];

// ---- 쪽 안에서 도는 검사 (문자열로 넘겨 실행한다) ----
// 폭과 상관없는 구조 검사. 맨 처음 상태(첫 탭이 열려 있음)에서 본다. 링크 목록과 패널 정보를 함께 돌려준다.
function inPageOnce() {
  const out = [], W = window.innerWidth;
  const add = (level, check, detail) => out.push({level, check, w: W, name: '', detail: detail || ''});
  if (document.compatMode !== 'CSS1Compat') add('error', '표준 모드가 아님', '문서 형식 선언이 없어 괴상 모드(' + document.compatMode + ')로 읽힘. 실제 화면과 배치가 다르다');
  if (!document.body.classList.contains('chalk')) add('error', '칠판 테마', 'body.chalk 가 붙지 않음');
  const loaded = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/"/g, ''));
  if (!loaded.some(f => /Noto Sans KR/.test(f))) add('error', '글꼴', 'Noto Sans KR 을 못 받음(인터넷 연결 확인). 이 검사 결과는 믿을 수 없음');

  const T = [...document.querySelectorAll('.tabs [role=tab]')], P = [...document.querySelectorAll('[role=tabpanel]')];
  if (!T.length) add('error', '탭 없음', '');
  if (T.length !== P.length) add('error', '탭 패널 수', T.length + '개 탭, ' + P.length + '개 패널');
  const ids = {};
  document.querySelectorAll('[id]').forEach(e => { ids[e.id] = (ids[e.id] || 0) + 1; });
  Object.keys(ids).filter(k => ids[k] > 1).forEach(k => add('error', 'id 중복', k + ' ×' + ids[k]));
  document.querySelectorAll('a[href^="#"]').forEach(a => { if (!document.getElementById(a.getAttribute('href').slice(1))) add('error', '안쪽 링크', a.getAttribute('href') + ' 가리키는 곳이 없음'); });

  const rids = T.map(t => t.dataset.r);
  if (rids.join() !== rids.slice().sort().reverse().join()) add('error', '탭 순서', '최근 회차가 왼쪽이어야 함(2026.09 가 맨 왼쪽): ' + rids.join(' '));
  T.forEach(t => {
    const p = document.getElementById(t.getAttribute('aria-controls') || '');
    if (!p) { add('error', '탭 연결', t.id + ' 의 aria-controls 가 가리키는 패널이 없음'); return; }
    if (p.getAttribute('aria-labelledby') !== t.id || p.dataset.r !== t.dataset.r) add('error', '탭 연결', t.id + ' 와 ' + p.id + ' 가 서로 맞지 않음');
    const badge = !!t.querySelector('.ok'), open = !!p.querySelector('a.btn'), on = p.querySelectorAll('a.mc.on').length;
    if (badge !== open || badge !== (on > 0)) add('error', '자료 있음 표시', t.dataset.r + ' 탭 배지 ' + badge + ', 열기 단추 ' + open + ', 눌리는 칸 ' + on + '개');
  });
  const sel = T.filter(t => t.getAttribute('aria-selected') === 'true');
  if (sel.length !== 1 || sel[0] !== T[0]) add('error', '처음 열린 탭', '맨 왼쪽 탭(가장 최근 회차)만 열려 있어야 함');
  T.forEach(t => { if (t.tabIndex !== (t === T[0] ? 0 : -1)) add('error', '탭 키 이동', t.dataset.r + ' 의 tabindex ' + t.tabIndex); });
  const vis = P.filter(p => !p.hidden && getComputedStyle(p).display !== 'none');
  if (vis.length !== 1 || !sel.length || vis[0].dataset.r !== sel[0].dataset.r) add('error', '탭 패널', '열린 탭의 패널 하나만 보여야 함: ' + vis.map(p => p.dataset.r).join(','));

  // 글자 크기: PC 기준 폭에서만(장이 폭에 비례해 줄어드는 폭에서는 보지 않는다. qa_deck.js 와 같은 기준)
  if (W >= 1300) {
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), seen = {};
    let n;
    while ((n = tw.nextNode())) {
      const e = n.parentElement;
      if (!n.textContent.trim() || e.closest('script,style,[hidden]')) continue;
      const fs = parseFloat(getComputedStyle(e).fontSize), k = (typeof e.className === 'string' && e.className) || e.tagName.toLowerCase();
      if (fs < 10.5 && !seen[k]) { seen[k] = 1; add('error', '글자가 너무 작음', k + ' ' + fs.toFixed(1) + 'px'); }
    }
  }
  return {
    findings: out,
    hrefs: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')),
    panels: P.map(p => {
      const open = p.querySelector('a.btn:not([download])'), pdf = p.querySelector('a.btn[download]');
      return {rid: p.dataset.r, open: open ? open.getAttribute('href') : '', pdf: pdf ? pdf.getAttribute('href') : '',
              on: [...p.querySelectorAll('a.mc.on')].map(a => a.getAttribute('href'))};
    }),
  };
}

// 탭 하나를 눌러 연 상태에서 보는 검사: 지금 보이는 패널의 지도와 칸, 넘침
function inPageTab(opts) {
  const out = [], W = window.innerWidth, wide = W > 700, rid = opts.rid;
  const add = (level, check, detail) => out.push({level, check, w: W, name: rid, detail: detail || ''});
  const tab = document.querySelector('.tabs [role=tab][data-r="' + rid + '"]');
  const vis = [...document.querySelectorAll('[role=tabpanel]')].filter(p => !p.hidden && getComputedStyle(p).display !== 'none');
  if (!tab || tab.getAttribute('aria-selected') !== 'true') add('error', '탭 선택 표시', rid + ' 탭을 눌렀는데 선택 표시(aria-selected)가 안 바뀜');
  if (vis.length !== 1 || vis[0].dataset.r !== rid) { add('error', '탭 패널', rid + ' 를 눌렀는데 보이는 패널: ' + vis.map(p => p.dataset.r).join(',')); return out; }
  if (location.hash !== '#' + rid) add('warn', '주소 끝 표시', rid + ' 를 눌렀는데 주소 끝이 ' + location.hash);
  const p = vis[0], m = p.querySelector('.mapslide');
  const de = document.documentElement;
  if (de.scrollWidth > de.clientWidth + 1) add('error', '가로 넘침', 'scrollWidth ' + de.scrollWidth + ' > ' + de.clientWidth);
  let nOver = 0;
  document.body.querySelectorAll('*').forEach(e => {
    if (e.closest('[hidden],script,style')) return;
    const r = e.getBoundingClientRect();
    if (r.width && r.right > W + 0.5 && nOver++ < 5) add('error', '오른쪽 밖으로 나감', ((typeof e.className === 'string' && e.className) || e.tagName.toLowerCase()) + ' 오른쪽 ' + r.right.toFixed(1));
  });
  document.querySelectorAll('.tabs button').forEach(b => { if (b.scrollWidth > b.clientWidth + 1) add('error', '탭 글자 넘침', b.textContent); });
  const ch = p.querySelector('.chips'), ac = p.querySelector('.acts');
  if (ch && ac) {
    const a = ch.getBoundingClientRect(), b = ac.getBoundingClientRect();
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) add('error', '칩과 단추 겹침', '');
  }
  if (!m) { add('error', '지도 없음', ''); return out; }

  // 지도: 칸 수, 머리 줄 숫자, 띠 숫자, 위 칩과 같은지
  const cells = [...m.querySelectorAll('.mc')];
  if (cells.length !== 45) add('error', '지도 칸 수', cells.length + '칸 (45칸이어야 함)');
  const lk = cells.filter(c => c.classList.contains('lk')), none = cells.filter(c => c.classList.contains('none')), on = m.querySelectorAll('a.mc.on');
  if (lk.length + none.length !== cells.length) add('error', '지도 칸 종류', '연계 ' + lk.length + ' + 독립 ' + none.length + ' ≠ ' + cells.length);
  const nums = [...m.querySelectorAll('.mh .ms b')].map(b => +b.textContent);
  if (nums[0] !== lk.length || nums[1] !== none.length) add('error', '지도 숫자', '머리 줄 ' + nums.slice(0, 2).join('/') + ', 칸 ' + lk.length + '/' + none.length);
  const rd = m.querySelector('.mh .ms .rd b');
  if ((rd ? +rd.textContent : 0) !== on.length) add('error', '지도 숫자', '수업 자료 ' + (rd ? rd.textContent : 0) + ' ≠ 눌리는 칸 ' + on.length);
  const bandSum = [...m.querySelectorAll('.band h3 .n')].reduce((s, e) => s + (+(e.textContent.match(/\d+/) || [0])[0]), 0);
  if (bandSum !== lk.length) add('error', '지도 숫자', '듣기·읽기 띠 ' + bandSum + ' ≠ 연계 칸 ' + lk.length);
  const chip = (p.querySelector('.chips') || {textContent: ''}).textContent;
  const cn = +((chip.match(/교재 연계\s*(\d+)/) || [])[1]), cf = parseFloat((chip.match(/체감 평균\s*([\d.]+)/) || [])[1]);
  if (cn !== lk.length) add('error', '칩 숫자', '교재 연계 칩 ' + cn + ' ≠ 연계 칸 ' + lk.length);
  const felts = lk.map(c => +((c.querySelector('.cells') || {getAttribute: () => ''}).getAttribute('aria-label').match(/중 (\d)점/) || [])[1]).filter(x => x > 0);
  const mean = felts.length ? felts.reduce((a, b) => a + b, 0) / felts.length : NaN;
  if (felts.length && !(Math.abs(cf - mean) <= 0.051)) add('error', '칩 숫자', '체감 평균 칩 ' + cf + ' ≠ 칸의 평균 ' + mean.toFixed(2));
  if (!felts.length && !isNaN(cf)) add('error', '칩 숫자', '체감이 있는 칸이 없는데 체감 평균 칩이 있음');
  if (felts.length !== lk.length) add('error', '체감 칸', '체감 점수가 없는 연계 칸 ' + (lk.length - felts.length) + '개');
  const btnOn = p.querySelector('a.btn'), btnOff = p.querySelector('.btn.off');
  if ((on.length > 0) !== !!btnOn) add('error', '단추', '눌리는 칸 ' + on.length + '개인데 수업 자료 열기 단추 ' + (btnOn ? '있음' : '없음'));
  if (!btnOn && !btnOff) add('error', '단추', '수업 자료 단추도 준비 중 표시도 없음');
  if (on.length && [...on].some(a => a.getAttribute('href').split('#')[0] !== btnOn.getAttribute('href'))) add('error', '단추', '열기 단추와 지도 칸이 서로 다른 파일을 가리킴');
  const pdf = p.querySelector('a.btn[download]');
  if (pdf && !/\.pdf$/i.test(pdf.getAttribute('href'))) add('error', '단추', 'PDF 단추가 PDF 파일을 가리키지 않음: ' + pdf.getAttribute('href'));

  if (wide) {
    const sr = m.getBoundingClientRect();
    if (Math.abs(sr.height - sr.width * 9 / 16) > 2) add('error', '16:9 비율', Math.round(sr.height) + ' / ' + Math.round(sr.width * 9 / 16));
    if (m.scrollHeight > m.clientHeight + 2) add('error', '칸 안 넘침', 'mapslide ' + m.scrollHeight + '>' + m.clientHeight);
    m.querySelectorAll('.mc').forEach(e => { if (e.scrollWidth > e.clientWidth + 1) add('error', '지도 칸 글자 넘침', e.textContent.slice(0, 16)); });
    m.querySelectorAll('.mf,.mh,.band').forEach(e => { if (e.getBoundingClientRect().bottom > sr.bottom + 1) add('error', '장 밖으로 나감', e.className); });
  } else {
    m.querySelectorAll('.mc,.mf .k').forEach(e => { if (e.scrollWidth > e.clientWidth + 1) add('error', '지도 칸 글자 넘침', e.textContent.slice(0, 16)); });
    const tw = document.createTreeWalker(p, NodeFilter.SHOW_TEXT), small = {};
    let n;
    while ((n = tw.nextNode())) {
      const e = n.parentElement;
      if (!n.textContent.trim() || e.closest('script,style')) continue;
      const fs = parseFloat(getComputedStyle(e).fontSize), k = (typeof e.className === 'string' && e.className) || e.tagName.toLowerCase();
      if (fs < 11) { small[k] = small[k] || {n: 0, min: 99}; small[k].n++; small[k].min = Math.min(small[k].min, fs); }
    }
    Object.keys(small).forEach(k => add('error', '폰에서 글자가 11px 미만', k + ' ' + small[k].min.toFixed(1) + 'px ×' + small[k].n));
  }
  return out;
}

// ---- 파일 검사(쪽 밖): 링크가 가리키는 파일과 문항이 실제로 있는지 ----
// data = inPageOnce() 가 돌려준 {hrefs, panels}. 링크는 index.html 이 있는 폴더 기준.
function checkLinks(file, data) {
  const out = [], dir = path.dirname(path.resolve(file)), cache = {};
  const add = (check, detail, name) => out.push({level: 'error', check, w: 0, name: name || '', detail});
  const read = f => (cache[f] = cache[f] || fs.readFileSync(f, 'utf8'));
  const target = h => { try { return path.join(dir, decodeURIComponent(h.split('#')[0])); } catch (e) { return null; } };
  const seen = new Set();
  data.hrefs.forEach(h => {
    if (h.charAt(0) === '#' || /^[a-z][a-z0-9+.-]*:/i.test(h) || seen.has(h)) return;
    seen.add(h);
    const f = target(h), frag = h.split('#')[1];
    if (!f || !fs.existsSync(f)) { add('링크 파일 없음', h); return; }
    if (/\.html?$/i.test(f) && frag && !new RegExp('\\sid="' + frag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '"').test(read(f))) add('링크 안 id 없음', h);
    if (/\.pdf$/i.test(f) && fs.readFileSync(f).subarray(0, 5).toString() !== '%PDF-') add('PDF 파일 이상', h);
  });
  data.panels.forEach(p => {
    if (!p.on.length) return;
    const f = target(p.on[0]);
    if (!f || !fs.existsSync(f)) return;                       // 위에서 이미 알림
    const have = [...read(f).matchAll(/<section class="slide" id="(q\d+)"/g)].map(m => m[1]);
    const linked = p.on.map(h => h.split('#')[1]);
    have.filter(i => !linked.includes(i)).forEach(i => add('지도에 없는 문항', path.basename(f) + ' 의 ' + i + ' 를 여는 칸이 이 회차 지도에 없음', p.rid));
  });
  return out;
}

// ---- 탭 동작(키보드와 주소): 폭 1300 에서 한 번 ----
async function interact(browser, file, findings) {
  const pg = await browser.newPage({viewport: {width: 1300, height: 900}});
  pg.on('pageerror', e => findings.push({level: 'error', check: '페이지 스크립트 오류', w: 1300, name: '', detail: e.message}));
  await pg.goto('file://' + file);
  await pg.evaluate(() => document.fonts.ready);
  const rids = await pg.$$eval('.tabs [role=tab]', els => els.map(e => e.dataset.r));
  const state = () => pg.evaluate(() => {
    const T = [...document.querySelectorAll('.tabs [role=tab]')];
    return {sel: T.filter(t => t.getAttribute('aria-selected') === 'true').map(t => t.dataset.r).join(), vis: [...document.querySelectorAll('[role=tabpanel]')].filter(p => !p.hidden).map(p => p.dataset.r).join(),
            focus: document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.r : '', hash: location.hash, tabbable: T.filter(t => t.tabIndex === 0).map(t => t.dataset.r).join()};
  });
  const bad = (what, s) => findings.push({level: 'error', check: '탭 동작', w: 1300, name: '', detail: what + ' ' + JSON.stringify(s)});
  const at = (s, r, focus) => s.sel === r && s.vis === r && s.tabbable === r && s.hash === '#' + r && (!focus || s.focus === r);
  if (rids.length < 3) { bad('탭이 3개 미만이라 동작을 볼 수 없음', rids); await pg.close(); return; }
  await pg.click('.tabs [role=tab][data-r="' + rids[2] + '"]');
  let s = await state(); if (!at(s, rids[2])) bad('세 번째 탭을 누르면 그 회차만 열리고 주소 끝이 바뀌어야 함', s);
  await pg.keyboard.press('ArrowRight'); s = await state(); if (!at(s, rids[3], true)) bad('→ 키는 다음 탭을 열고 포커스도 옮겨야 함', s);
  await pg.keyboard.press('ArrowLeft'); await pg.keyboard.press('ArrowLeft'); s = await state(); if (!at(s, rids[1], true)) bad('← 키는 이전 탭', s);
  await pg.keyboard.press('Home'); s = await state(); if (!at(s, rids[0], true)) bad('Home 은 맨 왼쪽 탭', s);
  await pg.keyboard.press('ArrowLeft'); s = await state(); if (!at(s, rids[rids.length - 1], true)) bad('맨 왼쪽에서 ← 는 맨 오른쪽 탭으로 돌아감', s);
  await pg.keyboard.press('ArrowRight'); s = await state(); if (!at(s, rids[0], true)) bad('맨 오른쪽에서 → 는 맨 왼쪽 탭으로 돌아감', s);
  await pg.keyboard.press('End'); s = await state(); if (!at(s, rids[rids.length - 1], true)) bad('End 는 맨 오른쪽 탭', s);
  await pg.close();
  for (const [hash, want, what] of [[rids[4 % rids.length], rids[4 % rids.length], '주소 끝 #회차 로 열면 그 회차가 열려야 함'], ['없는회차', rids[0], '없는 회차 이름이면 맨 왼쪽 탭이 그대로 열려 있어야 함']]) {
    const p2 = await browser.newPage({viewport: {width: 1300, height: 900}});
    await p2.goto('file://' + file + '#' + encodeURIComponent(hash).replace(/%2E/g, '.'));
    const s2 = await p2.evaluate(() => ({sel: [...document.querySelectorAll('.tabs [role=tab]')].filter(t => t.getAttribute('aria-selected') === 'true').map(t => t.dataset.r).join(),
      vis: [...document.querySelectorAll('[role=tabpanel]')].filter(p => !p.hidden).map(p => p.dataset.r).join()}));
    if (s2.sel !== want || s2.vis !== want) bad(what, s2);
    await p2.close();
  }
}

async function main() {
  const args = process.argv.slice(2);
  const oi = args.indexOf('--out');
  const outPath = oi >= 0 ? args[oi + 1] : null;
  const file = args.find((a, i) => !a.startsWith('--') && (oi < 0 || i !== oi + 1));
  if (!file) { console.log('사용: node qa_index.js index.html [--out 보고서.md]'); process.exit(2); }
  const abs = path.resolve(file);
  const prep = skeleton.prepared(abs);          // 조각이면 틀을 씌워 임시 파일로 연다. 링크는 원래 파일이 있는 폴더 기준으로 본다
  const browser = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  const findings = [];
  let tabCount = 0;
  for (const w of DESKTOP.concat(PHONE)) {
    const pg = await browser.newPage({viewport: {width: w, height: 800}});
    pg.on('pageerror', e => findings.push({level: 'error', check: '페이지 스크립트 오류', w, name: '', detail: e.message}));
    await pg.goto('file://' + prep.file);
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(800);
    const once = await pg.evaluate(`(${inPageOnce.toString()})()`);
    findings.push(...once.findings);
    if (w === DESKTOP[0]) findings.push(...checkLinks(abs, once));
    const rids = await pg.$$eval('.tabs [role=tab]', els => els.map(e => e.dataset.r));
    tabCount = rids.length;
    for (const rid of rids) {
      await pg.click('.tabs [role=tab][data-r="' + rid + '"]');
      await pg.waitForTimeout(120);
      findings.push(...await pg.evaluate(`(${inPageTab.toString()})(${JSON.stringify({rid})})`));
    }
    await pg.close();
  }
  if (tabCount) await interact(browser, prep.file, findings);
  await browser.close();
  prep.done();

  const key = f => [f.level, f.check, f.name, f.detail].join('|');
  const merged = new Map();
  findings.forEach(f => {
    const k = key(f);
    if (!merged.has(k)) merged.set(k, Object.assign({}, f, {widths: [f.w]}));
    else if (!merged.get(k).widths.includes(f.w)) merged.get(k).widths.push(f.w);
  });
  const rows = [...merged.values()];
  const order = {error: 0, warn: 1, info: 2};
  rows.sort((a, b) => order[a.level] - order[b.level] || a.check.localeCompare(b.check) || a.name.localeCompare(b.name));
  const cnt = l => rows.filter(f => f.level === l).length;
  const label = {error: '오류', warn: '주의', info: '참고'};
  const lines = ['# 자동 검사 결과: ' + path.basename(file), '',
    '- 검사한 파일: `' + path.basename(file) + '` (회차 탭 ' + tabCount + '개)',
    '- 검사 폭: PC ' + DESKTOP.join('·') + 'px, 폰 ' + PHONE.join('·') + 'px. 폭마다 탭을 하나씩 눌러 지도와 칸을 봄, 폭 1300 에서는 링크가 가리키는 파일과 문항, 탭 누르기·화살표 키·주소 끝 #회차 동작도 봄',
    '- 결과: 오류 ' + cnt('error') + '건, 주의 ' + cnt('warn') + '건, 참고 ' + cnt('info') + '건', ''];
  if (rows.length) {
    lines.push('| 단계 | 검사 | 어디 | 내용 | 폭 |', '|---|---|---|---|---|');
    rows.forEach(f => lines.push('| ' + label[f.level] + ' | ' + f.check + ' | ' + (f.name || '문서 전체') + ' | ' + (f.detail || '').replace(/\|/g, '\\|') + ' | ' + (f.widths.filter(x => x).join('·') || '-') + ' |'));
  } else {
    lines.push('문제가 없습니다.');
  }
  const text = lines.join('\n') + '\n';
  if (outPath) fs.writeFileSync(outPath, text, 'utf8');
  console.log(text);
  process.exit(cnt('error') ? 1 : 0);
}

module.exports = {inPageOnce, inPageTab, checkLinks, interact};
if (require.main === module) main();
