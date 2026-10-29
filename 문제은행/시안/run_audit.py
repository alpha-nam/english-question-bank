"""화면 자동 감사 실행기: 헤드리스 Chrome 으로 장면×너비를 열어 audit.js 결과를 모은다.
사용: python -X utf8 -I run_audit.py <html 이름> <라벨> [장면 쉼표목록] [너비 쉼표목록]
결과: 검토/감사기록.jsonl 에 한 줄 추가, 화면에 요약 표."""
import html, json, os, re, shutil, subprocess, sys, tempfile, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
name, label = sys.argv[1], sys.argv[2]
scenes = (sys.argv[3] if len(sys.argv) > 3 else 'home,sheet,drawer,variant,mine,request').split(',')
widths = [int(x) for x in (sys.argv[4] if len(sys.argv) > 4 else '1440,1024,768,390').split(',')]
_th = os.environ.get('QB_THEME')
base = 'http://127.0.0.1:8765/' + '/'.join(urllib.parse.quote(p) for p in ('문제은행', '시안', name))
rows = []
for sc in scenes:
    for w in widths:
        page = f'{base}?demo={sc}&audit=1' + (f'&theme={_th}' if _th else '')
        url = page if w >= 600 else base.rsplit('/', 1)[0] + '/frame.html?w=%d&h=844&src=%s' % (w, urllib.parse.quote(page, safe=''))
        prof = tempfile.mkdtemp(prefix='aud_')
        r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-first-run', f'--user-data-dir={prof}', f'--window-size={max(w, 520)},900', '--virtual-time-budget=7000', '--dump-dom', url],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        shutil.rmtree(prof, ignore_errors=True)  # 임시 프로필 정리
        m = re.search(r'<pre id="__audit">(.*?)</pre>', r.stdout, re.S)
        if not m:
            rows.append({'scene': sc, 'w': w, 'error': 'audit 결과 없음'})
            continue
        d = json.loads(html.unescape(m.group(1)))
        d['scene'] = sc
        rows.append(d)
rec = {'label': label, 'file': name, 'rows': rows}
with open(os.path.join(HERE, '검토', '감사기록.jsonl'), 'a', encoding='utf-8') as f:
    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
tot = {'contrast_n': 0, 'contrast_fail': 0, 'small12': 0, 'tn': 0, 't24': 0, 't44': 0, 'gn': 0, 'goff': 0, 'mis': 0, 'gaps': 0, 'hscroll': 0, 'overflow': 0}
for d in rows:
    if 'error' in d:
        print('오류', d)
        continue
    tot['contrast_n'] += d['contrast']['n']; tot['contrast_fail'] += d['contrast']['fail']; tot['small12'] += d['sizes']['under12']
    tot['tn'] += d['targets']['n']; tot['t24'] += d['targets']['under24']; tot['t44'] += d['targets']['under44']
    tot['gn'] += d['grid']['n']; tot['goff'] += d['grid']['off']; tot['hscroll'] += d['hscroll']; tot['overflow'] += len(d['overflow'])
    for k, v in d['align'].items():
        if isinstance(v, dict):
            tot['mis'] += v.get('misaligned_rows', 0); tot['gaps'] += v.get('uneven_gap_rows', 0)
print(label, json.dumps({
    '대비 실패 %': round(tot['contrast_fail'] / max(tot['contrast_n'], 1) * 100, 1), '12px 미만 글자': tot['small12'],
    '눌리는 곳 24px 미만': tot['t24'], '44px 미만 %': round(tot['t44'] / max(tot['tn'], 1) * 100, 1),
    '4px 격자 벗어난 %': round(tot['goff'] / max(tot['gn'], 1) * 100, 1), '같은 줄 어긋남': tot['mis'], '간격 불균일 줄': tot['gaps'],
    '가로 스크롤 장면': tot['hscroll'], '잘림 요소': tot['overflow']}, ensure_ascii=False))
