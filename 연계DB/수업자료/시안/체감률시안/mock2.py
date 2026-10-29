# 체감 표시 3가지(네모 칸 / 체감률 숫자 / 체감률 숫자 + 막대)를 지도 칸과 비교 장 헤더에 적용한 시안 HTML 3개
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapgen as mg

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = '/mnt/project-files/연계DB/수업자료/완성본/2026.09_파일럿.html'
DB_FELT = [2, 2, 3]  # 31번, 3번, 25번의 DB 값(31번은 덱에 1로 들어가 있었음)

HDR_CSS = '''
.fl .pc{font-style:normal;color:var(--felt);font-size:1.55cqw}
.fl .fb{display:inline-block;width:4.2cqw;height:.6cqw;border-radius:99px;background:rgba(243,241,230,.25);overflow:hidden}
.fl .fb::after{content:"";display:block;height:100%;width:var(--p);background:var(--felt)}
@media (max-width:700px){.fl .pc{font-size:15px}.fl .fb{width:44px;height:7px}}
'''

FL = re.compile(r'<span class="fl"><i>체감</i><span class="cells" role="img" aria-label="5점 중 \d점">(?:<span(?: class="e")?></span>){5}</span></span>')


def header_felt(n, style):
    if style == 'sq':
        return '<span class="fl"><i>체감</i>%s</span>' % mg.cells_html(n)
    pct = n * 20
    out = '<span class="fl" role="img" aria-label="체감률 %d%%"><i>체감률</i><em class="pc">%d%%</em>' % (pct, pct)
    return out + '</span>'


with open(DECK, encoding='utf-8') as f:
    deck = f.read()
rows = mg.load_rows()
name, held = '2027학년도 9월 모의평가', '2026년 9월 시행'
nav_old = re.search(r'<nav>.*?</nav>', deck, re.S).group(0)
nav_new = ('<nav class="cn"><b>%s 연계 분석</b><a href="#map">연계 지도</a>'
           '<a href="#q31">◀ 이전 문항</a><a href="#q25">다음 문항 ▶</a>'
           '<span class="legend"><mark>연계 단서</mark><span class="a">정답 근거</span></span></nav>') % name

for style in ('sq', 'pct', 'bar'):
    mg.STYLE = style
    slide = mg.map_slide('2026.09', name, held, rows, href='', slide_id='map')
    it = iter(DB_FELT)
    d2 = FL.sub(lambda m: header_felt(next(it), style), deck)
    assert next(it, None) is None, '비교 장 헤더 3개를 모두 바꿔야 한다'
    d2 = d2.replace(nav_old, nav_new + '\n\n' + slide)
    d2 = d2.replace('</style>', mg.MAP_CSS + HDR_CSS + '</style>', 1)
    d2 = d2.replace('<title>연계 분석 수업 시안</title>', '<title>연계 분석 수업 시안 (체감 %s)</title>' % style, 1)
    with open(os.path.join(HERE, 'v_%s.html' % style), 'w', encoding='utf-8') as f:
        f.write(d2)
    print(style, len(d2), d2.count('class="fl"'))
