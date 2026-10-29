# 연계 지도 시안 만들기: (1) 회차 파일 첫 장 + 짧은 목차 줄, (2) 전체 첫 화면(회차 탭 8개)
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapgen as mg

HERE = os.path.dirname(os.path.abspath(__file__))
T = '/mnt/project-files/연계DB/수업자료/생성기/template/'
DECK = '/mnt/project-files/연계DB/수업자료/완성본/2026.09_파일럿.html'


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


rows = mg.load_rows()

# ---------- (1) 회차 파일: 19판에 지도 장과 짧은 목차 줄을 끼워 넣는다
deck = read(DECK)
name, held = '2027학년도 9월 모의평가', '2026년 9월 시행'
slide = mg.map_slide('2026.09', name, held, rows, href='', slide_id='map')
nav_old = re.search(r'<nav>.*?</nav>', deck, re.S).group(0)
nav_new = ('<nav class="cn"><b>%s 연계 분석</b><a href="#map">연계 지도</a>'
           '<a href="#q31">◀ 이전 문항</a><a href="#q25">다음 문항 ▶</a>'
           '<span class="legend"><mark>연계 단서</mark><span class="a">정답 근거</span></span></nav>') % name
deck2 = deck.replace(nav_old, nav_new + '\n\n' + slide)
deck2 = deck2.replace('</style>', mg.MAP_CSS + '</style>', 1)
deck2 = deck2.replace('<title>연계 분석 수업 시안</title>', '<title>연계 분석 수업 시안 (연계 지도)</title>', 1)
with open(os.path.join(HERE, 'slide_mock.html'), 'w', encoding='utf-8') as f:
    f.write(deck2)

# ---------- (2) 전체 첫 화면
INDEX_CSS = '''
.ix{max-width:1200px;margin:0 auto}
.ix h1{font-size:28px;margin:4px 0 4px;font-weight:700}
.ix .sub{color:var(--sub);margin:0 0 16px;font-size:15px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px}
.tabs button{font:inherit;font-size:14px;color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:7px 14px;cursor:pointer;display:inline-flex;align-items:center;gap:7px}
.tabs button:hover{border-color:var(--warn)}
.tabs button[aria-selected=true]{border-color:var(--warn);background:rgba(255,185,140,.18);font-weight:700}
.tabs .ok{font-size:11px;font-weight:700;color:var(--paper);background:var(--warn);border-radius:999px;padding:1px 7px}
.panel[hidden]{display:none}
.ph{display:flex;align-items:center;gap:10px 14px;flex-wrap:wrap;margin:0 0 12px}
.ph h2{margin:0;font-size:22px}
.ph small{color:var(--sub);font-size:14px}
.ph .acts{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
.btn{color:var(--ink);text-decoration:none;font-size:14px;font-weight:700;padding:8px 16px;border:1.5px solid var(--warn);border-radius:999px;background:rgba(255,185,140,.16)}
.btn:hover{background:rgba(255,185,140,.3)}
.btn.off{border-color:var(--line);background:none;color:var(--sub);font-weight:400;pointer-events:none}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:0;font-size:14px;color:var(--sub)}
.chips span{border:1px solid var(--line);border-radius:999px;padding:4px 12px}
.chips b{color:var(--ink)}
.ix .slide{margin-bottom:16px}
@media (max-width:700px){.ix h1{font-size:22px}.ix .sub{font-size:14px}.tabs button{font-size:14px;padding:8px 12px}.ph h2{font-size:19px}.ph .acts{margin-left:0;width:100%}.btn{flex:1;text-align:center}.chips{font-size:13px}}
'''
out = {'2026.09': ('2026.09_파일럿.html', '2026.09_파일럿.pdf')}
tabs, panels = [], []
for rid, nm, hd, tab in mg.ROUNDS:
    has = rid in out
    tabs.append('<button role="tab" data-r="%s" aria-selected="false">%s%s</button>'
                % (rid, tab, '<span class="ok">자료 있음</span>' if has else ''))
    st = mg.stats(rid, rows)
    meth = ''.join('<span>%s <b>%d</b></span>' % (k, v) for k, v in sorted(st['methods'].items(), key=lambda kv: -kv[1]))
    href = out[rid][0] if has else ''
    acts = ('<a class="btn" href="%s">수업 자료 열기</a><a class="btn" href="%s" download>PDF 받기</a>' % (out[rid][0], out[rid][1])
            if has else '<span class="btn off">수업 자료 준비 중</span>')
    smap = mg.map_slide(rid, nm, hd, rows, href=href, slide_id='map-' + rid)
    if not has:  # 준비된 자료가 없으면 칸은 눌리지 않는다(마크업은 같음)
        pass
    panels.append(
        '<section class="panel" data-r="%s" hidden>\n<div class="ph">'
        '<div class="chips"><span>교재 연계 <b>%d</b>문항</span><span>체감 평균 <b>%.1f</b></span></div><div class="acts">%s</div></div>\n%s\n</section>'
        % (rid, st['linked'], st['felt'], acts, smap))

idx = ''.join([
    '<title>연계 분석 수업 자료</title>\n', read(T + 'head.html'), '<style>\n', read(T + 'deck.css'), read(T + 'icons.css'),
    mg.MAP_CSS, INDEX_CSS, '</style>\n', read(T + 'chalk.js').rstrip('\n'), '\n\n',
    '<div class="ix">\n<h1>연계 분석 수업 자료</h1>\n<p class="sub">평가원 영어 6월·9월·수능 8회(2025~2027학년도) · 교재 연계 지도와 수업 자료</p>\n',
    '<div class="tabs" role="tablist">', ''.join(tabs), '</div>\n', '\n'.join(panels), '\n</div>\n\n',
    read(T + 'credit.html').rstrip('\n'), '\n\n<script>\n',
    "(function(){var tabs=[].slice.call(document.querySelectorAll('.tabs button')),ps=[].slice.call(document.querySelectorAll('.panel'));"
    "function show(id){tabs.forEach(function(t){t.setAttribute('aria-selected',t.dataset.r===id?'true':'false')});"
    "ps.forEach(function(p){p.hidden=p.dataset.r!==id});try{history.replaceState(null,'','#'+id)}catch(e){}}"
    "tabs.forEach(function(t){t.addEventListener('click',function(){show(t.dataset.r)})});"
    "var h=(location.hash||'').slice(1);show(tabs.some(function(t){return t.dataset.r===h})?h:'2026.09')})();\n</script>\n",
])
with open(os.path.join(HERE, 'index_mock.html'), 'w', encoding='utf-8') as f:
    f.write(idx)
print('ok', len(deck2), len(idx))
