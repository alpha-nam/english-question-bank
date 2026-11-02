# 문제은행 시안 화면 시험 (Playwright)

예시 화면(`예시_화면시안.html`, 가짜 지문만 사용)을 브라우저로 열어 홈 → 문제 고르기 → 담기/되돌리기 → 보관함 → 인쇄 창 → 문항 상세, 화면 너비(1440/768/390), 키보드 사용을 끝까지 확인합니다. `시안.template.html` 은 고치지 않습니다. **해설지 인쇄는 시험하지 않습니다**(QR로 제공 예정).

## 실행

```bash
cd 문제은행/시안/tests
npm install                 # 처음 한 번
npx playwright install chromium   # 브라우저가 없을 때만
npx playwright test         # 전체 (약 1분)
npx playwright test specs/08_키보드.spec.js          # 파일 하나
npx playwright test --project=w390                  # 화면 너비 하나(1440 | w1440 | w768 | w390)
```

시험 전에 `python build.py --예시` 로 예시 화면을 다시 만들고, 로컬 Tailwind CSS를 만듭니다(`lib/global-setup.js`).

| 환경 변수 | 뜻 |
|---|---|
| `QB_ONLINE=1` | 로컬 사본 대신 진짜 CDN(Tailwind·qrcode·Pretendard) 사용 |
| `QB_STRICT=1` | '알려진 문제'도 예상된 실패가 아니라 그냥 **실패**로 센다(고쳤는지 확인할 때) |
| `QB_SKIP_BUILD=1` | `build.py` 와 Tailwind 만들기를 건너뜀 |
| `PYTHON` | python 실행 파일 (기본 `python3`, Windows는 `python`) |

## CDN이 막힐 때(기본 동작)

화면은 가짜 주소 `http://qb.test/` 로 열고, CDN 요청을 `lib/vendor.js` 가 가로채 같은 버전의 npm 로컬 사본으로 대신 줍니다.
`tailwindcss 3.4.17`, `qrcode-generator 1.4.4`, `pretendard 1.3.9` (모두 `package.json`, `npm install` 으로 설치). `icons/` 3D 아이콘 PNG는 저장소에 없어 투명 그림으로 대신합니다. 인터넷이 되는 PC에서는 `QB_ONLINE=1` 로 진짜 CDN을 써도 됩니다.

## 구성

- `specs/01_홈` · `02_문제고르기` · `03_시험지` · `04_보관함` · `05_인쇄` · `06_문항상세` — 기능(너비 1440)
- `specs/07_화면너비` — 장면 8개 × 너비 3개: 가로 스크롤·잘림·안쪽 가로 스크롤·콘솔 오류
- `specs/08_키보드` — 메뉴·체크칸·서랍·인쇄 창의 Tab/Enter/Space/Esc, 초점 가두기
- `lib/fixtures.js` — 콘솔 오류 수집(항상 0이어야 통과), `window.print` 가로채기, `known()`
- 헤드리스에서는 인쇄 창이 열리지 않아 `window.print` 호출 횟수와 쪽 수만 확인합니다.
- 예시 자료에는 해설(`cm`)이 없어, 해설 탭은 브라우저 안에서만 가짜 해설을 넣어 확인합니다.

## 알려진 문제(예상된 실패)

아직 고치지 않은 화면 문제는 `known()` 으로 표시되어 **예상된 실패(expected failure)** 로 나옵니다. 고쳐서 통과하면 Playwright가 "예상과 달리 통과"로 알려 주니 그때 `known()` 을 지우세요. 목록과 원인은 `결과.md`.

## 산출물 (git 제외)

- `스크린샷/` — 07 장면별 스크린샷(`장면_너비.png`)
- `test-results/결과.json` — 결과 JSON, 실패 시 스크린샷·trace
