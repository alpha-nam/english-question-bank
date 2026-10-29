// 화면 자동 감사: ?audit=1 일 때 로드된다. 결과는 <pre id="__audit"> 에 JSON으로 넣는다(Chrome --dump-dom 으로 읽음).
(function () {
  function parse(c) { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(x => parseFloat(x)); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; }
  function over(top, bottom) { const a = top.a + bottom.a * (1 - top.a); if (a === 0) return { r: 0, g: 0, b: 0, a: 0 }; return { r: (top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a, g: (top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a, b: (top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a, a }; }
  function lum(c) { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); }
  function ratio(a, b) { const l1 = lum(a), l2 = lum(b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); }
  function bgOf(el) {
    let layers = [], n = el;
    while (n && n.nodeType === 1) { const cs = getComputedStyle(n); const c = parse(cs.backgroundColor); if (c && c.a > 0) layers.push(c); if (c && c.a >= 1) break; n = n.parentElement; }
    let acc = { r: 255, g: 255, b: 255, a: 1 };
    const base = parse(getComputedStyle(document.body).backgroundColor);
    if (base && base.a > 0) acc = base;
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], acc);
    return acc;
  }
  function visible(el) { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0.05 && r.bottom > 0 && r.right > 0 && r.left < innerWidth && r.top < innerHeight; }
  function textOf(el) { let t = ''; for (const n of el.childNodes) if (n.nodeType === 3) t += n.nodeValue; return t.trim(); }
  const out = { w: innerWidth, h: innerHeight, contrast: { n: 0, fail: 0, min: 99, worst: [] }, sizes: { under12: 0, under14: 0, n: 0 }, targets: { n: 0, under24: 0, under44: 0, small: [] }, overflow: [], align: {}, grid: { off: 0, n: 0 }, hscroll: document.documentElement.scrollWidth > innerWidth + 1 };
  const seen = new Set();
  document.querySelectorAll('body *').forEach(el => {
    if (!visible(el) || ['SCRIPT', 'STYLE', 'IMG', 'SVG', 'PATH'].includes(el.tagName)) return;
    const t = textOf(el); const cs = getComputedStyle(el);
    if (t) {
      const fg = parse(cs.color); if (!fg) return;
      const bg = bgOf(el); const f = over(fg, bg); const r = ratio(f, bg);
      const fs = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 700;
      const need = (fs >= 24 || (fs >= 18.66 && bold)) ? 3 : 4.5;
      out.contrast.n++; if (r < need) { out.contrast.fail++; if (out.contrast.worst.length < 12) out.contrast.worst.push({ t: t.slice(0, 24), r: +r.toFixed(2), need, fs, cls: (el.className || el.tagName).toString().slice(0, 30) }); }
      out.contrast.min = Math.min(out.contrast.min, +r.toFixed(2));
      out.sizes.n++; if (fs < 12) out.sizes.under12++; if (fs < 14) out.sizes.under14++;
    }
    const tag = el.tagName;
    if (tag === 'BUTTON' || tag === 'A' || tag === 'SELECT' || tag === 'INPUT' || el.getAttribute('role') === 'button' || el.onclick || el.dataset.go || el.dataset.id) {
      const r = el.getBoundingClientRect(); const key = el.className + '|' + Math.round(r.top) + '|' + Math.round(r.left); if (seen.has(key)) return; seen.add(key);
      out.targets.n++; const m = Math.min(r.width, r.height);
      if (m < 24) { out.targets.under24++; if (out.targets.small.length < 8) out.targets.small.push({ t: (el.innerText || el.className).slice(0, 14), w: Math.round(r.width), h: Math.round(r.height) }); }
      if (m < 44) out.targets.under44++;
    }
    if (el.scrollWidth > el.clientWidth + 2 && cs.overflow !== 'visible' && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll' && cs.textOverflow !== 'ellipsis' && !el.closest('.sr') && !el.classList.contains('sr') && out.overflow.length < 8) out.overflow.push({ cls: (el.className || tag).toString().slice(0, 30), sw: el.scrollWidth, cw: el.clientWidth });
  });
  // 간격이 4px 배수 격자에 맞는지(패딩·간격)
  document.querySelectorAll('.card,.box,.btn,button,.tg,.chip,.trow,.row,.ch,.cf,header,.drawer,.mbox,.ecard').forEach(el => {
    if (!visible(el)) return; const cs = getComputedStyle(el);
    ['paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft', 'columnGap', 'rowGap'].forEach(k => { const v = parseFloat(cs[k]); if (!isNaN(v) && v > 0) { out.grid.n++; if (Math.round(v) % 4 !== 0) { out.grid.off++; (out.grid.who = out.grid.who || []).length < 6 && out.grid.who.push((el.className || el.tagName).toString().slice(0, 24) + ':' + k + '=' + v); } } });
  });
  // 정렬: 같은 줄(행) 항목의 위쪽·높이가 같은가
  function rows(sel, label) {
    const els = [...document.querySelectorAll(sel)].filter(visible); if (els.length < 2) { out.align[label] = { n: els.length }; return; }
    const g = {}; els.forEach(e => { const r = e.getBoundingClientRect(); const k = Math.round(r.top / 10); (g[k] = g[k] || []).push(r); });
    let bad = 0, rowsN = 0, gapVar = 0;
    Object.values(g).forEach(rs => { if (rs.length < 2) return; rowsN++; const tops = rs.map(r => Math.round(r.top)), hs = rs.map(r => Math.round(r.height)); if (Math.max(...tops) - Math.min(...tops) > 1 || Math.max(...hs) - Math.min(...hs) > 1) { bad++; (out.badrows = out.badrows || []).length < 4 && out.badrows.push({ label, tops, hs, lefts: rs.map(r => Math.round(r.left)) }); } rs.sort((a, b) => a.left - b.left); const gaps = rs.slice(1).map((r, i) => Math.round(r.left - rs[i].right)); if (gaps.length > 1 && Math.max(...gaps) - Math.min(...gaps) > 2) gapVar++; });
    out.align[label] = { n: els.length, rows: rowsN, misaligned_rows: bad, uneven_gap_rows: gapVar };
  }
  rows('.card', '카드(같은 줄 위·높이)'); rows('.nav a', '상단 메뉴'); rows('.seg button', '탭·세그먼트'); rows('.chip', '칩'); rows('.deck', '연계 분석 행'); rows('.opt', '선택 항목');
  // 카드 머리: 줄 수(한 줄이어야 깔끔)
  const heads = [...document.querySelectorAll('.card .ch')].filter(visible); const hh = heads.map(h => Math.round(h.getBoundingClientRect().height));
  out.align['카드 머리 높이 종류'] = heads.length ? [...new Set(hh)].length : 0; out.align['카드 머리 최대 높이'] = hh.length ? Math.max(...hh) : 0;
  // 가장자리 정렬: 같은 컬럼 패널의 왼쪽 선
  const cols = [...document.querySelectorAll('.layout > .col')].filter(visible).map(c => Math.round(c.getBoundingClientRect().top)); out.align['3단 위쪽 높이 차'] = cols.length ? Math.max(...cols) - Math.min(...cols) : 0;
  // 폭 합(여백 대칭)
  const lay = document.querySelector('.layout'); if (lay && visible(lay)) { const r = lay.getBoundingClientRect(); out.align['레이아웃 좌우 여백'] = [Math.round(r.left), Math.round(innerWidth - r.right)]; }
  if (out.hscroll) out.wide = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 1 && !e.closest('.drawer,.my,.side,.nav') && !e.closest('tbody'); }).slice(0, 6).map(e => (e.className || e.tagName).toString().slice(0, 30) + '[' + (e.textContent || '').trim().slice(0, 12) + '|' + (e.parentElement ? e.parentElement.className : '') + ']:' + Math.round(e.getBoundingClientRect().right) + ' sw=' + document.documentElement.scrollWidth);
  const pre = document.createElement('pre'); pre.id = '__audit'; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
})();
