# 화면 숫자 재기 도구 (2026-10-26 저장). Playwright 없이 PC의 크롬(헤드리스)만으로 슬라이드를 잰다.
#
# 무엇을 재나: 슬라이드마다 ① 칸을 넘치는지 ② 지문 글자가 실제로 몇 px로 보이는지(글자 맞춤 배수 포함)
# ③ 아래 남는 높이 ④ (--easy) 쉽게 보기 장의 카드가 아래 칸과 겹치는지.
#
# 사용 (연계DB 폴더 어디서든):
#   python -X utf8 -I 수업자료/생성기/tools/dev/measure_deck.py 2026.06            회차 정식 데이터로 만들어 재기
#   python -X utf8 -I 수업자료/생성기/tools/dev/measure_deck.py 2026.06 1920       창 폭 1920으로(기본 1280)
#   python -X utf8 -I 수업자료/생성기/tools/dev/measure_deck.py 2026.06 1280 --cand   후보(_시안후보/<회차>)를 얹어서
#   python -X utf8 -I 수업자료/생성기/tools/dev/measure_deck.py 2026.06 1280 --easy   쉽게 보기 장 겹침 검사
# 크롬 위치가 다르면 환경 변수 CHROME 에 chrome.exe 경로를 적는다. 사용 중인 크롬과 따로 도는 임시 프로필을 쓴다.
# 한계: 화면 캡처(screenshot)는 이 방식에서 빈 그림이 나와서 숫자로만 본다. 눈으로 볼 때는 앱 안 브라우저를 쓴다.
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))      # 연계DB 폴더
CHROME = os.environ.get('CHROME') or r'C:\Program Files\Google\Chrome\Application\chrome.exe'

pos = [a for a in sys.argv[1:] if not a.startswith('--')]
rnd = pos[0] if pos else '2026.09'
width = pos[1] if len(pos) > 1 else '1280'
use_cand, easy = '--cand' in sys.argv, '--easy' in sys.argv

tmp = tempfile.mkdtemp(prefix='measure_')
T = os.path.join(tmp, '연계DB')
os.makedirs(os.path.join(T, '수업자료'))
ign = shutil.ignore_patterns('백업*', '*백업*', 'fixture', 'node_modules')
shutil.copytree(os.path.join(ROOT, '수업자료', '생성기'), os.path.join(T, '수업자료', '생성기'), ignore=ign)
shutil.copytree(os.path.join(ROOT, '수업자료', '문항데이터'), os.path.join(T, '수업자료', '문항데이터'), ignore=ign)
shutil.copy(os.path.join(ROOT, '연계DB_통합_전체문항.csv'), T)
if use_cand:
    cand = os.path.join(ROOT, '수업자료', '문항데이터', '_시안후보', rnd)
    dest = os.path.join(T, '수업자료', '문항데이터', rnd)
    os.makedirs(dest, exist_ok=True)
    for f in os.listdir(cand):
        if f.startswith('q') and f.endswith('.json'):
            shutil.copy(os.path.join(cand, f), dest)
    if os.path.isdir(os.path.join(cand, '이미지')):                # 후보 그림(2026-10-26 추가)
        shutil.copytree(os.path.join(cand, '이미지'), os.path.join(dest, '이미지'), dirs_exist_ok=True)
deck = os.path.join(tmp, 'deck.html')
r = subprocess.run([sys.executable, '-X', 'utf8', '-I', 'build.py', rnd, '--out', deck],
                   cwd=os.path.join(T, '수업자료', '생성기'), capture_output=True, text=True, encoding='utf-8')
print((r.stdout + r.stderr).strip()[-200:])
if r.returncode:
    sys.exit(r.returncode)

JS_DECK = """<script>setTimeout(function(){var out=[];document.querySelectorAll('.slide').forEach(function(s,i){
var q=s.querySelector('.q');var o={i:i,id:s.id||'',ov:(s.scrollHeight>s.clientHeight+1||s.scrollWidth>s.clientWidth+1)};
if(q&&!q.classList.contains('twofig')){var p=s.querySelector('.passage,.speaker');var z=parseFloat(q.children[0].style.zoom||1);o.z=+z.toFixed(2);
if(p){var cs=getComputedStyle(p);o.f=+(parseFloat(cs.fontSize)*z).toFixed(1);var last=q.children[q.children.length-1].getBoundingClientRect();o.free=Math.round(q.getBoundingClientRect().bottom-last.bottom)}}
out.push(o)});document.title='R='+JSON.stringify(out)},4500)</script>"""
JS_EASY = """<script>setTimeout(function(){var out=[];document.querySelectorAll('.slide').forEach(function(s,i){var f=s.querySelector('.flow');if(!f)return;
var cards=[].slice.call(f.querySelectorAll('.ecard'));var sd=s.querySelector('.sd');
var cb=Math.max.apply(null,cards.map(function(c){return c.getBoundingClientRect().bottom}));var sdt=sd?sd.getBoundingClientRect().top:0;
var id='';var e=s;while(e&&!id){if(e.id)id=e.id;e=e.previousElementSibling}
out.push({i:i,q:id,es:getComputedStyle(f).getPropertyValue('--es').trim()||'-',cardOverSd:Math.round(cb-sdt),sOv:(s.scrollHeight>s.clientHeight+1)})});
document.title='R='+JSON.stringify(out)},4500)</script>"""

page = open(deck, encoding='utf-8').read()
open(os.path.join(tmp, 'm.html'), 'w', encoding='utf-8').write(page.replace('</body>', (JS_EASY if easy else JS_DECK) + '</body>'))
url = 'file:///' + os.path.join(tmp, 'm.html').replace('\\', '/')
out = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--user-data-dir=' + os.path.join(tmp, 'prof'),
                      '--window-size=%s,900' % width, '--virtual-time-budget=12000', '--dump-dom', url],
                     capture_output=True, text=True, encoding='utf-8', timeout=420).stdout
m = re.search(r'<title>R=(.*?)</title>', out, re.S)
if not m:
    print('측정 결과를 못 읽음(크롬이 사용 중이거나 경로가 다를 수 있음)')
    sys.exit(2)
d = json.loads(html.unescape(m.group(1)))
if easy:
    bad = [o for o in d if o['cardOverSd'] > 0 or o['sOv']]
    print('쉽게 보기 장 %d개, 겹침·넘침 %d개' % (len(d), len(bad)))
    for o in bad:
        print('  ', o)
    print('  카드 줄임 배수(--es):', [(o['q'], o['es']) for o in d if o['es'] not in ('-', '1')])
else:
    print('슬라이드 %d장, 넘침: %s' % (len(d), [o['i'] for o in d if o['ov']]))
    print('글자 17px 미만:', [(o['id'] or o['i'], o['f']) for o in d if 'f' in o and o['f'] < 17])
    print('글자 맞춤 배수 0.8 이하:', [(o['i'], o['z']) for o in d if 'z' in o and o['z'] <= 0.8])
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0)
