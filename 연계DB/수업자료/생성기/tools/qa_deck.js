// 수업용 HTML 한 파일을 자동으로 검사한다.
//   node qa_deck.js 파일.html [--out 보고서.md]
// 종료 코드: 0 = 고칠 문제 없음(참고 사항은 있을 수 있음), 1 = 고칠 문제 있음, 2 = 사용법 오류
// 검사 폭: PC 4가지(1300·1000·820·710)와 폰 2가지(390·360). 글꼴은 구글에서 실제로 내려받아 사용자 화면과 같게 잰다.
// 단계: 오류(error) = 반드시 고침, 주의(warn) = 눈으로 확인, 참고(info) = 알려진 사항
// 덱은 Artifact 가 틀(문서 형식 선언 등)을 씌워 표준 모드로 보여 주므로, 여기서도 skeleton.js 로 같은 틀을 씌워 읽는다(안 그러면 괴상 모드로 읽혀 배치가 다르다).
const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const fs = require('fs');
const path = require('path');
const skeleton = require('./skeleton');

const DESKTOP = [1300, 1000, 820, 710], PHONE = [390, 360];

// ---- 쪽 안에서 도는 검사 (문자열로 넘겨 실행한다) ----
function inPage(opts) {
  const out = [];
  const S = [...document.querySelectorAll('.slide')];
  const isMap = s => s.classList.contains('mapslide');     // 연계 지도 장: 문항 5장 묶음에 속하지 않는다
  const QS = S.filter(s => !isMap(s));
  const W = window.innerWidth, wide = W > 700;
  if (document.compatMode !== 'CSS1Compat') out.push({level: 'error', check: '표준 모드가 아님', w: W, slide: -1, name: '', detail: '문서 형식 선언이 없어 괴상 모드(' + document.compatMode + ')로 읽힘. 실제 화면과 배치가 다르다'});
  const nameOf = (s, i) => {
    if (isMap(s)) return '연계 지도';
    const a = (s.querySelector('.hd') && s.querySelector('.hd').getAttribute('aria-label')) || '';
    const m = a.match(/시험 (\d+)번.* — (.*)$/);
    return m ? m[1] + '번 ' + m[2] : '장 ' + (i + 1);
  };
  const add = (level, check, i, detail) => out.push({level, check, w: W, slide: i, name: i >= 0 ? nameOf(S[i], i) : '', detail: detail || ''});
  const idxOf = e => { const s = e.closest('.slide'); return s ? S.indexOf(s) : -1; };
  const cls = e => (typeof e.className === 'string' ? e.className : '') || e.tagName.toLowerCase();

  // 한 문장 안의 어절을 줄별로 나눠, 줄바꿈 뒤 마지막 줄에 한 어절만 남았는지 본다 (<br> 로 나뉜 덩어리마다)
  function orphan(el, skip) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_ALL, {acceptNode: n => {
      if (n.nodeType === 3) return (skip && skip(n)) || n.parentElement.closest('svg,script,style') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      return n.tagName === 'BR' ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
    }});
    let full = '', map = [], n;
    while ((n = walker.nextNode())) {
      if (n.nodeType === 1) { full += '\n'; map.push(null); continue; }
      const t = n.textContent;
      for (let k = 0; k < t.length; k++) { full += t[k]; map.push([n, k]); }
    }
    const segs = [[]];
    const re = /\S+/g;
    let m, lastEnd = 0;
    while ((m = re.exec(full))) {
      if (full.slice(lastEnd, m.index).indexOf('\n') >= 0) segs.push([]);
      lastEnd = m.index + m[0].length;
      const a = map[m.index], b = map[m.index + m[0].length - 1];
      if (!a || !b) continue;
      const r = document.createRange(); r.setStart(a[0], a[1]); r.setEnd(b[0], b[1] + 1);
      const rects = [...r.getClientRects()].filter(x => x.width > 0 && x.height > 0);
      if (rects.length) segs[segs.length - 1].push({t: m[0], first: rects[0], last: rects[rects.length - 1]});
    }
    const bad = [];
    segs.forEach(tokens => {
      if (tokens.length < 2) return;
      const cy = r => r.top + r.height / 2;
      const lineH = Math.min(...tokens.map(x => x.last.height));
      const lines = [];            // 줄마다 그 줄에서 시작하는 어절
      tokens.slice().sort((a, b) => cy(a.first) - cy(b.first)).forEach(tk => {
        const l = lines.find(L => Math.abs(L.y - cy(tk.first)) < lineH * 0.6);
        if (l) l.tk.push(tk); else lines.push({y: cy(tk.first), tk: [tk]});
      });
      if (lines.length < 2) return;
      const lastL = lines[lines.length - 1];
      if (lastL.tk.length === 1 && Math.abs(cy(lastL.tk[0].last) - lastL.y) < lineH * 0.6) bad.push(lastL.tk[0].t);
    });
    return bad;
  }

  add('info', 'meta', -1, '장 ' + S.length + '개, 쪽 폭 ' + W + 'px');
  if (!document.body.classList.contains('chalk')) add('error', '칠판 테마', -1, 'body.chalk 가 붙지 않음');
  if (S.length === 0) add('error', '장 없음', -1);

  // 글꼴 도착 확인: 못 받았으면 모든 측정이 어긋나므로 오류
  const loaded = [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/"/g, ''));
  if (!loaded.some(f => /Noto Sans KR/.test(f))) add('error', '글꼴', -1, 'Noto Sans KR 을 못 받음(인터넷 연결 확인). 이 검사 결과는 믿을 수 없음');
  if (!loaded.some(f => /Source Serif/.test(f))) add('error', '글꼴', -1, 'Source Serif 4 를 못 받음(인터넷 연결 확인). 이 검사 결과는 믿을 수 없음');

  // 문서 전체
  if (opts.once) {
    const ids = {};
    document.querySelectorAll('[id]').forEach(e => { ids[e.id] = (ids[e.id] || 0) + 1; });
    Object.keys(ids).filter(k => ids[k] > 1).forEach(k => add('error', 'id 중복', -1, k + ' ×' + ids[k]));
    document.querySelectorAll('nav a[href^="#"]').forEach(a => { if (!document.getElementById(a.getAttribute('href').slice(1))) add('error', '목차 링크', -1, a.getAttribute('href') + ' 가리키는 곳이 없음'); });
    if (QS.length % 5) add('error', '장 수', -1, '5의 배수가 아님' + (QS.length === S.length ? '' : '(연계 지도 장 제외)') + ': ' + QS.length);
    document.querySelectorAll('svg[id]').forEach(sv => { if (sv.id && sv.getAttribute('viewBox') && sv.children.length === 0) add('error', '도표', idxOf(sv), sv.id + ' 가 그려지지 않음'); });
    QS.forEach(s => {
      const i = S.indexOf(s), k = QS.indexOf(s) % 5;
      if (k < 2) { const a = s.querySelector('.foot .ans'); if (!a || !/정답/.test(a.textContent)) add('error', '정답 표시', i, '시험·교재 원문항 장에 정답 줄이 없음'); }
      if (!s.querySelector('.hd .kd .ty')) add('error', '헤더', i, '문항 유형 칸 없음');
    });
    // 연계 지도 장: 45칸, 눌리는 칸의 링크, 칸 수 글, 이 파일의 문항과 맞는지
    S.filter(isMap).forEach(s => {
      const i = S.indexOf(s), cells = [...s.querySelectorAll('.mc')];
      if (cells.length !== 45) add('error', '지도 칸 수', i, cells.length + '칸 (45칸이어야 함)');
      const lk = cells.filter(c => c.classList.contains('lk')).length, none = cells.filter(c => c.classList.contains('none')).length;
      const nums = [...s.querySelectorAll('.mh .ms b')].map(b => +b.textContent);
      if (nums[0] !== lk || nums[1] !== none) add('error', '지도 숫자', i, '머리 줄 ' + nums.slice(0, 2).join('/') + ', 칸 ' + lk + '/' + none);
      const on = [...s.querySelectorAll('a.mc.on')];
      on.forEach(a => {
        const h = a.getAttribute('href') || '';
        if (h.charAt(0) === '#' && !document.getElementById(h.slice(1))) add('error', '지도 링크', i, h + ' 가리키는 곳이 없음');
      });
      QS.forEach(q => { if (q.id && /^q\d+$/.test(q.id) && !on.some(a => a.getAttribute('href') === '#' + q.id)) add('error', '지도에 없는 문항', S.indexOf(q), q.id + ' 를 여는 칸이 지도에 없음'); });
      const rd = s.querySelector('.mh .ms .rd b'), nrd = rd ? +rd.textContent : 0;
      if (nrd !== on.length) add('error', '지도 숫자', i, '수업 자료 ' + nrd + ' ≠ 눌리는 칸 ' + on.length);
    });
  }

  // 목차 줄이 이동한 장의 위쪽을 가리는지: 장 위 여백(scroll-margin-top)이 목차 줄 높이보다 작으면 폰에서 장 머리가 가려진다.
  // 연계 지도를 넣은 파일은 이 문제를 고친 틀(nav.js)을 쓰므로 오류, 지도 없는 옛 틀은 주의로 알린다.
  const nv = document.querySelector('nav');
  if (nv && S.length && getComputedStyle(nv).position === 'sticky') {
    const nh = nv.getBoundingClientRect().height, sm = parseFloat(getComputedStyle(S[0]).scrollMarginTop) || 0;
    if (sm < nh) add(S.some(isMap) ? 'error' : 'warn', '목차 줄이 이동한 장 위를 가림', -1, '목차 줄 ' + Math.round(nh) + 'px > 장 위 여백 ' + Math.round(sm) + 'px');
  }

  if (wide) {
    S.forEach((s, i) => {
      const sr = s.getBoundingClientRect();
      if (Math.abs(sr.height - sr.width * 9 / 16) > 2) add('error', '16:9 비율', i, Math.round(sr.height) + ' / ' + Math.round(sr.width * 9 / 16));
      s.querySelectorAll('.two,.col,.q,.twofig,.rows,.diff,.passage').forEach(e => { if (e.scrollHeight > e.clientHeight + 2) add('error', '칸 안 넘침', i, cls(e) + ' ' + e.scrollHeight + '>' + e.clientHeight); });
      s.querySelectorAll('.diff,.col,.foot,.ch,.rows,.sum,.sd,.mf').forEach(e => { if (e.getBoundingClientRect().bottom > sr.bottom + 1) add('error', '장 밖으로 나감', i, cls(e)); });
      s.querySelectorAll('.mc').forEach(e => { if (e.scrollWidth > e.clientWidth + 1) add('error', '지도 칸 글자 넘침', i, e.textContent.slice(0, 16)); });
      const f = s.querySelector('.foot');
      if (f) {
        const fr = f.getBoundingClientRect();
        let mb = 0;
        s.querySelectorAll('.q p,.q li,.q svg,.q div').forEach(e => { const r = e.getBoundingClientRect(); if ((r.height && e.children.length === 0) || e.tagName === 'svg') mb = Math.max(mb, r.bottom); });
        if (mb > fr.top + 2) add('error', '정답 줄과 겹침', i, Math.round(mb - fr.top) + 'px');
      }
      const d = s.querySelector('.diff'), t = s.querySelector('.two,.twofig');
      if (d && t && t.getBoundingClientRect().bottom > d.getBoundingClientRect().top + 1) add('error', '위아래 상자 겹침', i);
      s.querySelectorAll('.cl').forEach(c => { const lh = parseFloat(getComputedStyle(c).lineHeight) || 20; if (c.getBoundingClientRect().height > lh * 1.6) add('error', '뜻 덩어리가 줄바꿈됨', i, c.textContent.slice(0, 24)); });
      s.querySelectorAll('.row,.diff div,.sd div').forEach(e => { if (e.scrollWidth > e.clientWidth + 2) add('error', '가로 넘침', i, cls(e)); });
      // 헤더: 오른쪽 칸이 왼쪽 칸에 닿거나 넘치면 오류, 여유가 6px 미만이면 주의
      const h = s.querySelector('.hd'), kd = h && h.querySelector('.kd');
      if (h && kd) {
        const last = [...h.children].filter(c => c !== kd).pop();
        const gap = parseFloat(getComputedStyle(h).columnGap) || 0;
        const slack = Math.round(kd.getBoundingClientRect().left - last.getBoundingClientRect().right - gap);
        if (h.scrollWidth > h.clientWidth + 1 || slack < 0) add('error', '헤더 폭', i, '여유 ' + slack + 'px');    // scrollWidth·clientWidth 는 정수로 반올림되므로 1px 까지는 오차
        else if (slack < 6) add('warn', '헤더 폭 여유 적음', i, slack + 'px');
      }
      // 자동 맞춤 결과: 글자가 10% 넘게 줄었으면 주의
      const q = s.querySelector('.q:not(.twofig)'), rows = s.querySelector('.rows');
      if (q && q.children[0]) { const z = parseFloat(q.children[0].style.zoom || 1); if (z < 0.9) add('warn', '본문 글자 줄어듦', i, Math.round(z * 100) + '%'); }
      if (rows) { const rs = parseFloat(rows.style.getPropertyValue('--rs') || 1); if (rs < 0.85) add('warn', '분석 글자 줄어듦', i, Math.round(rs * 100) + '%'); }
      // 설명 글의 마지막 줄에 한 어절만 남는지 (뜻 덩어리 표시 |, 문장 다듬기로 고친다)
      const lvl = opts.orphanLevel;
      s.querySelectorAll('.diff > div, .row li, .sum, .sd div span, .ecard p').forEach(e => {
        const skip = n => !!n.parentElement.closest('.diff > div > b, .sd b');
        orphan(e, skip).forEach(w => add(lvl, '마지막 줄 한 어절', i, '“' + w + '” (' + cls(e).split(' ')[0] + ')'));
      });
      // 너무 작은 글자: 장이 폭에 비례해 줄어드는 PC 폭에서는 기준 폭(1300)에서만 본다
      const tw = document.createTreeWalker(s, NodeFilter.SHOW_TEXT);
      let n;
      const seen = {};
      while (opts.once && (n = tw.nextNode())) {
        const e = n.parentElement;
        if (!n.textContent.trim() || e.closest('svg,script,style')) continue;
        const fs = parseFloat(getComputedStyle(e).fontSize);
        if (fs < 10.5 && !seen[cls(e)]) { seen[cls(e)] = 1; add('error', '글자가 너무 작음', i, cls(e) + ' ' + fs.toFixed(1) + 'px'); }
      }
    });
  } else {
    const de = document.documentElement;
    if (de.scrollWidth > de.clientWidth) add('error', '폰 가로 넘침', -1, 'scrollWidth ' + de.scrollWidth + ' > ' + de.clientWidth);
    let nOver = 0;
    document.querySelectorAll('body *').forEach(e => {
      const r = e.getBoundingClientRect();
      if (r.width && r.right > W + 0.5) { if (nOver++ < 5) add('error', '폰에서 오른쪽 밖으로 나감', idxOf(e), cls(e) + ' 오른쪽 ' + r.right.toFixed(1)); }
    });
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    const smallHtml = {}, smallSvg = {};
    const scale = e => { const sv = e.closest('svg'), vb = sv && sv.viewBox && sv.viewBox.baseVal; return vb && vb.width ? sv.getBoundingClientRect().width / vb.width : 1; };
    while ((n = tw.nextNode())) {
      const e = n.parentElement;
      if (!n.textContent.trim() || e.closest('script,style')) continue;
      const svg = !!e.closest('svg');
      const fs = parseFloat(getComputedStyle(e).fontSize) * scale(e);
      if (fs >= 11) continue;
      const bag = svg ? smallSvg : smallHtml, k = svg ? 'svg' : cls(e);
      const i = idxOf(e);
      bag[k] = bag[k] || {n: 0, min: 99, slides: new Set()};
      bag[k].n++; bag[k].min = Math.min(bag[k].min, fs); bag[k].slides.add(i);
    }
    Object.keys(smallHtml).forEach(k => add('error', '폰에서 글자가 11px 미만', -1, k + ' ' + smallHtml[k].min.toFixed(1) + 'px ×' + smallHtml[k].n));
    if (smallSvg.svg) add('info', '폰 도표 안 글자 작음(알려진 보류 항목)', -1, '최소 ' + smallSvg.svg.min.toFixed(1) + 'px, ' + smallSvg.svg.n + '곳');
    // 폰에서 설명 글 마지막 줄 한 어절: 참고만
    let no = 0;
    S.forEach((s, i) => s.querySelectorAll('.diff > div, .row li, .sum, .sd div span, .ecard p').forEach(e => {
      const skip = nn => !!nn.parentElement.closest('.diff > div > b, .sd b');
      no += orphan(e, skip).length;
    }));
    if (no) add('info', '폰: 마지막 줄 한 어절(참고)', -1, no + '곳');
  }
  return out;
}

async function main() {
  const args = process.argv.slice(2);
  const oi = args.indexOf('--out');
  const outPath = oi >= 0 ? args[oi + 1] : null;
  const file = args.find((a, i) => !a.startsWith('--') && (oi < 0 || i !== oi + 1));
  if (!file) { console.log('사용: node qa_deck.js 파일.html [--out 보고서.md]'); process.exit(2); }
  const prep = skeleton.prepared(file);
  const browser = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  const findings = [];
  for (const w of DESKTOP.concat(PHONE)) {
    const pg = await browser.newPage({viewport: {width: w, height: 800}});
    pg.on('pageerror', e => findings.push({level: 'error', check: '페이지 스크립트 오류', w, slide: -1, name: '', detail: e.message}));
    await pg.goto('file://' + prep.file);
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(2500);
    const opts = {once: w === DESKTOP[0], orphanLevel: w === DESKTOP[0] ? 'error' : 'warn'};
    const r = await pg.evaluate(`(${inPage.toString()})(${JSON.stringify(opts)})`);
    findings.push(...r);
    await pg.close();
  }
  await browser.close();
  prep.done();

  // 같은 문제가 여러 폭에서 나오면 한 줄로 합친다
  const key = f => [f.level, f.check, f.slide, f.detail].join('|');
  const merged = new Map();
  findings.forEach(f => {
    const k = key(f);
    if (!merged.has(k)) merged.set(k, Object.assign({}, f, {widths: [f.w]}));
    else merged.get(k).widths.push(f.w);
  });
  const rows = [...merged.values()].filter(f => f.check !== 'meta');
  const meta = findings.filter(f => f.check === 'meta' && f.w === DESKTOP[0])[0];
  const order = {error: 0, warn: 1, info: 2};
  rows.sort((a, b) => order[a.level] - order[b.level] || a.check.localeCompare(b.check) || a.slide - b.slide);
  const cnt = l => rows.filter(f => f.level === l).length;
  const label = {error: '오류', warn: '주의', info: '참고'};

  const lines = [];
  lines.push('# 자동 검사 결과: ' + path.basename(file));
  lines.push('');
  lines.push('- 검사한 파일: `' + path.basename(file) + '` (' + (meta ? meta.detail.split(',')[0] : '') + ')');
  lines.push('- 검사 폭: PC ' + DESKTOP.join('·') + 'px, 폰 ' + PHONE.join('·') + 'px (구글 글꼴 실제 내려받음, Artifact 와 같은 틀을 씌운 표준 모드로 읽음)');
  lines.push('- 결과: 오류 ' + cnt('error') + '건, 주의 ' + cnt('warn') + '건, 참고 ' + cnt('info') + '건');
  lines.push('');
  if (rows.length) {
    lines.push('| 단계 | 검사 | 어디 | 내용 | 폭 |');
    lines.push('|---|---|---|---|---|');
    rows.forEach(f => lines.push('| ' + label[f.level] + ' | ' + f.check + ' | ' + (f.name || '문서 전체') + ' | ' + (f.detail || '').replace(/\|/g, '\\|') + ' | ' + f.widths.join('·') + ' |'));
  } else {
    lines.push('문제가 없습니다.');
  }
  const text = lines.join('\n') + '\n';
  if (outPath) fs.writeFileSync(outPath, text, 'utf8');
  console.log(text);
  process.exit(cnt('error') ? 1 : 0);
}

module.exports = {inPage};
if (require.main === module) main();
