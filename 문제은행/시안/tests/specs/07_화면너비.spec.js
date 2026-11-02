// 화면 너비 1440 · 768 · 390 에서 장면마다: 가로 스크롤 없음, 콘솔 오류 없음, 창 밖으로 잘린 요소 없음, 스크린샷
// 프로젝트 w1440 / w768 / w390 이 같은 시험을 너비만 바꿔 돌린다(playwright.config.js).
const path = require('path');
const { test, expect, known } = require('../lib/fixtures');

const SHOTS = path.join(__dirname, '..', '스크린샷');

const scenes = {
  '홈': async (app, page) => {},
  '문제고르기': async (app, page) => { await app.go('find'); },
  '문제고르기_담은뒤': async (app, page) => { await app.go('find'); await page.evaluate(() => document.getElementById('addAllBtn').click()); },
  '보관함': async (app, page) => {
    await app.go('find');
    await page.evaluate(() => document.getElementById('addAllBtn').click());
    page.once('dialog', d => d.accept('너비 시험'));
    await page.evaluate(() => document.getElementById('saveSetBtn').click());
    await app.go('sets');
  },
  '문항상세_문제': async (app, page) => {
    await app.go('find');
    await page.evaluate(() => document.querySelector('#listArea button[data-open="2099.09-31"]').click());
    await expect(page.locator('#drawer')).not.toHaveClass(/translate-x-full/);
    await page.waitForTimeout(350);   // 서랍 미끄러지는 동작(300ms)
  },
  '문항상세_해설': async (app, page) => {
    await app.go('find');
    await page.evaluate(() => document.querySelector('#listArea button[data-open="2099.09-31"]').click());
    await page.locator('#dt-sol').click();
    await page.waitForTimeout(350);
  },
  '인쇄창_학생용': async (app, page) => {
    await app.go('find');
    await page.evaluate(() => document.getElementById('addAllBtn').click());
    await page.evaluate(() => document.getElementById('printBtn').click());
    await app.waitPreview();
  },
  '인쇄창_교사용': async (app, page) => {
    await app.go('find');
    await page.evaluate(() => document.getElementById('addAllBtn').click());
    await page.evaluate(() => document.getElementById('printBtn').click());
    await app.waitPreview();
    await page.locator('[data-pg=kind][data-i="1"]').click();
    await expect(page.locator('#pmSum')).toContainText('교사용');
  },
};

for (const [name, setup] of Object.entries(scenes)) {
  test(`${name}`, async ({ app, page }, info) => {
    const w = page.viewportSize().width;
    await setup(app, page);
    await page.screenshot({ path: path.join(SHOTS, `${name}_${w}.png`) });

    const hs = await app.hscroll();
    expect(hs.over, `가로 스크롤이 생기면 안 됩니다 (문서 ${hs.doc}px / 창 ${hs.win}px)`).toBe(false);

    const inner = await app.innerHScroll();
    info.annotations.push({ type: '안쪽 가로 스크롤', description: inner.join(' | ') || '없음' });
    const clip = await app.clipped();
    info.annotations.push({ type: '잘린 요소', description: clip.join(' | ') || '없음' });
    known(test, (clip.length > 0 || inner.length > 0) && w < 1440,
      `${w}px: 화면에 반응형(좁은 화면) 배치가 없다. 왼쪽 메뉴 188px + 필터 272px + 내 시험지 320px, 인쇄 창 오른쪽 설정 320px가 고정 폭이라 창 밖으로 잘린다. body가 overflow:hidden이라 가로 스크롤 대신 잘림으로 나타난다.`);
    expect({ clip, inner }, '창 밖으로 잘리거나 안쪽에서 옆으로 밀리는 곳이 없어야 합니다').toEqual({ clip: [], inner: [] });
  });
}
