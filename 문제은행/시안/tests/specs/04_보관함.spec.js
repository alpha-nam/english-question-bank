// 보관함: 이름 붙여 저장, 카드·QR, 불러오기(시험지 수정), 덮어쓰기/새로 저장, 인쇄로 바로 가기, 삭제와 되돌리기
const { test, expect } = require('../lib/fixtures');

async function saved(page) { return page.evaluate(() => JSON.parse(localStorage.getItem('qb2_sets') || '[]')); }

test.describe('보관함', () => {
  test.beforeEach(async ({ app, page }) => {
    await app.go('find');
    for (const id of ['2099.09-22', '2099.09-31', '2099.09-32']) await page.check(`[data-id="${id}"]`);
  });

  test('비어 있을 때 안내 글', async ({ app, page }) => {
    await app.go('sets');
    await expect(page.locator('#setsView')).toContainText('아직 저장한 문제지가 없습니다');
  });

  test('이름을 적어 저장 → 보관함 카드에 이름·문항 수·QR이 나온다', async ({ app, page }) => {
    await app.saveAs('시험용 문제지 A');
    await expect(app.toast()).toContainText('보관함에 저장했습니다 · 3문항');
    await app.go('sets');
    const card = page.locator('.setcard', { hasText: '시험용 문제지 A' });
    await expect(card).toBeVisible();
    await expect(card).toContainText('3문항');
    await expect(card.locator('svg').first()).toBeVisible();   // QR(로컬 qrcode-generator 1.4.4)
    await expect(card.locator('a.sb-sol')).toHaveAttribute('href', /#sol=/);
  });

  test('이름 칸에서 취소하면 저장하지 않는다', async ({ app, page }) => {
    page.once('dialog', d => d.dismiss());
    await page.click('#saveSetBtn');
    expect(await saved(page)).toEqual([]);
  });

  test('불러오기(시험지 수정): 다른 문항을 담았다가 불러오면 저장한 문항으로 바뀌고, 되돌리기가 된다', async ({ app, page }) => {
    await app.saveAs('불러오기 시험');
    await page.click('#clearBtn');
    await page.check('[data-id="2099.09-18"]');
    await app.go('sets');
    await page.locator('.setcard', { hasText: '불러오기 시험' }).locator('[data-sload]').click();
    await expect(page.locator('#findView')).toBeVisible();
    expect(await app.cartIds()).toEqual(['2099.09-22', '2099.09-31', '2099.09-32']);
    await expect(app.toast()).toContainText('불러왔습니다');
    await app.undo();
    expect(await app.cartIds()).toEqual(['2099.09-18']);
  });

  test('불러온 문제지를 고쳐 다시 저장: 확인=덮어쓰기', async ({ app, page }) => {
    await app.saveAs('덮어쓸 시험');
    await page.check('[data-id="2099.09-36"]');
    page.once('dialog', d => { expect(d.type()).toBe('confirm'); d.accept(); });
    await page.click('#saveSetBtn');
    await expect(app.toast()).toContainText('덮어썼습니다');
    const s = await saved(page);
    expect(s.length).toBe(1);
    expect(s[0].ids).toEqual(['2099.09-22', '2099.09-31', '2099.09-32', '2099.09-36']);
    await app.undo();
    expect((await saved(page))[0].ids.length).toBe(3);
  });

  test('불러온 문제지를 고쳐 다시 저장: 취소=새 문제지로 저장', async ({ app, page }) => {
    await app.saveAs('원본');
    await page.check('[data-id="2099.09-36"]');
    const seen = [];
    page.on('dialog', d => { seen.push(d.type()); d.type() === 'confirm' ? d.dismiss() : d.accept('사본'); });
    await page.click('#saveSetBtn');
    await expect.poll(async () => (await saved(page)).length).toBe(2);
    expect(seen).toEqual(['confirm', 'prompt']);
    expect((await saved(page)).map(x => x.name)).toEqual(['사본', '원본']);
  });

  test('보관함 카드의 "인쇄"는 그 문제지를 불러와 인쇄 창을 연다', async ({ app, page }) => {
    await app.saveAs('인쇄할 시험');
    await page.click('#clearBtn');
    await app.go('sets');
    await page.locator('.setcard', { hasText: '인쇄할 시험' }).locator('[data-sprint]').click();
    await expect(page.locator('#printModal')).toBeVisible();
    await app.waitPreview();
    await expect(page.locator('#pmSum')).toContainText('3문항');
  });

  test('삭제 → 되돌리기', async ({ app, page }) => {
    await app.saveAs('지울 시험');
    await app.go('sets');
    await page.locator('[data-sdel]').first().click();
    await expect(page.locator('.setcard')).toHaveCount(0);
    await app.undo();
    await expect(page.locator('.setcard', { hasText: '지울 시험' })).toBeVisible();
  });

  test('새로고침해도 보관함이 남고, 홈에도 나온다', async ({ app, page }) => {
    await app.saveAs('남는 시험');
    await page.reload();
    await expect(page.locator('#homeView')).toContainText('남는 시험');
    await app.go('sets');
    await expect(page.locator('.setcard', { hasText: '남는 시험' })).toBeVisible();
  });

  test('해설 화면 링크(QR 주소)를 열면 학생용 해설 화면이 나온다', async ({ app, page, context }) => {
    await app.saveAs('QR 시험');
    await app.go('sets');
    const [sol] = await Promise.all([context.waitForEvent('page'), page.locator('a.sb-sol').first().click()]);
    await sol.waitForLoadState();
    expect(sol.url()).toContain('#sol=');
    await expect(sol.locator('body')).toContainText('QR 시험');
  });
});
