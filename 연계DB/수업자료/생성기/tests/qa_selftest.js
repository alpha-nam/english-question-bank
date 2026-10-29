// 자동 검사(tools/qa_deck.js, tools/qa_index.js)가 실제로 잘못된 곳을 잡아내는지 시험한다. "검사기를 검사"하는 것이다.
// 시안 파일에 일부러 문제를 하나씩 만들어 넣고, 기대한 오류가 나오는지 본다.
//   node qa_selftest.js [시안.html]      (기본: ../../완성본/2026.09_파일럿.html)
const {chromium} = require(require('child_process').execSync('npm root -g').toString().trim() + '/playwright');
const path = require('path');
const os = require('os');
const {execFileSync} = require('child_process');
const {inPage} = require('../tools/qa_deck.js');
const qaIndex = require('../tools/qa_index.js');
const fs = require('fs');
const skeleton = require('../tools/skeleton');
const file = path.resolve(process.argv[2] || path.join(__dirname, '..', '..', '완성본', '2026.09_파일럿.html'));
// 연계 지도 검사는 지도를 넣은 파일(데이터에서 바로 만든다)로 시험한다. 조각 파일은 '표준 모드가 아님' 시험용
const mapFile = path.join(os.tmpdir(), 'selftest_map_' + process.pid + '.html');
const fragFile = path.join(os.tmpdir(), 'selftest_frag_' + process.pid + '.html');
execFileSync('python3', ['-I', path.join(__dirname, '..', 'build.py'), '2026.09', '--map', '--out', mapFile]);
execFileSync('python3', ['-I', path.join(__dirname, '..', 'build.py'), '2026.09', '--fragment', '--out', fragFile]);
const indexFile = path.join(os.tmpdir(), 'selftest_index_' + process.pid + '.html');       // 전체 첫 화면 시험용(링크가 가리키는 파일은 쓰지 않는다)
execFileSync('python3', ['-I', path.join(__dirname, '..', 'build.py'), 'index', '--out', indexFile]);
// 덱은 Artifact 와 같은 틀(표준 모드)을 씌워 연다(tools/skeleton.js)
const PREP = {main: skeleton.prepared(file), map: skeleton.prepared(mapFile)};

// 각 시험: 이름, 쪽 안에서 도는 고장 내기(문자열), 기대하는 검사 이름(없으면 '오류 없음'), 기대 단계
const CASES = [
  {name: '고장 없음', break: '', expect: null},
  {name: '마지막 줄에 한 어절만 남는 글', expect: '마지막 줄 한 어절',
    break: `const e=document.querySelectorAll('.sum')[0];e.textContent='가나다라 마바사아 자차카타';e.style.cssText='width:180px;margin:0;text-align:left;font-size:20px'`},
  {name: '마지막 줄에 두 어절 이상 남는 글(잡으면 안 됨)', expect: null,
    break: `const e=document.querySelectorAll('.sum')[0];e.textContent='가나다라 마바사아 자차카타 하하';e.style.cssText='width:180px;margin:0;text-align:left;font-size:20px'`},
  {name: '헤더 왼쪽 글이 너무 길어 오른쪽 칸을 밀어냄', expect: '헤더 폭',
    break: `document.querySelector('.hd .chip em').textContent='2026학년도 대학수학능력시험 영어 영역 홀수형 매우 긴 이름'`},
  {name: '글자가 너무 작음', expect: '글자가 너무 작음',
    break: `document.querySelector('.stem').style.fontSize='8px'`},
  {name: '도표가 안 그려짐', expect: '도표',
    break: `const sv=document.querySelector('svg[id]');sv.innerHTML=''`},
  {name: 'id 가 겹침', expect: 'id 중복',
    break: `document.querySelectorAll('.slide:not(.mapslide)')[1].id='q31'`},
  {name: '목차 링크가 없는 곳을 가리킴', expect: '목차 링크',
    break: `document.querySelector('nav a').setAttribute('href','#없는곳')`},
  {name: '지문이 칸을 넘침', expect: '칸 안 넘침',
    break: `const p=document.querySelector('.passage p');p.innerHTML=p.innerHTML+' '+p.innerHTML+' '+p.innerHTML`},
  {name: '정답 줄이 없음', expect: '정답 표시',
    break: `document.querySelector('.foot').remove()`},
  {name: '문항 유형 칸이 없음', expect: '헤더',
    break: `document.querySelector('.kd .ty').remove()`},
  // ---- 연계 지도를 넣은 파일(deck: 'map')
  {deck: 'map', name: '[지도 파일] 고장 없음(지도 장은 5장 묶음·헤더 검사에서 빠진다)', break: '', expect: null},
  {deck: 'map', name: '[지도] 칸이 하나 빠짐', expect: '지도 칸 수',
    break: `document.querySelector('.mapslide .mc:last-child').remove()`},
  {deck: 'map', name: '[지도] 눌리는 칸이 없는 곳을 가리킴', expect: '지도 링크',
    break: `document.querySelector('a.mc.on').setAttribute('href','#q99')`},
  {deck: 'map', name: '[지도] 문항이 있는데 눌리는 칸이 아님', expect: '지도에 없는 문항',
    break: `const a=document.querySelector('a.mc.on'),sp=document.createElement('span');sp.className='mc lk';sp.innerHTML=a.innerHTML;a.replaceWith(sp)`},
  {deck: 'map', name: '[지도] 머리 줄 숫자가 칸과 다름', expect: '지도 숫자',
    break: `document.querySelector('.mh .ms b').textContent='24'`},
  {deck: 'map', name: '[지도] 칸 안 글자가 넘침', expect: '지도 칸 글자 넘침',
    break: `document.querySelector('.mc .bk').textContent='수능특강영어독해연습긴이름'`},
  {deck: 'map', name: '[지도] 목차 줄이 이동한 장 위를 가림', expect: '목차 줄이 이동한 장 위를 가림',
    break: `document.querySelector('nav').style.height='220px'`},
  {deck: 'raw', name: '[모드] 문서 형식 선언 없이 열면 괴상 모드', break: '', expect: '표준 모드가 아님'},
];

// 전체 첫 화면(build.py index 로 만든 파일)의 쪽 안 검사. phase: 'once' 구조 검사, 'tab' 열린 탭의 지도·칸 검사, 없으면 둘 다
const INDEX_CASES = [
  {name: '[첫 화면] 고장 없음', break: '', expect: null},
  {name: '[첫 화면] 탭 순서가 옛 회차부터', expect: '탭 순서', phase: 'once',
    break: `const t=document.querySelector('.tabs');[...t.children].reverse().forEach(c=>t.appendChild(c))`},
  {name: '[첫 화면] 패널 두 개가 함께 보임', expect: '탭 패널', phase: 'once',
    break: `document.querySelectorAll('[role=tabpanel]')[1].hidden=false`},
  {name: '[첫 화면] 탭과 패널 연결이 끊김', expect: '탭 연결', phase: 'once',
    break: `document.querySelector('.tabs [role=tab]').setAttribute('aria-controls','없는패널')`},
  {name: '[첫 화면] 자료 있는 회차의 배지가 없음', expect: '자료 있음 표시', phase: 'once',
    break: `document.querySelector('.tabs .ok').remove()`},
  {name: '[첫 화면] 맨 왼쪽이 아닌 탭이 열려 있음', expect: '처음 열린 탭', phase: 'once',
    break: `const T=[...document.querySelectorAll('.tabs [role=tab]')],P=[...document.querySelectorAll('[role=tabpanel]')];T[0].setAttribute('aria-selected','false');P[0].hidden=true;T[1].setAttribute('aria-selected','true');P[1].hidden=false`},
  {name: '[첫 화면] id 가 겹침', expect: 'id 중복', phase: 'once',
    break: `document.querySelectorAll('[role=tabpanel]')[1].id=document.querySelectorAll('[role=tabpanel]')[0].id`},
  {name: '[첫 화면] 지도 칸이 하나 빠짐', expect: '지도 칸 수', phase: 'tab',
    break: `document.querySelector('[role=tabpanel]:not([hidden]) .mc:last-child').remove()`},
  {name: '[첫 화면] 지도 머리 줄 숫자가 칸과 다름', expect: '지도 숫자', phase: 'tab',
    break: `document.querySelector('[role=tabpanel]:not([hidden]) .mh .ms b').textContent='24'`},
  {name: '[첫 화면] 체감 평균 칩이 칸과 다름', expect: '칩 숫자', phase: 'tab',
    break: `document.querySelector('[role=tabpanel]:not([hidden]) .chips b:last-child').textContent='4.9'`},
  {name: '[첫 화면] 수업 자료 열기 단추가 없음', expect: '단추', phase: 'tab',
    break: `document.querySelector('[role=tabpanel]:not([hidden]) a.btn').remove()`},
  {name: '[첫 화면] 가로로 넘침', expect: '가로 넘침', phase: 'tab',
    break: `document.querySelector('.ix').style.minWidth='2000px'`},
  {name: '[첫 화면] 지도 칸 안 글자가 넘침', expect: '지도 칸 글자 넘침', phase: 'tab',
    break: `document.querySelector('[role=tabpanel]:not([hidden]) .mc .bk').textContent='수능특강영어독해연습긴이름'`},
];
// 링크가 가리키는 파일과 문항(쪽 밖 검사). data 는 고장 낸 링크 정보를 만든다
const LINK_CASES = [
  {name: '[첫 화면 링크] 고장 없음', expect: null, data: g => g},
  {name: '[첫 화면 링크] 없는 파일을 가리킴', expect: '링크 파일 없음', data: g => ({hrefs: g.hrefs.concat('없는파일.html'), panels: g.panels})},
  {name: '[첫 화면 링크] 덱 파일에 없는 문항을 가리킴', expect: '링크 안 id 없음', data: g => ({hrefs: g.hrefs.concat('2026.09_파일럿.html#q99'), panels: g.panels})},
  {name: '[첫 화면 링크] 덱 파일의 문항이 지도에서 빠짐', expect: '지도에 없는 문항',
    data: g => ({hrefs: g.hrefs, panels: [Object.assign({}, g.panels[0], {on: g.panels[0].on.slice(0, 2)})]})},
];
// 탭 키보드와 주소 동작(tools/qa_index.js 의 interact). from→to 로 첫 화면 스크립트를 고장 낸다
const KEY_CASES = [
  {name: '[첫 화면 키보드] 고장 없음', expect: null},
  {name: '[첫 화면 키보드] 화살표 키가 듣지 않음', expect: '탭 동작', from: "'keydown'", to: "'keydownX'"},
  {name: '[첫 화면 키보드] 맨 왼쪽에서 ← 가 맨 오른쪽으로 돌아가지 않음(실제로 있었던 오류)', expect: '탭 동작', from: "k==='ArrowLeft'?i-1", to: "k==='ArrowLeft'&&i>0?i-1"},
  {name: '[첫 화면 키보드] 탭을 눌러도 주소 끝이 안 바뀜', expect: '탭 동작', from: "try{history.replaceState(null,'','#'+r)}catch(e){}", to: ''},
  {name: '[첫 화면 키보드] 주소 끝 #회차 로 열어도 안 열림', expect: '탭 동작', from: 'window.addEventListener(\'hashchange\',fromHash);fromHash()', to: 'window.addEventListener(\'hashchange\',fromHash)'},
  {name: '[첫 화면 키보드] 없는 회차 이름이면 패널이 모두 사라짐', expect: '탭 동작', from: 'if(T.some(function(t){return id(t)===h}))show(h)', to: 'show(h)'},
];

(async () => {
  const browser = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
  let bad = 0;
  for (const c of CASES) {
    const pg = await browser.newPage({viewport: {width: 1300, height: 800}});
    await pg.goto('file://' + (c.deck === 'raw' ? fragFile : (c.deck === 'map' ? PREP.map : PREP.main).file));
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(2000);
    if (c.break) { await pg.evaluate(c.break); await pg.evaluate(() => fit()); await pg.waitForTimeout(300); }
    const r = await pg.evaluate(`(${inPage.toString()})(${JSON.stringify({once: true, orphanLevel: 'error'})})`);
    await pg.close();
    const errs = r.filter(f => f.level === 'error');
    const ok = c.expect === null ? errs.length === 0 : errs.some(f => f.check === c.expect);
    if (!ok) bad++;
    console.log((ok ? '통과 ' : '실패 ') + c.name + (ok ? '' : '  → 기대: ' + (c.expect || '오류 없음') + ', 실제 오류: ' + JSON.stringify(errs.map(f => f.check + ' ' + f.detail).slice(0, 4))));
  }
  // ---- 전체 첫 화면 검사기(tools/qa_index.js)
  const report = (c, ok, errs) => {
    if (!ok) bad++;
    console.log((ok ? '통과 ' : '실패 ') + c.name + (ok ? '' : '  → 기대: ' + (c.expect || '오류 없음') + ', 실제 오류: ' + JSON.stringify(errs.map(f => f.check + ' ' + f.detail).slice(0, 4))));
  };
  for (const c of INDEX_CASES) {
    const pg = await browser.newPage({viewport: {width: 1300, height: 800}});
    await pg.goto('file://' + indexFile);
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(800);
    if (c.break) await pg.evaluate(c.break);
    const rid = await pg.evaluate(() => document.querySelector('.tabs [role=tab]').dataset.r);
    let errs = [];
    if (c.phase !== 'tab') errs = errs.concat((await pg.evaluate(`(${qaIndex.inPageOnce.toString()})()`)).findings);
    if (c.phase !== 'once') errs = errs.concat(await pg.evaluate(`(${qaIndex.inPageTab.toString()})(${JSON.stringify({rid})})`));
    await pg.close();
    errs = errs.filter(f => f.level === 'error');
    report(c, c.expect === null ? errs.length === 0 : errs.some(f => f.check === c.expect), errs);
  }
  // 링크가 가리키는 파일과 문항: 이 시험은 실제 완성본 폴더(덱 파일이 있는 곳) 기준으로 본다
  const realIndex = path.join(path.dirname(file), 'index.html');
  const good = {hrefs: ['2026.09_파일럿.html', '2026.09_파일럿.pdf', '2026.09_파일럿.html#q3'], panels: [{rid: '2026.09', open: '2026.09_파일럿.html', pdf: '2026.09_파일럿.pdf', on: ['2026.09_파일럿.html#q3', '2026.09_파일럿.html#q25', '2026.09_파일럿.html#q31']}]};
  for (const c of LINK_CASES) {
    const errs = qaIndex.checkLinks(realIndex, c.data(good));
    report(c, c.expect === null ? errs.length === 0 : errs.some(f => f.check === c.expect), errs);
  }
  // 탭 키보드와 주소 동작: 첫 화면 파일의 스크립트를 일부러 고장 낸 복사본으로 시험한다
  const html = fs.readFileSync(indexFile, 'utf8');
  for (const c of KEY_CASES) {
    const f = path.join(os.tmpdir(), 'selftest_index_js_' + process.pid + '.html');
    const broken = c.from ? html.replace(c.from, c.to) : html;
    if (c.from && broken === html) { bad++; console.log('실패 ' + c.name + '  → 고장 낼 글을 파일에서 못 찾음: ' + c.from); continue; }
    fs.writeFileSync(f, broken);
    const errs = [];
    await qaIndex.interact(browser, f, errs);
    fs.unlinkSync(f);
    report(c, c.expect === null ? errs.length === 0 : errs.some(e => e.check === c.expect), errs);
  }
  await browser.close();
  PREP.main.done(); PREP.map.done();
  try { fs.unlinkSync(indexFile); } catch (e) { /* 이미 없음 */ }
  const total = CASES.length + INDEX_CASES.length + LINK_CASES.length + KEY_CASES.length;
  console.log(bad ? '검사기 시험 실패 ' + bad + '건' : '검사기 시험 통과 (' + total + '건)');
  process.exit(bad ? 1 : 0);
})();
