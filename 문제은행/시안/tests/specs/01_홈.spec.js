// 홈 화면: 시험 카드, 기관 거르기, 오답률 TOP15 담기, 막대 → 문항 상세, 보관함으로 가기
const { test, expect } = require('../lib/fixtures');

test.describe('홈', () => {
  test('처음 열면 홈이 보이고 메뉴에 현재 위치가 표시된다', async ({ app, page }) => {
    await expect(page.locator('#homeView')).toBeVisible();
    await expect(page.locator('#findView')).toBeHidden();
    await expect(page.locator('#sideNav [data-view=home]')).toHaveAttribute('aria-current', 'page');
    await expect(page.locator('#homeView')).toContainText('2099년 9월');
    await expect(page.locator('#homeView')).toContainText('평가원');
  });

  test('평가원/교육청 거르기 단추', async ({ app, page }) => {
    await page.click('[data-horg="교육청"]');
    await expect(page.locator('#homeView [data-htop2]')).toHaveCount(0);   // 예시 자료에는 교육청 시험이 없다
    await page.click('[data-horg="평가원"]');
    await expect(page.locator('#homeView [data-htop2="2099.09"]')).toBeVisible();
    await page.click('[data-horg=""]');
    await expect(page.locator('#homeView [data-htop2="2099.09"]')).toBeVisible();
  });

  test('오답률 TOP15 담기 → 내 시험지에 들어가고 되돌리기가 된다', async ({ app, page }) => {
    await page.click('[data-htop2="2099.09"]');
    await expect(app.toast()).toContainText('TOP15');
    const ids = await app.cartIds();
    expect(ids.length).toBe(5);   // 예시 자료의 TOP15 문항: 22·31·32·36·38
    expect(ids).toEqual(expect.arrayContaining(['2099.09-22', '2099.09-31', '2099.09-32', '2099.09-36', '2099.09-38']));
    await app.undo();
    expect(await app.cartIds()).toEqual([]);
    await page.click('[data-htop2="2099.09"]');
    // 다시 누르면 '이미 모두 담았습니다'
    await page.click('[data-htop2="2099.09"]');
    await expect(app.toast()).toContainText('이미 모두 담았습니다');
  });

  test('오답률 막대를 누르면 그 문항 상세가 열린다', async ({ app, page }) => {
    await page.click('#homeView [data-hq2="2099.09-32"]');
    await expect(page.locator('#drawer')).not.toHaveClass(/translate-x-full/);
    await expect(page.locator('#drawerTitle')).toContainText('32번');
    await page.keyboard.press('Escape');
    await expect(page.locator('#drawer')).toHaveClass(/translate-x-full/);
  });

  test('홈의 인쇄·저장 단추는 담은 문항이 없으면 꺼져 있다', async ({ app, page }) => {
    await expect(page.locator('[data-hprint]')).toBeDisabled();
    await page.click('[data-htop2="2099.09"]');
    await expect(page.locator('[data-hprint]')).toBeEnabled();
  });

  test('"모두 보기"는 보관함으로 간다', async ({ app, page }) => {
    await page.click('[data-hsets]');
    await expect(page.locator('#setsView')).toBeVisible();
    await expect(page.locator('#sideNav [data-view=sets]')).toHaveAttribute('aria-current', 'page');
  });
});
