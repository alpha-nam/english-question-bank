// 문항 상세 서랍: 열기·닫기, '문제/해설' 탭(마우스·키보드), 해설 있음/없음, 담기·빼기, 비슷한 기출
const { test, expect, known } = require('../lib/fixtures');

const open = async (page, id) => {
  await page.click(`#listArea button[data-open="${id}"]`);
  await expect(page.locator('#drawer')).not.toHaveClass(/translate-x-full/);
};
const closed = page => expect(page.locator('#drawer')).toHaveClass(/translate-x-full/);

test.describe('문항 상세(서랍)', () => {
  test.beforeEach(async ({ app }) => { await app.go('find'); });

  test('열면 제목·문제가 보이고 서랍에 초점이 간다', async ({ app, page }) => {
    await open(page, '2099.09-31');
    await expect(page.locator('#drawerTitle')).toHaveText('2099년 9월 예시 가짜지문 31번 · 빈칸');
    await expect(page.locator('#drawer')).toBeFocused();
    await expect(page.locator('#dt-q')).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('#dtPanel')).toContainText('Maps are useful');
    await expect(page.locator('#dtPanel')).toContainText('TOP15 3위');
    await expect(page.locator('[data-dv=img]')).toBeDisabled();   // 예시 자료에는 원본 그림이 없다
  });

  test('해설 탭: 마우스로 바꾸면 정답과 "해설 준비 중"(예시 자료에는 해설이 없음)', async ({ app, page }) => {
    await open(page, '2099.09-31');
    await page.click('#dt-sol');
    await expect(page.locator('#dt-sol')).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('#dt-q')).toHaveAttribute('aria-selected', 'false');
    await expect(page.locator('#dtPanel')).toHaveAttribute('aria-labelledby', 'dt-sol');
    await expect(page.locator('#dtPanel')).toContainText('정답 ① ignore most details');
    await expect(page.locator('#dtPanel')).toContainText('해설 준비 중');
    await expect(page.locator('#dt-sol')).toBeFocused();
    await expect(page.locator('[data-dv=txt]')).toBeDisabled();   // 해설 탭에서는 보기 방식 단추를 끈다
  });

  test('해설 탭: ←/→ 키로 문제↔해설 전환, 초점이 따라간다', async ({ app, page }) => {
    await open(page, '2099.09-22');
    await page.focus('#dt-q');
    await page.keyboard.press('ArrowRight');
    await expect(page.locator('#dt-sol')).toBeFocused();
    await expect(page.locator('#dt-sol')).toHaveAttribute('aria-selected', 'true');
    await page.keyboard.press('ArrowLeft');
    await expect(page.locator('#dt-q')).toBeFocused();
    await expect(page.locator('#dtPanel')).toContainText('When students explain');
  });

  test('해설 탭: 해설(풀이·해석)이 있으면 보여 준다 (브라우저 안에서만 가짜 해설을 넣어 봄)', async ({ app, page }) => {
    await page.evaluate(() => { const d = D.find(x => x.id === '2099.09-32'); d.cm = { ex: '가짜 풀이: 측정을 멈추라는 흐름', tr: '가짜 해석: 몇 초마다 시계를 보는 주자는…' }; });
    await open(page, '2099.09-32');
    await page.click('#dt-sol');
    await expect(page.locator('#dtPanel')).toContainText('가짜 풀이');
    await expect(page.locator('#dtPanel')).toContainText('가짜 해석');
    await expect(page.locator('#dtPanel')).not.toContainText('해설 준비 중');
  });

  test('고른 탭은 다른 문항을 열어도 유지된다', async ({ app, page }) => {
    await open(page, '2099.09-22');
    await page.click('#dt-sol');
    await page.keyboard.press('Escape');
    await open(page, '2099.09-36');
    await expect(page.locator('#dt-sol')).toHaveAttribute('aria-selected', 'true');
  });

  test('서랍에서 담기 ↔ 빼기, 목록 체크칸과 맞물린다', async ({ app, page }) => {
    await open(page, '2099.09-18');
    await expect(page.locator('#drawerAddBtn')).toHaveText('시험지에 담기');
    await page.click('#drawerAddBtn');
    await expect(page.locator('#drawerAddBtn')).toHaveText('시험지에서 빼기');
    expect(await app.cartIds()).toEqual(['2099.09-18']);
    await page.click('#drawerAddBtn');
    expect(await app.cartIds()).toEqual([]);
    await page.click('#drawerAddBtn');
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-id="2099.09-18"]')).toBeChecked();
  });

  test('닫기: Esc, × 단추, 바깥(어두운 막) 누르기 — 초점은 연 단추로 돌아온다', async ({ app, page }) => {
    await open(page, '2099.09-31');
    await page.keyboard.press('Escape');
    await closed(page);
    await expect(page.locator('#listArea button[data-open="2099.09-31"]')).toBeFocused();
    await open(page, '2099.09-31');
    await page.click('#drawerClose');
    await closed(page);
    await open(page, '2099.09-31');
    await page.mouse.click(50, 450);   // 서랍 바깥
    await closed(page);
    await expect(page.locator('#scrim')).toBeHidden();
  });

  test('비슷한 기출: 누르면 그 문항으로 바뀐다', async ({ app, page }) => {
    await open(page, '2099.09-18');   // 예시 자료에서 18번은 38·22번과 낱말이 겹친다
    const sim = page.locator('[data-simgo]').first();
    if (!(await sim.count())) test.skip(true, '예시 자료에 비슷한 기출이 없음');
    const id = await sim.getAttribute('data-simgo');
    await sim.click();
    await expect(page.locator('#drawerTitle')).toContainText(id.split('-')[1] + '번');
  });

  test('행의 글자 칸을 눌러도 상세가 열린다', async ({ app, page }) => {
    await page.click('#listArea td[data-open="2099.09-36"]');
    await expect(page.locator('#drawer')).not.toHaveClass(/translate-x-full/);
    await expect(page.locator('#drawerTitle')).toContainText('36번');
  });

  test('교재 문항 목록: 지금 설계에서는 상세 보기 없이 담기만 된다(기록용)', async ({ app, page }) => {
    await page.click('[data-src=book]');
    await expect(page.locator('#listArea [data-open]')).toHaveCount(0);
    await page.click('text=7강 Ex 01');
    await closed(page);
  });
});
