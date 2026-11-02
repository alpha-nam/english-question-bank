// 문제 고르기: 자료(기출/교재), 시험 고르기 표, 영역·오답률·유형 거르기, 찾기, 모두 담기, TOP15 담기, 무작위 담기
const { test, expect, known } = require('../lib/fixtures');

test.describe('문제 고르기', () => {
  test.beforeEach(async ({ app }) => { await app.go('find'); });

  test('기본 목록: 독해 6문항, 표 머리와 담기 칸', async ({ app, page }) => {
    expect(await app.rowIds()).toEqual(['2099.09-18', '2099.09-22', '2099.09-31', '2099.09-32', '2099.09-36', '2099.09-38']);
    await expect(page.locator('[data-src=past]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#selectAll')).toBeVisible();
  });

  test('자료 탭: EBS 교재 문항 ↔ 기출문제', async ({ app, page }) => {
    await page.click('[data-src=book]');
    await expect(page.locator('[data-src=book]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('[data-src=past]')).toHaveAttribute('aria-pressed', 'false');
    const book = await app.rowIds();
    expect(book.length).toBeGreaterThan(0);
    expect(book.every(id => !id.startsWith('2099.09'))).toBe(true);
    await page.click('[data-src=past]');
    expect((await app.rowIds()).length).toBe(6);
  });

  test('시험 고르기: 펼치기·접기, 시험 빼기·모두 지우기, 다시 고르기', async ({ app, page }) => {
    const tgl = page.locator('[data-so]');
    await expect(tgl).toHaveAttribute('aria-expanded', 'false');
    await tgl.click();
    await expect(page.locator('[data-so]')).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator('#examPanel')).toBeVisible();
    // 시험 칸(2099년 9월)
    const cell = page.locator('#examPanel [data-ex="2099.09"]');
    await expect(cell).toBeVisible();
    // 선택 지우기 → 시험이 하나도 없으면 목록은 전체(같은 6문항) 또는 안내
    await page.click('[data-exall]');
    await expect(page.locator('[data-exrm]')).toHaveCount(0);
    // 칸 눌러 다시 고르기
    await page.locator('#examPanel [data-ex="2099.09"]').click();
    await expect(page.locator('[data-exrm="2099.09"]')).toBeVisible();
    expect((await app.rowIds()).length).toBe(6);
    // 접기
    await page.locator('[data-so]').click();
    await expect(page.locator('#examPanel')).toHaveCount(0);
  });

  test('기관 탭(평가원): 누르면 그 기관 시험을 모두 빼고, 다시 누르면 모두 고른다', async ({ app, page }) => {
    const og = page.locator('[data-og="평가원"]');
    await expect(og).toHaveAttribute('aria-pressed', 'true');
    await og.click();
    await expect(page.locator('[data-og="평가원"]')).toHaveAttribute('aria-pressed', 'false');
    await page.locator('[data-og="평가원"]').click();
    await expect(page.locator('[data-og="평가원"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('[data-exrm="2099.09"]')).toBeVisible();
  });

  test('aria-pressed 값은 true/false/mixed 중 하나여야 한다', async ({ app, page }) => {
    const bad = await page.$$eval('[aria-pressed]', a => a.filter(e => !['true', 'false', 'mixed'].includes(e.getAttribute('aria-pressed')))
      .map(e => `${e.outerHTML.slice(0, 60)}… aria-pressed="${e.getAttribute('aria-pressed')}"`));
    expect(bad).toEqual([]);
  });

  test('영역: 전체/듣기/독해', async ({ app, page }) => {
    await page.click('[data-area=listen]');
    await expect(page.locator('[data-area=listen]')).toHaveAttribute('aria-pressed', 'true');
    expect(await app.rowIds()).toEqual([]);   // 예시 자료에는 듣기 문항이 없다
    await page.click('[data-area=all]');
    expect((await app.rowIds()).length).toBe(6);
    await page.click('[data-area=read]');
    expect((await app.rowIds()).length).toBe(6);
  });

  test('오답률 TOP15만 보기', async ({ app, page }) => {
    await page.check('[data-wq=t]');
    expect((await app.rowIds()).sort()).toEqual(['2099.09-22', '2099.09-31', '2099.09-32', '2099.09-36', '2099.09-38']);
    await page.check('[data-wq=""]');
    expect((await app.rowIds()).length).toBe(6);
  });

  test('문제 유형 거르기(빈칸) · 초기화', async ({ app, page }) => {
    await page.check('[data-ty="R|빈칸"]');
    expect(await app.rowIds()).toEqual(['2099.09-31', '2099.09-32']);
    await page.check('[data-ty="R|순서"]');
    expect((await app.rowIds()).sort()).toEqual(['2099.09-31', '2099.09-32', '2099.09-36']);
    await page.click('#resetBtn');
    expect((await app.rowIds()).length).toBe(6);
    await expect(page.locator('[data-ty="R|빈칸"]')).not.toBeChecked();
  });

  test('찾기: 단어로 거르고, 없는 말이면 빈 목록, 지우면 원래대로', async ({ app, page }) => {
    const s = page.locator('#searchInput');
    await s.fill('map');
    const hit = await app.rowIds();
    expect(hit).toContain('2099.09-31');   // 31번 가짜 지문: "Maps are useful..."
    expect(hit.length).toBeLessThan(6);
    await s.fill('zzqqxx-없는말');
    expect(await app.rowIds()).toEqual([]);
    await expect(page.locator('#listArea')).not.toBeEmpty();   // 빈 목록 안내가 있어야 함
    await s.fill('');
    expect((await app.rowIds()).length).toBe(6);
  });

  test('보이는 문항 모두 담기 → 되돌리기', async ({ app, page }) => {
    await page.click('#addAllBtn');
    expect((await app.cartIds()).length).toBe(6);
    await expect(app.toast()).toContainText('6문항을 담았습니다');
    await app.undo();
    expect(await app.cartIds()).toEqual([]);
    await expect(page.locator('#sideCartCount')).toHaveText('0');
  });

  test('표 머리 체크칸(selectAll)으로 모두 담기/빼기', async ({ app, page }) => {
    await page.check('#selectAll');
    expect((await app.cartIds()).length).toBe(6);
    await page.uncheck('#selectAll');
    expect(await app.cartIds()).toEqual([]);
  });

  test('오답률 TOP15만 담기', async ({ app, page }) => {
    await page.click('#addTopBtn');
    expect((await app.cartIds()).length).toBe(5);
    await page.click('#addTopBtn');
    await expect(app.toast()).toContainText('새로 담을 TOP15 문항이 없습니다');
  });

  test('무작위로 고르기: 펼침 메뉴, 개수만큼 담기, 되돌리기', async ({ app, page }) => {
    await page.click('#randBox summary');
    await expect(page.locator('#randBox')).toHaveAttribute('open', '');
    const opts = await page.$$eval('#randN option', o => o.map(x => +x.value));
    const n = Math.min(...opts);
    await page.selectOption('#randN', String(n));
    await page.click('#randBtn');
    const ids = await app.cartIds();
    expect(ids.length).toBe(Math.min(n, 6));
    expect(new Set(ids).size).toBe(ids.length);   // 겹치지 않음
    await expect(app.toast()).toContainText('무작위로 담았습니다');
    await app.undo();
    expect(await app.cartIds()).toEqual([]);
  });

  test('무작위: 이미 다 담았으면 "새로 담을 문항이 없습니다"', async ({ app, page }) => {
    await page.click('#addAllBtn');
    await page.click('#randBox summary');
    await page.click('#randBtn');
    await expect(app.toast()).toContainText('새로 담을 문항이 없습니다');
  });

  test('무작위: TOP15 섞기 비율', async ({ app, page }) => {
    await page.click('#randBox summary');
    const tops = await page.$$eval('#randTop option', o => o.map(x => x.value));
    const hi = tops.map(Number).sort((a, b) => b - a)[0];
    await page.selectOption('#randTop', String(hi));
    await page.selectOption('#randN', (await page.$$eval('#randN option', o => o.map(x => x.value)))[0]);
    await page.click('#randBtn');
    const ids = await app.cartIds();
    const topSet = ['2099.09-22', '2099.09-31', '2099.09-32', '2099.09-36', '2099.09-38'];
    const topN = ids.filter(i => topSet.includes(i)).length;
    expect(topN).toBeGreaterThanOrEqual(Math.min(5, Math.round(ids.length * hi / 100)));
  });
});
