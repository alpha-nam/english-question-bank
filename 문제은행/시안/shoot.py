"""장면 스크린샷 찍기: python shoot.py <html> <라벨> [장면들] [너비들]  → 검토/스크린샷/<라벨>/<장면>_<너비>.png"""
import os, shutil, subprocess, sys, tempfile, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
name, label = sys.argv[1], sys.argv[2]
scenes = (sys.argv[3] if len(sys.argv) > 3 else 'home,sheet,drawer,variant,mine,request,mock,hub,group').split(',')
widths = [int(x) for x in (sys.argv[4] if len(sys.argv) > 4 else '1440').split(',')]
_th = os.environ.get('QB_THEME')
base = 'http://127.0.0.1:8765/' + '/'.join(urllib.parse.quote(p) for p in ('문제은행', '시안', name))
out = os.path.join(HERE, '검토', '스크린샷', label)
os.makedirs(out, exist_ok=True)
for sc in scenes:
    for w in widths:
        h = 900 if w >= 900 else 844
        page = f'{base}?demo={sc}' + (f'&theme={_th}' if _th else '')
        url = page if w >= 600 else base.rsplit('/', 1)[0] + '/frame.html?w=%d&h=%d&src=%s' % (w, h, urllib.parse.quote(page, safe=''))
        prof = tempfile.mkdtemp(prefix='shot_')
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', f'--user-data-dir={prof}',
                        f'--window-size={max(w, 520)},{int(__import__('os').environ.get('QB_H', h))}', '--virtual-time-budget=7000', f'--screenshot={os.path.join(out, f"{sc}_{w}.png")}', url],
                       capture_output=True)
        shutil.rmtree(prof, ignore_errors=True)  # 임시 Chrome 프로필이 쌓여 디스크가 찼던 일 방지
print('done', out)
