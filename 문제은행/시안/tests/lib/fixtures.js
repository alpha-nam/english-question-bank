// 공통 준비: 가짜 주소로 예시 화면 열기 · 콘솔 오류 모으기 · window.print 가로채기
const base = require('@playwright/test');
const v = require('./vendor');

// 알려진 문제(아직 고치지 않은 화면 문제)는 기본으로 '예상된 실패'로 둔다.
// 고쳐지면 Playwright가 "예상과 달리 통과"로 알려 준다. QB_STRICT=1 이면 그냥 실패로 센다.
const STRICT = process.env.QB_STRICT === '1';
function known(test, cond, why) {
  if (!cond) return;
  test.info().annotations.push({ type: '알려진 문제', description: why });
  if (!STRICT) test.fail(true, why);
}

const test = base.test.extend({
  context: async ({ context }, use) => {
    await v.installSite(context);
    await context.addInitScript(() => {
      // 헤드리스에서는 인쇄 창이 열리지 않는다: 부른 횟수와 인쇄용 쪽 수만 적고 afterprint를 보낸다
      window.__print = [];
      window.print = () => {
        const r = document.getElementById('printRoot');
        window.__print.push({ pages: r ? r.querySelectorAll('.xp').length : 0, title: document.title });
        setTimeout(() => window.dispatchEvent(new Event('afterprint')), 0);
      };
    });
    await use(context);
  },
  // 콘솔 오류·페이지 오류·실패한 요청을 모은다. 시험 끝에 0개인지 확인한다.
  errors: async ({ context }, use) => {
    const errs = [];
    const watch = p => {
      p.on('console', m => { if (m.type() === 'error') errs.push(`[console] ${m.text()} @ ${p.url()}`); });
      p.on('pageerror', e => errs.push(`[pageerror] ${e.message}`));
      p.on('requestfailed', r => errs.push(`[requestfailed] ${r.url()} ${r.failure() && r.failure().errorText}`));
    };
    context.pages().forEach(watch);
    context.on('page', watch);
    await use(errs);
    base.expect(errs, '콘솔 오류가 없어야 합니다').toEqual([]);
  },
  app: async ({ page, errors }, use) => {
    await page.goto(v.URL_PAGE);
    await page.waitForFunction(() => document.querySelector('#homeView') && !document.querySelector('#homeView').classList.contains('hidden') || location.hash.startsWith('#sol='));
    await use(new App(page, errors));
  },
});

class App {
  constructor(page, errors) { this.page = page; this.errors = errors; }
  async go(view) { await this.page.click(`#sideNav [data-view=${view}]`); await base.expect(this.page.locator(`#${view}View`)).toBeVisible(); }
  cartIds() { return this.page.evaluate(() => JSON.parse(localStorage.getItem('qb2_cart') || '[]')); }
  async cartCount() { return +(await this.page.locator('#sideCartCount').innerText()); }
  rowIds() { return this.page.$$eval('#listArea input[data-id]', a => a.filter(e => e.offsetParent).map(e => e.dataset.id)); }
  toast() { return this.page.locator('#toast'); }
  async undo() { await this.page.locator('#toast button', { hasText: '되돌리기' }).click(); }
  async openPrint() { await this.page.click('#printBtn'); await base.expect(this.page.locator('#printModal')).toBeVisible(); await this.waitPreview(); }
  async waitPreview() { await this.page.waitForFunction(() => document.querySelectorAll('#pvPages .xp').length > 0 && /쪽/.test((document.getElementById('pvNow') || {}).textContent || '')); }
  pageInfo() { return this.page.evaluate(() => { const t = (document.getElementById('pvNow') || {}).textContent || ''; const m = t.match(/(\d+)\s*\/\s*(\d+)/); return m ? { now: +m[1], total: +m[2] } : null; }); }
  async saveAs(name) {
    this.page.once('dialog', d => d.accept(name));
    await this.page.click('#saveSetBtn');
  }
  // 가로 스크롤: 문서 전체가 창보다 넓은가
  hscroll() { return this.page.evaluate(() => ({ doc: document.documentElement.scrollWidth, body: document.body.scrollWidth, win: innerWidth, over: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) > innerWidth + 1 })); }
  // 안쪽 가로 스크롤: 화면 안 스크롤 상자(홈·보관함·목록·서랍·인쇄 설정 등)가 옆으로 밀리는가
  innerHScroll() {
    return this.page.evaluate(() => [...document.querySelectorAll('body *')].filter(e => {
      const cs = getComputedStyle(e), r = e.getBoundingClientRect();
      if (!r.width || cs.visibility === 'hidden' || e.closest('.hidden,.translate-x-full,#pvMeasure')) return false;
      if (!['auto', 'scroll'].includes(cs.overflowX)) return false;
      if (e.id === 'pmPreview') return false;   // 인쇄 미리보기는 확대(100~150%)하면 옆으로 넘기는 것이 정상
      return e.scrollWidth > e.clientWidth + 1;
    }).map(e => `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : '.' + String(e.className).trim().split(/\s+/).slice(0, 2).join('.')} (${e.scrollWidth}>${e.clientWidth})`));
  }
  // 잘림: 보이는 요소 중 오른쪽 끝이 창 밖으로 나간 것(가로 스크롤 상자 안은 제외)
  clipped(root = 'body') {
    return this.page.evaluate(root => {
      const iw = innerWidth, out = [];
      const scrollerX = e => { for (let n = e.parentElement; n && n !== document.body; n = n.parentElement) { const o = getComputedStyle(n).overflowX; if ((o === 'auto' || o === 'scroll') && n.getBoundingClientRect().right <= iw + 1) return true; } return false; };
      document.querySelectorAll(root + ' *').forEach(e => {
        const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
        if (!r.width || !r.height || cs.visibility === 'hidden' || e.closest('.hidden,.translate-x-full,.sr-only,#pvMeasure')) return;
        if (r.right > iw + 1 && r.left < iw && !scrollerX(e)) out.push(`${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}${e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.') : ''} → ${Math.round(r.right)}px`);
      });
      return out.slice(0, 8);
    }, root);
  }
}

module.exports = { test, expect: base.expect, known, v };
