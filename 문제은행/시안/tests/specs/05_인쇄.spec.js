// 인쇄 창: 학생용·교사용, 번호 방식, 제목, 해설 QR, 미리보기 크기, 쪽 넘기기(단추·화살표), PDF 만들기, 닫기
// 해설지(만들 것 세 번째)는 시험하지 않는다: 해설은 QR로 주기로 함(제이님 2026-11-02).
const { test, expect } = require('../lib/fixtures');

const pv = page => page.locator('#pvPages .xp').first();
const allText = page => page.$$eval('#pvPages .xp', a => a.map(x => x.innerText).join('\n'));

test.describe('인쇄 창', () => {
  test.beforeEach(async ({ app, page }) => {
    await app.go('find');
    await page.click('#addAllBtn');   // 6문항 → 학생용 2쪽
    await app.openPrint();
  });

  test('열리면 닫기 단추에 초점, 학생용·2쪽·6문항 요약', async ({ app, page }) => {
    await expect(page.locator('#pmClose')).toBeFocused();
    await expect(page.locator('[data-pg=kind][data-i="0"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#pmSum')).toHaveText(/학생용 · 2쪽 · 6문항/);
    expect(await app.pageInfo()).toEqual({ now: 1, total: 2 });
    const t = await allText(page);
    expect(t).toContain('영어 영역');
    expect(t).not.toContain('(교사용)');
  });

  test('교사용으로 바꾸면 "(교사용)" 머리가 붙고, 학생용으로 돌아올 수 있다', async ({ app, page }) => {
    await page.click('[data-pg=kind][data-i="1"]');
    await expect(page.locator('[data-pg=kind][data-i="1"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#pmSum')).toContainText('교사용');
    await expect(pv(page)).toContainText('(교사용)');
    await page.click('[data-pg=kind][data-i="0"]');
    await expect(page.locator('#pmSum')).toContainText('학생용');
    await expect(pv(page)).not.toContainText('(교사용)');
  });

  test('번호: 1번부터 새로 ↔ 원래 번호', async ({ app, page }) => {
    await expect(pv(page)).toContainText(/QR1\.\s*다음 글의 목적/);
    await page.click('[data-pg=num][data-i="1"]');
    await expect(page.locator('[data-pg=num][data-i="1"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(pv(page)).toContainText(/(^|[^0-9])18\.\s*다음 글의 목적/);
  });

  test('해설 QR 끄고 켜기', async ({ app, page }) => {
    await expect(page.locator('#pvPages .xp svg')).not.toHaveCount(0);
    await page.uncheck('[data-pc=qr]');
    await expect(page.locator('#pvPages .xp').first()).not.toContainText('해설 QR');
    await page.check('[data-pc=qr]');
    await expect(page.locator('#pvPages .xp').first()).toContainText('해설 QR');
  });

  test('제목을 적으면 미리보기와 PDF 파일 이름(문서 제목)에 쓰인다', async ({ app, page }) => {
    await page.fill('[data-pt=title]', '2학기 중간 대비');
    await expect(pv(page)).toContainText('2학기 중간 대비');
    await page.click('#pmGo');
    await expect.poll(() => page.evaluate(() => window.__print.length)).toBe(1);
    const p = await page.evaluate(() => window.__print[0]);
    expect(p.title).toBe('2학기 중간 대비');
  });

  test('쪽 넘기기: 단추, 끝에서 단추 꺼짐, 초점 유지', async ({ app, page }) => {
    await expect(page.locator('#pvPrev')).toBeDisabled();
    await page.click('#pvNext');
    expect(await app.pageInfo()).toEqual({ now: 2, total: 2 });
    await expect(page.locator('#pvNext')).toBeDisabled();
    await expect(page.locator('#pvPrev')).toBeFocused();   // 꺼진 단추 대신 반대쪽 단추로 초점
    await page.click('#pvPrev');
    expect(await app.pageInfo()).toEqual({ now: 1, total: 2 });
  });

  test('쪽 넘기기: 키보드 ←/→ (미리보기에 초점이 있을 때)', async ({ app, page }) => {
    await page.focus('#pmPreview');
    await page.keyboard.press('ArrowRight');
    expect(await app.pageInfo()).toEqual({ now: 2, total: 2 });
    await page.keyboard.press('ArrowRight');   // 마지막 쪽에서는 그대로
    expect(await app.pageInfo()).toEqual({ now: 2, total: 2 });
    await page.keyboard.press('ArrowLeft');
    expect(await app.pageInfo()).toEqual({ now: 1, total: 2 });
  });

  test('쪽 넘기기: 제목 칸에서 ←/→ 는 글자 이동만 하고 쪽은 그대로', async ({ app, page }) => {
    await page.fill('[data-pt=title]', 'abc');
    await page.focus('[data-pt=title]');
    await page.keyboard.press('ArrowLeft');
    expect((await app.pageInfo()).now).toBe(1);
  });

  test('미리보기 크기: 100% 를 누르면 실제 크기, 쪽 맞춤으로 돌아오기', async ({ app, page }) => {
    await page.click('[data-pz="100"]');
    await expect(page.locator('[data-pz="100"]')).toHaveAttribute('aria-pressed', 'true');
    await expect.poll(() => page.evaluate(() => [...document.querySelectorAll('#pvPages .xp')].find(x => x.style.display !== 'none').style.zoom)).toBe('1');
    await page.click('[data-pz="0"]');
    await expect(page.locator('[data-pz="0"]')).toHaveAttribute('aria-pressed', 'true');
    await expect.poll(() => page.evaluate(() => +[...document.querySelectorAll('#pvPages .xp')].find(x => x.style.display !== 'none').style.zoom)).toBeLessThan(1);
  });

  test('PDF 만들기: 미리보기 쪽 수 그대로 인쇄 묶음을 만들고, 인쇄가 끝나면 치운다', async ({ app, page }) => {
    await page.click('#pmGo');
    await expect.poll(() => page.evaluate(() => window.__print.length)).toBe(1);
    const p = await page.evaluate(() => window.__print[0]);
    expect(p.pages).toBe(2);
    expect(p.title).toBe('영어 문제지');
    await expect(page.locator('#printRoot')).toHaveCount(0);
    expect(await page.title()).not.toContain('영어 문제지');   // 원래 제목으로 돌아옴
    await expect(app.toast()).toContainText('PDF로 저장');
  });

  test('PDF 만들기: 교사용도 쪽 수가 맞다', async ({ app, page }) => {
    await page.click('[data-pg=kind][data-i="1"]');
    await expect(page.locator('#pmSum')).toContainText('교사용');
    const total = (await app.pageInfo()).total;
    await page.click('#pmGo');
    await expect.poll(() => page.evaluate(() => window.__print.length)).toBe(1);
    expect((await page.evaluate(() => window.__print[0])).pages).toBe(total);
  });

  test('인쇄 설정은 새로고침 뒤에도 남는다(교사용·원래 번호)', async ({ app, page }) => {
    await page.click('[data-pg=kind][data-i="1"]');
    await page.click('[data-pg=num][data-i="1"]');
    await page.reload();
    await app.go('find');
    await app.openPrint();
    await expect(page.locator('[data-pg=kind][data-i="1"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('[data-pg=num][data-i="1"]')).toHaveAttribute('aria-pressed', 'true');
  });

  test('Esc·닫기·× 로 닫히고 초점이 "인쇄 및 미리보기" 단추로 돌아온다', async ({ app, page }) => {
    await page.keyboard.press('Escape');
    await expect(page.locator('#printModal')).toBeHidden();
    await expect(page.locator('#printBtn')).toBeFocused();
    await page.click('#printBtn'); await app.waitPreview();
    await page.click('#pmCancel');
    await expect(page.locator('#printModal')).toBeHidden();
    await page.click('#printBtn'); await app.waitPreview();
    await page.click('#pmClose');
    await expect(page.locator('#printModal')).toBeHidden();
  });
});

test('담은 문항이 없으면 인쇄 단추가 꺼져 있다', async ({ app, page }) => {
  await app.go('find');
  await expect(page.locator('#printBtn')).toBeDisabled();
});
