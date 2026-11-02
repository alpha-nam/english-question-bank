// 내 시험지(오른쪽): 담기·빼기·순서 바꾸기·비우기와 되돌리기, 새로고침 뒤에도 남는지
const { test, expect } = require('../lib/fixtures');

test.describe('내 시험지', () => {
  test.beforeEach(async ({ app }) => { await app.go('find'); });

  test('체크칸으로 담고 빼면 개수·요약·단추 상태가 바뀐다', async ({ app, page }) => {
    await expect(page.locator('#printBtn')).toBeDisabled();
    await expect(page.locator('#saveSetBtn')).toBeDisabled();
    await page.check('[data-id="2099.09-22"]');
    await page.check('[data-id="2099.09-31"]');
    await expect(page.locator('#sideCartCount')).toHaveText('2');
    await expect(page.locator('#cartSum')).toContainText('독해 2');
    await expect(page.locator('#printBtn')).toBeEnabled();
    await expect(page.locator('#saveSetBtn')).toBeEnabled();
    await expect(page.locator('#listArea tr.row-selected')).toHaveCount(2);
    await page.uncheck('[data-id="2099.09-22"]');
    await expect(page.locator('#sideCartCount')).toHaveText('1');
    expect(await app.cartIds()).toEqual(['2099.09-31']);
  });

  test('순서 바꾸기 ▲▼ 와 빼기 ✕', async ({ app, page }) => {
    for (const id of ['2099.09-18', '2099.09-22', '2099.09-31']) await page.check(`[data-id="${id}"]`);
    await page.click('#cartList [data-mv="2"][data-d="-1"]');   // 3번째를 위로
    expect(await app.cartIds()).toEqual(['2099.09-18', '2099.09-31', '2099.09-22']);
    await page.click('#cartList [data-mv="0"][data-d="1"]');    // 1번째를 아래로
    expect(await app.cartIds()).toEqual(['2099.09-31', '2099.09-18', '2099.09-22']);
    await page.click('#cartList [data-rm="2099.09-18"]');
    expect(await app.cartIds()).toEqual(['2099.09-31', '2099.09-22']);
    await expect(page.locator('[data-id="2099.09-18"]')).not.toBeChecked();
  });

  test('맨 위 ▲ / 맨 아래 ▼ 는 아무 일도 하지 않거나 꺼져 있다', async ({ app, page }) => {
    for (const id of ['2099.09-18', '2099.09-22']) await page.check(`[data-id="${id}"]`);
    const up = page.locator('#cartList [data-mv="0"][data-d="-1"]');
    if (await up.isEnabled()) await up.click();
    const dn = page.locator('#cartList [data-mv="1"][data-d="1"]');
    if (await dn.isEnabled()) await dn.click();
    expect(await app.cartIds()).toEqual(['2099.09-18', '2099.09-22']);
  });

  test('전체 비우기 → 되돌리기', async ({ app, page }) => {
    await page.click('#addAllBtn');
    await page.click('#clearBtn');
    expect(await app.cartIds()).toEqual([]);
    await expect(page.locator('#sideCartCount')).toHaveText('0');
    await expect(app.toast()).toContainText('비웠습니다');
    await app.undo();
    expect((await app.cartIds()).length).toBe(6);
    await expect(page.locator('#sideCartCount')).toHaveText('6');
  });

  test('새로고침해도 담은 문항이 남아 있다(브라우저 저장)', async ({ app, page }) => {
    await page.check('[data-id="2099.09-32"]');
    await page.check('[data-id="2099.09-36"]');
    await page.reload();
    await app.go('find');
    await expect(page.locator('#sideCartCount')).toHaveText('2');
    await expect(page.locator('[data-id="2099.09-32"]')).toBeChecked();
  });

  test('교재 문항과 기출 문항을 섞어 담을 수 있다', async ({ app, page }) => {
    await page.check('[data-id="2099.09-22"]');
    await page.click('[data-src=book]');
    const first = (await app.rowIds())[0];
    await page.check(`[data-id="${first}"]`);
    expect(await app.cartIds()).toEqual(['2099.09-22', first]);
    await expect(page.locator('#sideCartCount')).toHaveText('2');
  });
});
