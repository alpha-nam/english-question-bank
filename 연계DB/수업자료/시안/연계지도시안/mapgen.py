# 연계 지도(회차 한 장짜리 지도) 시안용 생성 함수. 승인되면 생성기(build.py)로 옮긴다.
import csv
import html
import os
import re

CSV = '/mnt/project-files/연계DB/연계DB_통합_전체문항.csv'
DATA = '/mnt/project-files/연계DB/수업자료/문항데이터'

ROUNDS = [  # 폴더 이름, 헤더에 쓰는 이름, 시행 시기, 탭 이름
    ('2024.06', '2025학년도 6월 모의평가', '2024년 6월 시행', '2025학년도 6월'),
    ('2024.09', '2025학년도 9월 모의평가', '2024년 9월 시행', '2025학년도 9월'),
    ('2024.11', '2025학년도 수능', '2024년 11월 시행', '2025학년도 수능'),
    ('2025.06', '2026학년도 6월 모의평가', '2025년 6월 시행', '2026학년도 6월'),
    ('2025.09', '2026학년도 9월 모의평가', '2025년 9월 시행', '2026학년도 9월'),
    ('2025.11', '2026학년도 수능', '2025년 11월 시행', '2026학년도 수능'),
    ('2026.06', '2027학년도 6월 모의평가', '2026년 6월 시행', '2027학년도 6월'),
    ('2026.09', '2027학년도 9월 모의평가', '2026년 9월 시행', '2027학년도 9월'),
]
BOOK_TAG = {'수능특강 영어': '수특', '수능특강 영어듣기': '수특듣기', '수능특강 영어독해연습': '독해연습', '수능완성 영어': '수완'}
METHOD_TAG = {'소재만': '소재', '일부변형': '변형', '연계약함': '약함', '도표형식만': '도표', '인물만': '인물', '개념·유형만': '개념', '지문그대로': '원문'}
LISTEN_LAST = 17
LAST_NO = 45


def esc(s):
    return html.escape(s, quote=True)


def load_rows():
    """회차별로 문항 번호 1~45 칸마다 한 줄(연계 문항이면 내용, 아니면 None)을 만든다."""
    with open(CSV, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        cells = out.setdefault(r['시험'], {})
        m = re.fullmatch(r'(\d+)(?:~(\d+))?', r['문항'].strip())
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        for no in range(lo, hi + 1):
            cells[no] = r
    return out


def ready_numbers(round_id):
    d = os.path.join(DATA, round_id)
    if not os.path.isdir(d):
        return set()
    return {int(m.group(1)) for n in os.listdir(d) for m in [re.fullmatch(r'q(\d+)\.json', n)] if m}


def cells_html(n):
    return ('<span class="cells" role="img" aria-label="5점 중 %d점">' % n
            + ''.join('<span></span>' if i < n else '<span class="e"></span>' for i in range(5)) + '</span>')


def cell(no, r, ready, href):
    if r is None or r['연계방식'] == '비연계':
        return '<span class="mc none" title="%d번 · 독립 출제(교재와 연계되지 않음)"><b>%d</b><em>독립</em></span>' % (no, no)
    felt = int(r['학생체감'] or 0)
    method = r['연계방식']
    book = BOOK_TAG.get(r['교재'], r['교재'])
    tip = '%d번 · %s · %s %s쪽 · %s · 체감 %d' % (no, r['시험유형'], r['교재'], r['쪽'], method, felt)
    inner = '<b>%d</b><em>%s</em><span class="bk">%s</span>%s' % (no, esc(METHOD_TAG.get(method, method)), esc(book), cells_html(felt))
    if no in ready:
        return '<a class="mc lk on" href="%s#q%d" title="%s">%s</a>' % (href, no, esc(tip + ' · 수업 자료 있음'), inner)
    return '<span class="mc lk" title="%s">%s</span>' % (esc(tip + ' · 수업 자료 준비 중'), inner)


def stats(round_id, rows):
    cs = rows.get(round_id, {})
    seen = {}
    for no, r in cs.items():
        seen[no] = r
    linked = [no for no, r in seen.items() if r['연계방식'] != '비연계']
    methods = {}
    for no in linked:
        methods[seen[no]['연계방식']] = methods.get(seen[no]['연계방식'], 0) + 1
    felts = [int(seen[no]['학생체감']) for no in linked if seen[no]['학생체감'].isdigit()]
    return {'linked': len(linked), 'none': LAST_NO - len(linked), 'methods': methods,
            'felt': (sum(felts) / len(felts)) if felts else 0}


def map_slide(round_id, name, held, rows, href='', slide_id='map'):
    cs = rows.get(round_id, {})
    ready = ready_numbers(round_id)
    st = stats(round_id, rows)
    bands = []
    for title, lo, hi in (('듣기', 1, LISTEN_LAST), ('읽기', LISTEN_LAST + 1, LAST_NO)):
        n_link = sum(1 for no in range(lo, hi + 1) if cs.get(no) and cs[no]['연계방식'] != '비연계')
        grid = ''.join(cell(no, cs.get(no), ready, href) for no in range(lo, hi + 1))
        bands.append('<div class="band"><h3>%s <small>%d~%d번</small><span class="n">교재 연계 %d문항</span></h3><div class="mg">%s</div></div>'
                     % (title, lo, hi, n_link, grid))
    n_ready = len(ready & {n for n, r in cs.items() if r['연계방식'] != '비연계'})
    rd = '<span class="rd">수업 자료 <b>%d</b>문항</span>' % n_ready if n_ready else ''
    used = [m for m in METHOD_TAG if m in st['methods']]
    words = ' · '.join('<b>%s</b>=%s %d' % (METHOD_TAG[m], esc(m), st['methods'][m]) for m in used)
    return (
        '<section class="slide mapslide" id="%s" aria-label="연계 지도">\n'
        '  <div class="mh"><h2><span class="ic i-link" aria-hidden="true"></span>연계 지도</h2>'
        '<span class="rn">%s<small>%s</small></span>'
        '<p class="ms"><span>교재 연계 <b>%d</b>문항</span><span>독립 출제 <b>%d</b>문항</span>%s</p></div>\n'
        '  %s\n'
        '  <div class="mf"><span class="k"><i class="sw on"></i>수업 자료 있음(눌러서 열기)</span><span class="k"><i class="sw"></i>준비 중</span>'
        '<span class="k"><i class="sw none"></i>독립 출제(교재와 연계되지 않음)</span>'
        '<span class="k">체감 %s 교재를 공부한 학생이 본 적 있다고 느끼기 쉬운 정도</span>'
        '<span class="k wd">연계방식 ' + '%s' + '</span></div>\n'
        '</section>'
    ) % (slide_id, esc(name), esc(held), st['linked'], st['none'], rd,
         '\n  '.join(bands), cells_html(3), words)


MAP_CSS = '''
/* 연계 지도: 회차 첫 장. 칸 하나 = 시험 문항 하나(번호, 연계방식, 교재, 체감) */
.mapslide{gap:.8cqw;padding-top:2.4cqw;padding-bottom:2cqw}
.mh{display:flex;align-items:center;gap:1.4cqw;border-bottom:2px dashed var(--line);padding-bottom:.9cqw}
.mh h2{margin:0;display:flex;align-items:center;gap:.8cqw;font-size:2.7cqw;font-weight:700;white-space:nowrap}
.mh h2 .ic{--s:3.4cqw}
.mh .rn{font-size:1.9cqw;font-weight:500;white-space:nowrap}
.mh .rn small{font-size:1.25cqw;color:var(--sub);margin-left:.8cqw;font-weight:400}
.mh .ms{margin:0 0 0 auto;display:flex;gap:1.8cqw;font-size:1.45cqw;color:var(--sub);white-space:nowrap}
.mh .ms b{font-size:2.2cqw;color:var(--ink);margin:0 .2cqw}
.mh .ms .rd b{color:var(--warn)}
.band{display:flex;flex-direction:column;gap:.55cqw}
.band h3{margin:0;display:flex;align-items:baseline;gap:.8cqw;font-size:1.75cqw;font-weight:700}
.band h3 small{font-size:1.25cqw;font-weight:400;color:var(--sub)}
.band h3 .n{margin-left:auto;font-size:1.25cqw;font-weight:400;color:var(--sub)}
.mg{display:grid;grid-template-columns:repeat(14,minmax(0,1fr));gap:.6cqw}
.mc{display:flex;flex-direction:column;align-items:center;gap:.2cqw;padding:.45cqw .1cqw .55cqw;border-radius:.8cqw;border:1.5px solid transparent;color:var(--ink);text-decoration:none;text-align:center;line-height:1.2;min-width:0}
.mc b{font-size:2.5cqw;font-weight:700;line-height:1.1}
.mc em{font-style:normal;font-size:1.25cqw;font-weight:700;color:var(--warn)}
.mc .bk{font-size:1.25cqw;color:var(--sub);white-space:nowrap}
.mc .cells{margin-top:.25cqw;gap:.22cqw}.mc .cells span{width:.9cqw;height:.9cqw;border-radius:.22cqw}
.mc.lk{border:1.5px dashed rgba(255,185,140,.55)}
.mc.lk.on{border:2px solid var(--warn);background:var(--warn-soft)}
a.mc.on:hover,a.mc.on:focus-visible{background:rgba(255,185,140,.28);outline:none}
.mc.none{opacity:.38}
.mc.none em{color:var(--sub);font-weight:400}
.mf{margin-top:auto;display:flex;align-items:center;gap:.5cqw 1.8cqw;flex-wrap:wrap;font-size:1.25cqw;color:var(--sub)}
.mf .k{display:inline-flex;align-items:center;gap:.6cqw;white-space:nowrap}
.mf .wd{display:block;flex-basis:100%;white-space:normal;line-height:1.5}.mf .wd b{color:var(--warn);font-weight:700;margin-right:.1cqw}
.mf .sw{display:inline-block;width:2cqw;height:1.3cqw;border-radius:.4cqw;border:1.5px dashed rgba(255,185,140,.55)}
.mf .sw.on{border:2px solid var(--warn);background:var(--warn-soft)}
.mf .sw.none{border-color:transparent;background:rgba(243,241,230,.25)}
.mf .cells span{width:.9cqw;height:.9cqw;border-radius:.2cqw}
@media (max-width:700px){
  .mapslide{gap:12px}
  .mh{flex-wrap:wrap;gap:6px 10px}.mh h2{font-size:20px;gap:8px}.mh h2 .ic{--s:26px}.mh .rn{font-size:15px}.mh .rn small{font-size:12px;display:block;margin:0}
  .mh .ms{margin-left:0;width:100%;gap:4px 14px;font-size:13px;flex-wrap:wrap}.mh .ms b{font-size:16px}
  .band{gap:8px}.band h3{font-size:15px}.band h3 small,.band h3 .n{font-size:12px}
  .mg{grid-template-columns:repeat(5,minmax(0,1fr));gap:5px}
  .mc{border-radius:8px;padding:6px 2px 7px;gap:2px}.mc b{font-size:19px}.mc em,.mc .bk{font-size:11px}
  .mc .cells{gap:2px;margin-top:2px}.mc .cells span{width:7px;height:7px;border-radius:2px}
  .mf{font-size:12px;gap:6px 14px}.mf .k{white-space:normal;text-wrap:balance}.mf .sw{width:20px;height:13px;border-radius:4px}.mf .cells span{width:9px;height:9px;border-radius:2px}}
'''
