// 문제은행 시안(예시 화면) 끝까지 시험. 실행: README.md 참고
const { defineConfig } = require('@playwright/test');

const W = { '1440': { width: 1440, height: 900 }, '768': { width: 768, height: 1024 }, '390': { width: 390, height: 844 } };

module.exports = defineConfig({
  testDir: './specs',
  globalSetup: require.resolve('./lib/global-setup.js'),
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['list'], ['json', { outputFile: 'test-results/결과.json' }]],
  use: {
    locale: 'ko-KR',
    timezoneId: 'Asia/Seoul',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    // 기능 흐름(홈 → 문제 고르기 → 시험지 → 보관함 → 인쇄 → 문항 상세)은 데스크톱 너비에서
    { name: '1440', use: { viewport: W['1440'] }, testIgnore: /화면너비/ },
    // 화면 너비 점검은 세 너비 모두
    { name: 'w1440', use: { viewport: W['1440'] }, testMatch: /화면너비/ },
    { name: 'w768', use: { viewport: W['768'] }, testMatch: /화면너비/ },
    { name: 'w390', use: { viewport: W['390'], isMobile: true, hasTouch: true }, testMatch: /화면너비/ },
  ],
});
