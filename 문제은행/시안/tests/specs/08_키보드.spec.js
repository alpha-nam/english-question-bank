// 키보드만으로 쓰기: 메뉴·체크칸·서랍·인쇄 창의 Tab 순서, Enter/Space, Esc, 초점 가두기(aria-modal)
// (문항 상세 '문제/해설' 탭 ←/→ 는 06, 인쇄 쪽 넘기기 ←/→ 는 05 에 있다)
const { test, expect, known } = require('../lib/fixtures');

const active = page => page.evaluate(() => { const a = document.activeElement; return a ? (a.id ? '#' + a.id : a.tagName.toLowerCase()) : null; });
// Tab 을 n번 누르며 초점이 간 요소가 root 안에 있는지 적는다
async function tabWithin(page, root, n) {
  const seq = [];
  for (let i = 0; i < n; i++) {
    await page.keyboard.press('Tab');
    seq.push(await page.evaluate(r => !!document.activeElement.closest(r), root));
  }
  return seq;
}

test.describe('키보드', () => {
  test('왼쪽 메뉴: Tab 으로 닿고 Enter 로 화면이 바뀐다', async ({ app, page }) => {
    await page.focus('#sideNav [data-view=find]');
    await expect(page.locator('#sideNav [data-view=find]')).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.locator('#findView')).toBeVisible();
    await page.focus('#sideNav [data-view=sets]');
    await page.keyboard.press('Enter');   // 메뉴는 <a> 링크라 Space 가 아니라 Enter 로 누른다(링크의 원래 동작)
    await expect(page.locator('#setsView')).toBeVisible();
  });

  test('메뉴 단추에는 눈에 보이는 초점 표시가 있다', async ({ app, page }) => {
    await page.focus('#sideNav [data-view=find]');
    await page.keyboard.press('Tab');   // 키보드로 옮겨야 :focus-visible
    const ol = await page.evaluate(() => { const cs = getComputedStyle(document.activeElement); return { w: parseFloat(cs.outlineWidth), s: cs.outlineStyle, sh: cs.boxShadow }; });
    expect(ol.s !== 'none' && ol.w > 0 || ol.sh !== 'none', `초점 표시 없음: ${JSON.stringify(ol)}`).toBe(true);
  });

  test('체크칸: Space 로 담고 다시 Space 로 뺀다', async ({ app, page }) => {
    await app.go('find');
    const before = await app.cartCount();
    const cb = page.locator('#listArea input[data-id]:visible').first();
    const id = await cb.getAttribute('data-id');
    const same = page.locator(`#listArea input[data-id="${id}"]`);
    await cb.focus();
    await page.keyboard.press('Space');
    await expect(same).toBeChecked();
    expect(await app.cartCount()).toBe(before + 1);
    await same.focus();   // 담으면 목록을 다시 그려서 초점이 사라진다(아래 별도 시험에서 기록) → 다시 맞춘다
    await page.keyboard.press('Space');
    await expect(same).not.toBeChecked();
    expect(await app.cartCount()).toBe(before);
  });

  test('체크칸: 담은 뒤에도 초점이 그 체크칸에 남아 있어야 한다', async ({ app, page }) => {
    await app.go('find');
    const cb = page.locator('#listArea input[data-id]:visible').first();
    const id = await cb.getAttribute('data-id');
    await cb.focus();
    await page.keyboard.press('Space');
    await expect(page.locator(`#listArea input[data-id="${id}"]`)).toBeChecked();
    const at = await page.evaluate(() => { const a = document.activeElement; return a === document.body ? 'body' : (a.dataset && a.dataset.id) || a.id || a.tagName; });
    known(test, at !== id, `담은 뒤 초점이 ${at} 로 옮겨진다(목록을 다시 그림). 키보드 사용자는 연이어 담으려면 처음부터 Tab 을 다시 눌러야 한다. 홈 화면은 초점을 되살린다.`);
    expect(at).toBe(id);
  });

  test('서랍: 열린 뒤 Tab 은 서랍 안에서 돈다 (aria-modal 초점 가두기)', async ({ app, page }) => {
    await app.go('find');
    await page.locator('#listArea button[data-open="2099.09-31"]').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#drawer')).not.toHaveClass(/translate-x-full/);
    await expect(page.locator('#drawer')).toBeFocused();
    const seq = await tabWithin(page, '#drawer', 25);
    known(test, seq.includes(false), '서랍(aria-modal)에 초점 가두기가 없다: Tab 을 계속 누르면 초점이 서랍 밖(뒤쪽 목록)으로 나간다. keydown Tab 처리 또는 뒤쪽 inert 필요.');
    expect(seq.every(Boolean), `서랍 밖으로 나간 Tab 위치: ${seq.map((v, i) => v ? '' : i + 1).filter(Boolean)}`).toBe(true);
  });

  test('서랍: Esc 로 닫히고 초점이 열었던 단추로 돌아온다', async ({ app, page }) => {
    await app.go('find');
    const opener = page.locator('#listArea button[data-open="2099.09-31"]');
    await opener.focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('#drawer')).not.toHaveClass(/translate-x-full/);
    await page.keyboard.press('Escape');
    await expect(page.locator('#drawer')).toHaveClass(/translate-x-full/);
    await expect(opener).toBeFocused();
  });

  test('인쇄 창: 열면 닫기 단추에 초점, Esc 로 닫히고 인쇄 단추로 돌아온다', async ({ app, page }) => {
    await app.go('find');
    await page.evaluate(() => document.getElementById('addAllBtn').click());
    await page.focus('#printBtn');
    await page.keyboard.press('Enter');
    await expect(page.locator('#printModal')).toBeVisible();
    await expect(page.locator('#pmClose')).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(page.locator('#printModal')).toBeHidden();
    await expect(page.locator('#printBtn')).toBeFocused();
  });

  test('인쇄 창: 설정 단추를 Tab/Space 로 바꿀 수 있다', async ({ app, page }) => {
    await app.go('find');
    await page.evaluate(() => document.getElementById('addAllBtn').click());
    await app.openPrint();
    const t = page.locator('[data-pg=kind][data-i="1"]');
    await t.focus();
    await page.keyboard.press('Space');
    await expect(t).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#pmSum')).toContainText('교사용');
  });

  test('인쇄 창: Tab 은 창 안에서 돈다 (aria-modal 초점 가두기)', async ({ app, page }) => {
    await app.go('find');
    await page.evaluate(() => document.getElementById('addAllBtn').click());
    await app.openPrint();
    const seq = await tabWithin(page, '#printModal', 40);
    known(test, seq.includes(false), '인쇄 창(aria-modal)에 초점 가두기가 없다: Tab 을 계속 누르면 초점이 창 밖(뒤쪽 화면)으로 나간다.');
    expect(seq.every(Boolean), `창 밖으로 나간 Tab 위치: ${seq.map((v, i) => v ? '' : i + 1).filter(Boolean)}`).toBe(true);
  });
});
