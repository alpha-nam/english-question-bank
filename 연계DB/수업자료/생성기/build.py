#!/usr/bin/env python3
"""연계 분석 수업 자료 생성기.

문항 데이터(JSON) + 틀(template/) → 수업용 HTML 한 파일(문항마다 5장).
  python3 build.py 2026.09            # ../완성본/ 에 회차 파일을 만든다(문서 형식 선언이 있는 독립 파일: 더블클릭으로 열 수 있다)
  python3 build.py 2026.09 --fragment # Artifact 에 올릴 조각으로 만든다(문서 형식 선언·head·body 없음. Artifact 가 틀을 씌운다)
  python3 build.py 2026.09 --out 경로  # 다른 곳에 만든다
  python3 build.py 2026.09 --check    # 데이터만 검사한다(파일은 만들지 않음)
  python3 build.py 2026.09 --map      # 연계 지도 장을 맨 앞에 넣는다(round.json 에 "map": true 를 적어 두면 늘 넣는다. --no-map 은 뺀다)
  python3 build.py index              # ../완성본/index.html : 전체 첫 화면(회차 탭마다 연계 지도와 수업 자료·PDF 단추. 탭은 최근 회차가 왼쪽).
                                      #   문항데이터/회차목록.json 과 CSV 에서 만든다. --out, --fragment, --check 는 회차 파일과 같다

데이터 모양과 표기법은 README.md. 틀(template/)의 글은 18판 시안에서 그대로 떼어 온 것이므로
손으로 고치면 모든 회차에 퍼진다. 고치면 tests/test_build.py 로 기준본과 비교해 본다.
"""
import base64
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, 'template')
DATA = os.path.join(HERE, '..', '문항데이터')
OUT = os.path.join(HERE, '..', '완성본')
LINK_CSV = os.path.join(HERE, '..', '..', '연계DB_통합_전체문항.csv')   # 연계 지도의 재료이자 문항 데이터와 맞춰 볼 DB

CIRC = '①②③④⑤'
KINDS = {'exam': '시험 문항', 'book': '교재 원문항', 'compare': '비교', 'easy': '쉽게 보기', 'teacher': '교사 분석'}
FIG_H, FIG_H_COMPACT = 440, 300          # 도표 그림 높이(문항 장, 비교 장)
BOOK_TAG = {'수능특강 영어': '수특', '수능특강 영어듣기': '수특듣기', '수능특강 영어독해연습': '독해연습', '수능완성 영어': '수완'}
METHOD_TAG = {'소재만': '소재', '일부변형': '변형', '연계약함': '약함', '도표형식만': '도표', '인물만': '인물', '개념·유형만': '개념', '지문그대로': '원문'}
LISTEN_LAST, LAST_NO = 17, 45            # 지도의 듣기 1~17번, 읽기 18~45번
COMPACT_NAV_OVER = 8                     # 문항이 이보다 많은 회차는 목차 줄을 '연계 지도 · 이전 문항 · 다음 문항'으로 줄인다


class BuildError(Exception):
    pass


# ---------- 글 표기 -> HTML ----------
# 데이터 글에서 쓸 수 있는 표기: <mark> <b> <u> <ev>(정답 근거 물결 밑줄) <blank/>(빈칸 줄) <br>. 그 밖의 <, >, & 는 그냥 글자.
_TOK = re.compile(r'<(/?)(mark|b|u|ev)>|<(blank|br)\s*/?>')
_OPEN = {'mark': '<mark>', 'b': '<b>', 'u': '<u>', 'ev': '<span class="a">'}
_CLOSE = {'mark': '</mark>', 'b': '</b>', 'u': '</u>', 'ev': '</span>'}


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def esc_attr(s):
    return esc(s).replace('"', '&quot;')


def mk(s, where=''):
    if not isinstance(s, str):
        raise BuildError('%s: 글이어야 하는 자리에 %r' % (where, s))
    out, stack, pos = [], [], 0
    for m in _TOK.finditer(s):
        out.append(esc(s[pos:m.start()]))
        pos = m.end()
        if m.group(3):
            out.append('<span class="blk"></span>' if m.group(3) == 'blank' else '<br>')
        elif not m.group(1):
            stack.append(m.group(2))
            out.append(_OPEN[m.group(2)])
        else:
            if not stack or stack[-1] != m.group(2):
                raise BuildError('%s: </%s> 의 짝이 없음: %s' % (where, m.group(2), s[:50]))
            stack.pop()
            out.append(_CLOSE[m.group(2)])
    out.append(esc(s[pos:]))
    if stack:
        raise BuildError('%s: <%s> 를 닫지 않음: %s' % (where, stack[-1], s[:50]))
    return ''.join(out)


# ---------- 조각 ----------
def read_tpl(name):
    with open(os.path.join(TPL, name), encoding='utf-8') as f:
        return f.read()


def felt_cells(n):
    """체감 n/5: 채운 칸 n개와 빈 칸 5-n개(스크린 리더에는 '5점 중 n점')"""
    return '<span class="cells" role="img" aria-label="5점 중 %d점">%s</span>' % (
        n, ''.join('<span></span>' if i < n else '<span class="e"></span>' for i in range(5)))


def covers(q):
    """한 지문에 문항이 여러 개인 장문(43~45번)은 q43.json 하나가 44·45번까지 맡는다. 맡는 다른 번호 목록(없으면 빈 목록)"""
    return list(q.get('covers') or [])


def exam_label(q):
    """시험 번호 표시: 43번이 44·45번까지 맡으면 '43~45'"""
    return '%d~%d' % (q['no'], max(covers(q))) if covers(q) else str(q['no'])


def ready_alias(qs):
    """수업 자료가 있는 시험 번호 집합과, 다른 문항 장이 대신 맡는 번호의 이동 대상 {44: 43, 45: 43}"""
    ready, alias = set(), {}
    for q in qs:
        ready.add(q['no'])
        for c in covers(q):
            ready.add(c)
            alias[c] = q['no']
    return ready, alias


def chip(rnd, q, who, state):
    cls = 'chip %s%s' % (who, (' ' + state) if state else '')
    if who == 'x':
        icon, label, em, small, num = 'memo', '시험', rnd['name'], rnd['held'], exam_label(q)
    else:
        b = q['meta']['book']
        icon, label, em, small, num = 'books', '교재', '%s %d쪽' % (b['name'], b['page']), b['unit'], b['no']
    return ('<span class="%s"><span class="ic i-%s" aria-hidden="true"></span><i>%s</i>'
            '<span class="tx"><em>%s</em><small>%s</small></span><b>%s번</b></span>'
            % (cls, icon, label, esc(em), esc(small), num))


def link_mark(q):
    return ('<span class="lk"><span class="ic i-link" aria-hidden="true"></span><small>%s</small></span>'
            % esc(q['meta']['link']['label']))


def kd_sub(q, kind):
    """헤더 오른쪽의 유형 글. 듣기 문항이면 시험 문항·교재 원문항·쉽게 보기 장에 '듣기/읽기'를 덧붙인다(18판 그대로)."""
    ex, bk = q['meta']['exam'], q['meta']['book']
    listening = ex.get('mode') == '듣기'
    if kind == 'book':
        return bk['type'] + (' · 읽기' if listening else '')
    if kind in ('exam', 'easy'):
        return ex['type'] + (' · 듣기' if listening else '')
    return ex['type']


def header(rnd, q, kind):
    # 지금 보는 쪽(on)은 왼쪽에서 진하게, 다른 쪽(off)은 오른쪽에서 흐리게. 비교·쉽게 보기·교사 분석은 둘 다 같은 세기
    x_on, x_off = chip(rnd, q, 'x', 'on'), chip(rnd, q, 'x', 'off')
    b_on, b_off = chip(rnd, q, 'b', 'on'), chip(rnd, q, 'b', 'off')
    x, b = chip(rnd, q, 'x', ''), chip(rnd, q, 'b', '')
    lk = link_mark(q)
    first, last = {'exam': (x_on, b_off), 'book': (b_on, x_off), 'compare': (x, b),
                   'easy': (b, x), 'teacher': (x, b)}[kind]
    if kind == 'compare':
        kd = '<span class="kd"><b>비교<span class="fl"><i>체감</i>%s</span></b><span class="ty">%s</span></span>' % (
            felt_cells(q['meta']['link']['felt']), esc(kd_sub(q, kind)))
    else:
        kd = '<span class="kd"><b>%s</b><span class="ty">%s</span></span>' % (KINDS[kind], esc(kd_sub(q, kind)))
    return ('  <div class="hd" role="group" aria-label="시험 %d번, 교재 %d번 — %s">%s%s%s%s</div>'
            % (q['no'], q['meta']['book']['no'], KINDS[kind], first, lk, last, kd))


def section(cls, sid, parts):
    return '<section class="%s"%s>\n%s\n</section>' % (cls, (' id="%s"' % sid) if sid else '', '\n'.join(parts))


def answer_glyph(n):
    return CIRC[n - 1]


def foot(q, which):
    note = q['analysis'].get('answer_note', {}).get(which, '')
    n = q['meta'][which]['answer']
    return '  <div class="foot"><div class="ans">정답 %s%s</div></div>' % (
        answer_glyph(n), (' · ' + esc(note)) if note else '')


def stem(text_block, no, where):
    t = mk(text_block['stem'], where + '.stem')
    pts = text_block.get('points')
    return '<p class="stem">%d. %s%s</p>' % (no, t, ('&nbsp;<small>[%d점]</small>' % pts) if pts else '')


def paragraph(p, where):
    fn = p.get('fn')
    return '<p>%s%s</p>' % (mk(p['t'], where), ('<span class="fn">%s</span>' % ' &nbsp;'.join(esc(f) for f in fn)) if fn else '')


def choices_ol(ch, answer, where, multiline=False):
    items = ch['items']
    if not 1 <= answer <= len(items):
        raise BuildError('%s: 정답 번호 %s 가 선택지 수(%d)를 벗어남' % (where, answer, len(items)))
    cls = 'ch' + (' en' if ch.get('lang') == 'en' else '') + (' col%d' % ch['cols'] if ch.get('cols') else '')
    lis = ['<li%s><i>%s</i>%s</li>' % (' class="ok"' if i + 1 == answer else '', CIRC[i], mk(t, '%s.choices[%d]' % (where, i)))
           for i, t in enumerate(items)]
    if multiline:
        return '<ol class="%s">\n        %s</ol>' % (cls, '\n        '.join(lis))
    return '<ol class="%s">%s</ol>' % (cls, ''.join(lis))


def fig_ids(q):
    return {k: 'c%d-%s' % (q['no'], k) for k in ('exam', 'book', 'exam2', 'book2')}


FIG_KINDS = ('figure', 'picture', 'table')          # 옆 배치(그림·표 + 글) 본문 종류. figure=그래프(SVG), picture=그림 이미지, table=표(데이터로 다시 그림)
IMAGE_MIME = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'webp': 'webp'}
IMAGES = {}                                         # 이번에 만드는 파일에 넣을 그림 {열쇠: data URI}. build_html 이 시작할 때 비운다


def image_path(q, name):
    return os.path.join(DATA, q['round'], '이미지', name)


def image_uri(q, name):
    """그림 이미지를 글 안에 넣는 주소(data URI)로 바꾼다. 파일 하나로 열리는 결과물을 지키려는 것"""
    path = image_path(q, name)
    if not os.path.isfile(path):
        raise BuildError('%s: 그림 파일이 없음: %s' % (q['id'], path))
    mime = IMAGE_MIME.get(os.path.splitext(name)[1].lower().lstrip('.'))
    if not mime:
        raise BuildError('%s: 그림 파일 종류를 모름(jpg, png, webp만): %s' % (q['id'], name))
    with open(path, 'rb') as f:
        return 'data:image/%s;base64,%s' % (mime, base64.b64encode(f.read()).decode('ascii'))


def table_html(body, where, compact=False):
    """표: head(머리 칸 목록), rows(행 목록), title(제목), numbered(왼쪽에 ①~⑤), hl(눈에 띄게 할 행 번호 목록, 0부터)"""
    th = ''.join('<th>%s</th>' % mk(h, where + '.head') for h in body['head'])
    if body.get('numbered'):
        th = '<th class="n"></th>' + th
    trs = []
    for i, r in enumerate(body['rows']):
        tds = ''.join('<td>%s</td>' % mk(c, '%s.rows[%d]' % (where, i)) for c in r)
        if body.get('numbered'):
            tds = '<td class="n">%s</td>' % CIRC[i] + tds
        trs.append('<tr%s>%s</tr>' % (' class="hl"' if i in body.get('hl', []) else '', tds))
    cap = '<caption>%s</caption>' % mk(body['title'], where + '.title') if body.get('title') else ''
    return '<table class="tbl%s" aria-label="%s">%s<thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (
        ' c' if compact else '', esc(body.get('alt', '표')), cap, th, ''.join(trs))


def fig_inner(q, which, body, fig_id, h, where, compact=False):
    """옆 배치 장(문항 장, 비교 장)의 그림 자리 안쪽: 그래프(SVG 자리), 그림 이미지, 표"""
    if body['kind'] == 'figure':
        return '<svg id="%s" viewBox="0 0 580 %d" role="img" aria-label="%s"></svg>' % (fig_id, h, esc(body['alt']))
    if body['kind'] == 'picture':
        key = '%s/%s' % (q['round'], body['image'])
        if key not in IMAGES:                                  # 같은 그림이 문항 장과 비교 장에 두 번 나와도 파일 안에는 한 번만 넣는다
            IMAGES[key] = image_uri(q, body['image'])
        return '<img class="pic" data-img="%s" alt="%s">' % (esc_attr(key), esc(body['alt']))
    return table_html(body, where + '.table', compact)


# ---------- 5장 ----------
def slide_text(rnd, q, which, first):
    """시험 문항 장(which=exam) 또는 교재 원문항 장(which=book)"""
    tb = q['text'][which]
    body = tb['body']
    no = q['no'] if which == 'exam' else q['meta']['book']['no']
    where = '%s.text.%s' % (q['id'], which)
    cls = 'slide' + (' tight' if body.get('tight') else '')
    ans = q['meta'][which]['answer']
    if body['kind'] in FIG_KINDS:
        ids = fig_ids(q)
        side = body.get('side', 's1' if which == 'exam' else 's2')
        fig_html = ('<div>%s<div class="fig%s">%s</div></div>'
                    % (stem(tb, no, where), ' tblbox' if body['kind'] == 'table' else '', fig_inner(q, which, body, ids[which], FIG_H, where)))
        if 'script' in body:
            paras = '<div class="speaker">%s</div>' % mk(body['script'], where + '.script')
        else:
            paras = '<div class="passage">%s</div>' % ''.join(paragraph(p, where + '.passage') for p in body['passage'])
        q_html = ('  <div class="q side %s%s">\n    %s\n    <div>%s\n      %s</div>\n  </div>'
                  % (side, ' pic' if body['kind'] == 'picture' else '', fig_html, paras, choices_ol(tb['choices'], ans, where, multiline=True)))
    else:
        parts = ['    ' + stem(tb, no, where)]
        if body['kind'] == 'passage':
            parts.append('    <div class="passage%s">\n%s\n    </div>' % (' cc2' if body.get('cols') == 2 else '', '\n'.join('      ' + paragraph(p, where + '.paragraphs') for p in body['paragraphs'])))
        elif body['kind'] == 'speaker':
            parts.append('    <div class="speaker%s">%s</div>' % (' cc2' if body.get('cols') == 2 else '', mk(body['text'], where + '.speaker')))
        else:
            raise BuildError('%s: 알 수 없는 본문 종류 %r' % (where, body['kind']))
        parts.append('    ' + choices_ol(tb['choices'], ans, where))
        q_html = '  <div class="q">\n%s\n  </div>' % '\n'.join(parts)
    return section(cls, ('q%d' % q['no']) if first else None, [header(rnd, q, which), q_html, foot(q, which)])


def col_title(q, who):
    ex = q['meta']['exam']
    if who == 'exam':
        return '시험 %d번' % q['no'] + (' · 듣기 대본' if ex.get('mode') == '듣기' else '')
    return '교재 %d번' % q['meta']['book']['no']


def diff_box(cls, icon, label, text, where):
    return '    <div class="%s"><b><span class="ic i-%s" aria-hidden="true"></span>%s</b>%s</div>' % (cls, icon, label, mk(text, where))


def slide_compare(rnd, q):
    an, tx = q['analysis']['compare'], q['text']['quotes']
    where = q['id'] + '.compare'
    if 'fig_labels' in an:
        ids = fig_ids(q)

        def one(who, note_cls):
            note = '시험 %d번 · %s' % (q['no'], an['fig_labels']['exam']) if who == 'exam' else '교재 %d번 · %s' % (q['meta']['book']['no'], an['fig_labels']['book'])
            fb = q['text'][who]['body']
            inner = ('<svg id="%s" viewBox="0 0 580 %d"></svg>' % (ids[who + '2'], FIG_H_COMPACT) if fb['kind'] == 'figure'
                     else fig_inner(q, who, fb, ids[who + '2'], FIG_H_COMPACT, where, compact=True))
            return ('    <div><div class="note %s">%s</div>%s<div class="cap">%s</div></div>'
                    % (note_cls, esc(note), inner, mk(tx[who][0], where + '.cap')))
        fig = '  <div class="twofig q">\n%s\n%s\n  </div>' % (one('exam', 'x'), one('book', 'b'))
        body = fig
    else:
        def col(who, c):
            ps = ''.join('<p>%s</p>' % mk(t, '%s.quotes.%s' % (q['id'], who)) for t in tx[who])
            return '    <div class="col %s"><h3>%s</h3>\n      <div class="passage">%s</div></div>' % (c, esc(col_title(q, who)), ps)
        body = '  <div class="two">\n%s\n%s\n  </div>' % (col('exam', 'x'), col('book', 'b'))
    diff = '  <div class="diff">\n%s\n%s\n  </div>' % (diff_box('s', 'check', '같은 것', an['same'], where + '.same'),
                                                       diff_box('d', 'cycle', '달라진 것', an['diff'], where + '.diff'))
    return section('slide', None, [header(rnd, q, 'compare'), body, diff])


def slide_easy(rnd, q):
    e = q['analysis']['easy']
    where = q['id'] + '.easy'

    def card(who, c, title):
        return ('    <div class="ecard %s"><div class="ico"><span class="ic i-%s" aria-hidden="true"></span></div><h3>%s</h3><p>%s</p></div>'
                % (c, e[who]['icon'], title, mk(e[who]['text'], where + '.' + who)))
    arrow = ('    <div class="arr"><svg viewBox="0 0 120 60" aria-hidden="true"><path d="M6 30h92M78 8l24 22-24 22" fill="none" '
             'stroke="currentColor" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg><span>이렇게 바뀌었어요</span></div>')
    flow = '  <div class="flow">\n%s\n%s\n%s\n  </div>' % (card('book', 'b', '교재 이야기'), arrow, card('exam', 'x', '시험 이야기'))
    sd = ('  <div class="sd"><div class="same"><b>같아요</b><span>%s</span></div><div class="dif"><b>달라요</b><span>%s</span></div></div>'
          % (mk(e['same'], where + '.same'), mk(e['diff'], where + '.diff')))
    sm = '  <p class="sum">%s</p>' % mk(e['sum'], where + '.sum')
    return section('slide easy', None, [header(rnd, q, 'easy'), flow, sd, sm])


def slide_teacher(rnd, q):
    t = q['analysis']['teacher']
    where = q['id'] + '.teacher'
    rows = []
    for key, cls, icon, label in (('evidence', 'r1', 'magnify', '근거'), ('changed', 'r2', 'cycle', '바뀐 점'), ('view', 'r3', 'cap', '교사 관점')):
        lis = '\n'.join('      <li>%s</li>' % mk(s, '%s.%s[%d]' % (where, key, i)) for i, s in enumerate(t[key]))
        rows.append('    <div class="row %s"><h3><span class="ic i-%s" aria-hidden="true"></span>%s</h3><ul>\n%s\n    </ul></div>' % (cls, icon, label, lis))
    return section('slide', None, [header(rnd, q, 'teacher'), '  <div class="rows">\n%s\n  </div>' % '\n'.join(rows)])


def question_html(rnd, q):
    slides = [slide_text(rnd, q, 'exam', True), slide_text(rnd, q, 'book', False),
              slide_compare(rnd, q), slide_easy(rnd, q), slide_teacher(rnd, q)]
    return '<!-- ============ %d번 ============ -->\n%s' % (q['no'], '\n\n'.join(slides))


# ---------- 연계 지도 ----------
def load_link_rows(path=LINK_CSV):
    """연계DB_통합_전체문항.csv → {회차: {문항 번호: 한 줄}}. '16~17'처럼 묶인 줄은 번호마다 같은 줄을 넣는다. 파일이 없으면 None."""
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        m = re.fullmatch(r'(\d+)(?:~(\d+))?', r['문항'].strip())
        if not m:
            raise BuildError('%s: 문항 칸을 읽을 수 없음: %r' % (os.path.basename(path), r['문항']))
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        cells = out.setdefault(r['시험'], {})
        for no in range(lo, hi + 1):
            cells[no] = r
    return out


def is_linked(r):
    return r is not None and r['연계방식'] != '비연계'


def map_cell(no, r, ready, href, alias=None):
    """지도 칸 하나. 수업 자료가 있으면(ready) 눌리는 칸, 아직 없으면 점선 칸, 연계가 아니면 흐린 '독립' 칸"""
    if not is_linked(r):
        return '<span class="mc none" title="%d번 · 독립 출제(교재와 연계되지 않음)"><b>%d</b><em>독립</em></span>' % (no, no)
    if not r['학생체감'].strip().isdigit():
        raise BuildError('연계 지도: %s %d번은 연계 문항인데 학생체감이 비어 있음' % (r['시험'], no))
    felt, method = int(r['학생체감']), r['연계방식']
    tip = '%d번 · %s · %s %s쪽 · %s · 체감 %d점' % (no, r['시험유형'], r['교재'], r['쪽'], method, felt)
    inner = '<b>%d</b><em>%s</em><span class="bk">%s</span>%s' % (
        no, esc(METHOD_TAG.get(method, method)), esc(BOOK_TAG.get(r['교재'], r['교재'])), felt_cells(felt))
    if no in ready:
        return '<a class="mc lk on" href="%s#q%d" title="%s" aria-label="%s">%s</a>' % (
            esc_attr(href), (alias or {}).get(no, no), esc_attr(tip + ' · 수업 자료 있음'), esc_attr('%d번 수업 자료 열기. %s' % (no, tip)), inner)
    return '<span class="mc lk" title="%s">%s</span>' % (esc_attr(tip + ' · 수업 자료 준비 중'), inner)


def map_slide(rnd, cells, ready, href='', slide_id='map', alias=None):
    """연계 지도 장: 시험 문항 1~45번 칸. cells={번호: CSV 한 줄}, ready=수업 자료가 있는 번호, href=수업 자료 파일(같은 파일이면 빈 글)"""
    linked = {no for no, r in cells.items() if is_linked(r)}
    methods = {}
    for no in linked:
        methods[cells[no]['연계방식']] = methods.get(cells[no]['연계방식'], 0) + 1
    bands = []
    for title, lo, hi in (('듣기', 1, LISTEN_LAST), ('읽기', LISTEN_LAST + 1, LAST_NO)):
        grid = ''.join(map_cell(no, cells.get(no), ready, href, alias) for no in range(lo, hi + 1))
        bands.append('<div class="band"><h3>%s <small>%d~%d번</small><span class="n">교재 연계 %d문항</span></h3><div class="mg">%s</div></div>'
                     % (title, lo, hi, sum(1 for no in range(lo, hi + 1) if no in linked), grid))
    n_ready = len(ready & linked)
    rd = '<span class="rd">수업 자료 <b>%d</b>문항</span>' % n_ready if n_ready else ''
    words = ' · '.join('<b>%s</b>=%s %d' % (METHOD_TAG[m], esc(m), methods[m]) for m in METHOD_TAG if m in methods)
    other = [m for m in methods if m not in METHOD_TAG]
    if other:
        raise BuildError('연계 지도: 약어가 없는 연계방식: %s (build.py 의 METHOD_TAG 에 넣을 것)' % ', '.join(other))
    return (
        '<section class="slide mapslide" id="%s" aria-label="연계 지도">\n'
        '  <div class="mh"><h2><span class="ic i-link" aria-hidden="true"></span>연계 지도</h2>'
        '<span class="rn">%s<small>%s</small></span>'
        '<p class="ms"><span>교재 연계 <b>%d</b>문항</span><span>독립 출제 <b>%d</b>문항</span>%s</p></div>\n'
        '  %s\n'
        '  <div class="mf"><span class="k"><i class="sw on"></i>수업 자료 있음(눌러서 열기)</span><span class="k"><i class="sw"></i>준비 중</span>'
        '<span class="k"><i class="sw none"></i>독립 출제(교재와 연계되지 않음)</span>'
        '<span class="k">체감 %s 교재를 공부한 학생이 본 적 있다고 느끼기 쉬운 정도</span>'
        '<span class="k wd">연계방식 %s</span></div>\n'
        '</section>'
    ) % (slide_id, esc(rnd['name']), esc(rnd['held']), len(linked), LAST_NO - len(linked), rd,
         '\n  '.join(bands), felt_cells(3), words)


def nav_html(rnd, qs, map_on):
    """위 목차 줄. 문항이 많으면(COMPACT_NAV_OVER 초과) 번호 알약 대신 이전·다음 문항 단추(nav.js)를 둔다."""
    legend = '<span class="legend"><mark>연계 단서</mark><span class="a">정답 근거</span></span>'
    map_a = '<a href="#map">연계 지도</a>' if map_on else ''
    if len(qs) > COMPACT_NAV_OVER:
        first = qs[0]['no']
        go = ('<a href="#%s" data-go="prev">‹ 이전 문항</a><a href="#q%d" data-go="next">다음 문항 ›</a>'
              % ('map' if map_on else 'q%d' % first, first))
        return '<nav class="cn"><b>%s</b>%s%s%s</nav>' % (esc(rnd['nav_title']), map_a, go, legend)
    links = ''.join('<a href="#q%d">%s번 %s</a>' % (q['no'], exam_label(q), esc(q['tag'])) for q in qs)
    return '<nav><b>%s</b>%s%s%s</nav>' % (esc(rnd['nav_title']), map_a, links, legend)


# ---------- 검사 ----------
def unfilled(o, path=''):
    """서식에서 채우지 않고 남긴 칸(★ 로 시작하는 안내 글)을 찾는다"""
    if isinstance(o, str):
        return [path] if '★' in o else []
    if isinstance(o, dict):
        return [x for k, v in o.items() for x in unfilled(v, path + '.' + k if path else k)]
    if isinstance(o, list):
        return [x for i, v in enumerate(o) for x in unfilled(v, '%s[%d]' % (path, i))]
    return []


def validate(q, rnd, icons):
    miss = []
    left = unfilled(q)
    if left:
        raise BuildError('%s: 채우지 않은 칸(★)이 남아 있음: %s' % (q.get('id', '?'), ', '.join(left[:8])))

    def need(path, cond):
        if not cond:
            miss.append(path)
    need('id', isinstance(q.get('id'), str))
    need('no', isinstance(q.get('no'), int) and q['no'] >= 1)
    need('tag', isinstance(q.get('tag'), str))
    need('covers (선택. 이 문항 장이 함께 맡는 시험 번호 목록)', q.get('covers') is None or (isinstance(q['covers'], list) and q['covers'] and all(isinstance(c, int) and c > q['no'] for c in q['covers'])))
    m = q.get('meta', {})
    for who in ('exam', 'book'):
        need('meta.%s.type' % who, isinstance(m.get(who, {}).get('type'), str))
        need('meta.%s.answer' % who, isinstance(m.get(who, {}).get('answer'), int))
    for k in ('name', 'unit'):
        need('meta.book.' + k, isinstance(m.get('book', {}).get(k), str) and m['book'][k])
    for k in ('page', 'no'):
        need('meta.book.' + k + ' (1 이상의 정수)', isinstance(m.get('book', {}).get(k), int) and m['book'][k] >= 1)
    need('meta.exam.mode (읽기 또는 듣기)', m.get('exam', {}).get('mode') in ('읽기', '듣기'))
    need('meta.link.label', isinstance(m.get('link', {}).get('label'), str))
    need('meta.link.felt', m.get('link', {}).get('felt') in (1, 2, 3, 4, 5))
    t = q.get('text', {})
    for who in ('exam', 'book'):
        tb = t.get(who, {})
        need('text.%s.stem' % who, isinstance(tb.get('stem'), str))
        need('text.%s.body.kind' % who, tb.get('body', {}).get('kind') in ('passage', 'speaker') + FIG_KINDS)
        need('text.%s.choices.items' % who, isinstance(tb.get('choices', {}).get('items'), list) and len(tb['choices']['items']) == 5)
        if tb.get('body', {}).get('kind') == 'figure':
            need('text.%s.body.chart' % who, isinstance(tb['body'].get('chart'), dict))
        if tb.get('body', {}).get('kind') in ('picture', 'table'):
            fb = tb['body']
            need('text.%s.body.alt (그림·표 설명)' % who, isinstance(fb.get('alt'), str))
            need('text.%s.body.script 또는 passage (그림·표 옆 글)' % who, isinstance(fb.get('script'), str) or (isinstance(fb.get('passage'), list) and fb['passage']))
        if tb.get('body', {}).get('kind') == 'picture':
            need('text.%s.body.image (그림 파일이 문항데이터/<회차>/이미지/ 에 있어야 함)' % who,
                 isinstance(tb['body'].get('image'), str) and os.path.isfile(image_path(q, tb['body']['image'])))
        if tb.get('body', {}).get('kind') == 'table':
            fb = tb['body']
            need('text.%s.body.head, rows (표)' % who, isinstance(fb.get('head'), list) and isinstance(fb.get('rows'), list) and fb['rows']
                 and all(isinstance(r, list) and len(r) == len(fb['head']) for r in fb['rows']))
    need('text.quotes.exam', isinstance(t.get('quotes', {}).get('exam'), list) and t['quotes']['exam'])
    need('text.quotes.book', isinstance(t.get('quotes', {}).get('book'), list) and t['quotes']['book'])
    a = q.get('analysis', {})
    need('analysis.compare.same', isinstance(a.get('compare', {}).get('same'), str))
    need('analysis.compare.diff', isinstance(a.get('compare', {}).get('diff'), str))
    for who in ('book', 'exam'):
        need('analysis.easy.%s.text' % who, isinstance(a.get('easy', {}).get(who, {}).get('text'), str))
        ic = a.get('easy', {}).get(who, {}).get('icon')
        need('analysis.easy.%s.icon (없는 아이콘: %s)' % (who, ic), ic in icons)
    for k in ('same', 'diff', 'sum'):
        need('analysis.easy.' + k, isinstance(a.get('easy', {}).get(k), str))
    for k in ('evidence', 'changed', 'view'):
        need('analysis.teacher.' + k, isinstance(a.get('teacher', {}).get(k), list) and a['teacher'][k])
    both_fig = all(t.get(w, {}).get('body', {}).get('kind') in FIG_KINDS for w in ('exam', 'book'))
    need('analysis.compare.fig_labels (시험·교재 둘 다 그래프·그림·표인 문항에는 필요, 한쪽만이면 쓰지 않는다)',
         both_fig == ('fig_labels' in a.get('compare', {})))
    if miss:
        raise BuildError('%s: 빠졌거나 모양이 틀린 칸: %s' % (q.get('id', '?'), ', '.join(miss)))


def check_db(rnd, qs, rows):
    """문항 데이터가 DB(연계DB_통합_전체문항.csv)와 같은지 본다: 교재, 쪽, 연계방식, 학생체감. 다르면 어느 칸인지 알려 준다.
    (파일럿 때 31번 체감이 DB는 2점인데 데이터에 1점으로 들어가 있던 것을 늦게 찾아서 만든 검사)"""
    cells = rows.get(rnd['id'])
    if cells is None:
        raise BuildError('DB 대조: CSV에 회차 %s 가 없음' % rnd['id'])
    norm = lambda s: re.sub(r'연계$', '', re.sub(r'\s+', '', s))
    for q in qs:
        r = cells.get(q['no'])
        if not is_linked(r):
            raise BuildError('%s: DB에는 %d번이 연계 문항이 아님(비연계)' % (q['id'], q['no']))
        b, lk, diffs = q['meta']['book'], q['meta']['link'], []
        if b['name'] != r['교재']:
            diffs.append('meta.book.name 데이터 %r, DB %r' % (b['name'], r['교재']))
        if r['쪽'].strip().isdigit() and b['page'] != int(r['쪽']):
            diffs.append('meta.book.page 데이터 %d, DB %s' % (b['page'], r['쪽']))
        if norm(lk['label']) != norm(r['연계방식']):
            diffs.append('meta.link.label 데이터 %r, DB %r' % (lk['label'], r['연계방식']))
        if r['학생체감'].strip().isdigit() and lk['felt'] != int(r['학생체감']):
            diffs.append('meta.link.felt 데이터 %d, DB 학생체감 %s' % (lk['felt'], r['학생체감']))
        for c in covers(q):
            rc = cells.get(c)
            if not is_linked(rc):
                diffs.append('covers 의 %d번이 DB에서 연계 문항이 아님' % c)
            elif rc['교재'] != r['교재'] or rc['쪽'] != r['쪽']:
                diffs.append('covers 의 %d번: DB 교재·쪽 %s %s쪽이 %d번(%s %s쪽)과 다름' % (c, rc['교재'], rc['쪽'], q['no'], r['교재'], r['쪽']))
        if diffs:
            raise BuildError('%s: 데이터가 DB와 다름: %s' % (q['id'], '; '.join(diffs)))


def load_round(rid):
    d = os.path.join(DATA, rid)
    if not os.path.isdir(d):
        raise BuildError('회차 폴더가 없음: %s' % d)
    with open(os.path.join(d, 'round.json'), encoding='utf-8') as f:
        rnd = json.load(f)
    nums = rnd.get('order')
    files = {}
    for fn in os.listdir(d):
        m = re.fullmatch(r'q(\d+)\.json', fn)
        if m:
            files[int(m.group(1))] = fn
    if nums is None:
        nums = sorted(files)
    if nums != sorted(set(nums)):                      # 문항은 번호순(제이님 요청 2026-10-23)
        raise BuildError('round.json 의 order: 문항은 번호가 작은 것부터, 겹치지 않게 둔다: %s (order 를 지우면 q*.json 을 번호순으로 모두 만든다)' % nums)
    qs = []
    for n in nums:
        if n not in files:
            raise BuildError('q%02d.json 이 없음 (round.json 의 order)' % n)
        with open(os.path.join(d, files[n]), encoding='utf-8') as f:
            q = json.load(f)
        if q.get('no') != n:
            raise BuildError('%s: 파일 이름의 번호(%d)와 no(%r)가 다름' % (files[n], n, q.get('no')))
        qs.append(q)
    return rnd, qs


def icon_names():
    css = read_tpl('icons.css')
    return set(re.findall(r'\.i-([a-z0-9]+)\{--u:', css))


# ---------- 조립 ----------
def build_html(rnd, qs, map_on=None, rows=None, db_check=True):
    """map_on: 연계 지도 장을 맨 앞에 넣을지(None 이면 round.json 의 "map"). rows: load_link_rows() 결과(None 이면 CSV 를 읽는다).
    db_check=False 는 DB에 없는 가짜 문항으로 시험할 때만 쓴다."""
    icons = icon_names()
    for q in qs:
        validate(q, rnd, icons)
    if map_on is None:
        map_on = bool(rnd.get('map'))
    if rows is None:
        rows = load_link_rows()
    if rows is None and map_on:
        raise BuildError('연계 지도: %s 를 찾을 수 없음' % os.path.basename(LINK_CSV))
    if rows is not None and db_check:
        check_db(rnd, qs, rows)
    nav = nav_html(rnd, qs, map_on)
    map_css, map_block = '', ''
    if map_on:
        if rnd['id'] not in rows:
            raise BuildError('연계 지도: CSV에 회차 %s 가 없음' % rnd['id'])
        map_css = read_tpl('map.css')
        _ready, _alias = ready_alias(qs)
        map_block = map_slide(rnd, rows[rnd['id']], _ready, alias=_alias) + '\n\n'
    nav_on = map_on or len(qs) > COMPACT_NAV_OVER      # 지도나 이전·다음 문항 단추가 있으면 목차 줄 높이 보정(nav.css, nav.js)도 함께 넣는다
    nav_css, nav_js = (read_tpl('nav.css'), read_tpl('nav.js')) if nav_on else ('', '')
    IMAGES.clear()
    blocks = '\n\n'.join(question_html(rnd, q) for q in qs)
    img_data = ''
    if IMAGES:
        img_data = ('var IMGS=%s;\ndocument.querySelectorAll("img[data-img]").forEach(function(i){i.src=IMGS[i.getAttribute("data-img")]});\n'
                    % json.dumps(IMAGES, ensure_ascii=False, separators=(',', ':')))
    figs = []
    for q in qs:
        ids = fig_ids(q)
        for who in ('exam', 'book'):
            body = q['text'][who]['body']
            if body['kind'] != 'figure':
                continue
            cfg = body['chart']
            figs.append({'id': ids[who], 'H': FIG_H, 'compact': False, 'cfg': cfg})
            figs.append({'id': ids[who + '2'], 'H': FIG_H_COMPACT, 'compact': True, 'cfg': dict(cfg, **body.get('compact_override', {}))})
    chart_data = ''
    if figs:
        chart_data = 'var FIGS=%s;\nFIGS.forEach(function(f){chart(f.id,f.cfg,f.H,f.compact)});\n' % json.dumps(figs, ensure_ascii=False, separators=(',', ':'))
    return ''.join([
        '<title>%s</title>\n' % esc(rnd['title']),
        read_tpl('head.html'),
        '<style>\n', read_tpl('deck.css'), read_tpl('icons.css'), nav_css, map_css, '</style>\n',
        read_tpl('chalk.js').rstrip('\n'), '\n\n',
        nav, '\n\n',
        map_block,
        blocks, '\n\n',
        read_tpl('credit.html').rstrip('\n'), '\n\n',
        '<script>\n', read_tpl('chart.js'), chart_data, img_data, read_tpl('post.js'), nav_js, '</script>\n',
    ])


# ---------- 전체 첫 화면(index.html) ----------
ROUNDS_JSON = os.path.join(DATA, '회차목록.json')


def load_round_list(path=ROUNDS_JSON):
    """문항데이터/회차목록.json → 첫 화면의 제목·부제와 회차 줄 목록. 회차는 최근 것이 먼저 오게(id 내림차순) 정렬해서 돌려준다
    (탭이 왼쪽부터 최근 회차 순, 제이님 요청 2026-10-23). 모양이 틀리면 어느 칸인지 알려 준다."""
    with open(path, encoding='utf-8') as f:
        rl = json.load(f)
    text = lambda v: isinstance(v, str) and v.strip() != ''
    miss = [k for k in ('title', 'sub') if not text(rl.get(k))]
    rounds = rl.get('rounds')
    if not isinstance(rounds, list) or not rounds:
        miss.append('rounds')
        rounds = []
    for i, r in enumerate(rounds):
        if not isinstance(r, dict):
            miss.append('rounds[%d]' % i)
            continue
        miss += ['rounds[%d].%s' % (i, k) for k in ('id', 'tab', 'name', 'held') if not text(r.get(k))]
        if text(r.get('id')) and not re.fullmatch(r'\d{4}\.\d{2}', r['id']):
            miss.append('rounds[%d].id (2026.09 같은 모양)' % i)
    for k in ('id', 'tab'):
        vals = [r.get(k) for r in rounds if isinstance(r, dict)]
        miss += ['rounds.%s 겹침: %s' % (k, v) for v in sorted({v for v in vals if text(v) and vals.count(v) > 1})]
    if miss:
        raise BuildError('%s: 빠졌거나 모양이 틀린 칸: %s' % (os.path.basename(path), ', '.join(miss)))
    return dict(rl, rounds=sorted(rounds, key=lambda r: r['id'], reverse=True))


def round_files(r, exists=os.path.isfile):
    """회차 r(목록의 한 줄)의 수업 자료. 문항 데이터 폴더가 있고 만들어 둔 HTML 이 완성본에 있으면
    {'html': 파일 이름, 'pdf': PDF 파일 이름(없으면 None), 'ready': 수업 자료가 있는 문항 번호 집합}, 아니면 None.
    목록의 이름·시행 시기가 round.json 과 다르면 오류(한쪽만 고치다 만 것)."""
    if not os.path.isfile(os.path.join(DATA, r['id'], 'round.json')):
        return None
    rnd, qs = load_round(r['id'])
    for k in ('name', 'held'):
        if rnd[k] != r[k]:
            raise BuildError('%s: %s 가 회차목록.json(%r)과 round.json(%r)에서 다름' % (r['id'], k, r[k], rnd[k]))
    html = rnd.get('out') or r['id'] + '.html'
    if not exists(os.path.join(OUT, html)):
        return None
    pdf = os.path.splitext(html)[0] + '.pdf'
    ready, alias = ready_alias(qs)
    return {'html': html, 'pdf': pdf if exists(os.path.join(OUT, pdf)) else None, 'ready': ready, 'alias': alias}


def felt_mean(cells):
    """연계 문항의 학생체감 평균(1~5). 연계 문항이 없으면 None"""
    felts = [int(r['학생체감']) for r in cells.values() if is_linked(r) and r['학생체감'].strip().isdigit()]
    return sum(felts) / len(felts) if felts else None


def icons_subset(names):
    """icons.css 에서 쓰는 아이콘 줄만 남긴다(첫 화면은 아이콘이 하나뿐이라 88KB 를 다 넣지 않는다)"""
    lines = read_tpl('icons.css').split('\n')
    keep = [l for l in lines if l.startswith('/*') or any(l.startswith('.i-%s{' % n) for n in names)]
    missing = [n for n in names if not any(l.startswith('.i-%s{' % n) for l in keep)]
    if missing:
        raise BuildError('icons.css 에 없는 아이콘: %s' % ', '.join(sorted(missing)))
    return '\n'.join(keep) + '\n'


def index_actions(deck):
    if deck is None:
        return '<span class="btn off">수업 자료 준비 중</span>'
    html = '<a class="btn" href="%s">수업 자료 열기</a>' % esc_attr(deck['html'])
    if deck['pdf']:
        return html + '<a class="btn" href="%s" download>PDF 받기</a>' % esc_attr(deck['pdf'])
    return html + '<span class="btn off">PDF 준비 중</span>'


def index_html(rl, rows, decks):
    """전체 첫 화면(Artifact 에 올리는 조각 모양): 회차 탭, 탭마다 연계 지도와 수업 자료·PDF 단추.
    rl=load_round_list(), rows=load_link_rows(), decks={회차 id: round_files() 결과(없으면 None)}.
    처음에는 첫 탭(가장 최근 회차)이 열려 있고, 탭을 바꾸는 것은 template/index.js"""
    if rows is None:
        raise BuildError('첫 화면: %s 를 찾을 수 없음' % os.path.basename(LINK_CSV))
    tabs, panels = [], []
    for i, r in enumerate(rl['rounds']):
        rid, deck, first = r['id'], decks.get(r['id']), i == 0
        if rid not in rows:
            raise BuildError('첫 화면: CSV에 회차 %s 가 없음' % rid)
        cells = rows[rid]
        tabs.append('<button type="button" role="tab" id="tab-%s" aria-controls="panel-%s" aria-selected="%s" tabindex="%d" data-r="%s">%s%s</button>'
                    % (rid, rid, 'true' if first else 'false', 0 if first else -1, rid, esc(r['tab']),
                       '<span class="ok">자료 있음</span>' if deck else ''))
        mean = felt_mean(cells)
        chips = '<span>교재 연계 <b>%d</b>문항</span>' % sum(1 for row in cells.values() if is_linked(row))
        if mean is not None:
            chips += '<span>체감 평균 <b>%.1f</b></span>' % mean
        smap = map_slide(r, cells, deck['ready'] if deck else set(), href=deck['html'] if deck else '', slide_id='map-' + rid, alias=deck.get('alias') if deck else None)
        panels.append('<div class="panel" role="tabpanel" id="panel-%s" aria-labelledby="tab-%s" data-r="%s"%s>\n'
                      '<div class="ph"><div class="chips">%s</div><div class="acts">%s</div></div>\n%s\n</div>'
                      % (rid, rid, rid, '' if first else ' hidden', chips, index_actions(deck), smap))
    return ''.join([
        '<title>%s</title>\n' % esc(rl['title']),
        read_tpl('head.html'),
        '<style>\n', read_tpl('deck.css'), icons_subset({'link'}), read_tpl('map.css'), read_tpl('index.css'), '</style>\n',
        read_tpl('chalk.js').rstrip('\n'), '\n\n',
        '<div class="ix">\n<h1>%s</h1>\n<p class="sub">%s</p>\n' % (esc(rl['title']), esc(rl['sub'])),
        '<div class="tabs" role="tablist" aria-label="시험 회차">%s</div>\n' % ''.join(tabs),
        '\n'.join(panels), '\n</div>\n\n',
        read_tpl('credit.html').rstrip('\n'), '\n\n',
        '<script>\n', read_tpl('index.js'), '</script>\n',
    ])


def standalone(html):
    """Artifact 에 올리는 조각(build_html 결과)에, Artifact 가 씌워 주는 것과 같은 틀(문서 형식 선언, charset, viewport, 작은 초기값)을 씌워
    파일로 바로 열리는 독립 파일로 만든다. 틀 없이 파일로 열면 크롬이 괴상 모드(quirks)로 읽어서 Artifact 화면과 칸 배치가 달라진다.
    틀 글은 template/skeleton_head.html, skeleton_tail.html (tools/skeleton.js 도 같은 글을 쓴다)."""
    return read_tpl('skeleton_head.html') + html + read_tpl('skeleton_tail.html')


def write_page(out, html, fragment):
    """조각(html)을 파일로 쓴다. fragment 가 아니면 독립 파일 틀을 씌운다. 쓴 바이트 수를 돌려준다."""
    page = html if fragment else standalone(html)
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(page)
    return len(page.encode('utf-8'))


def main_index(args):
    check_only = '--check' in args
    fragment = '--fragment' in args
    out = None
    if '--out' in args:
        out = args[args.index('--out') + 1]
    try:
        rl = load_round_list()
        decks = {r['id']: round_files(r) for r in rl['rounds']}
        html = index_html(rl, load_link_rows(), decks)
    except BuildError as e:
        print('오류:', e)
        return 1
    n_decks = sum(1 for d in decks.values() if d)
    if check_only:
        print('검사 통과: 첫 화면, 회차 %d개(수업 자료 있는 회차 %d개)' % (len(decks), n_decks))
        return 0
    if out is None:
        os.makedirs(OUT, exist_ok=True)
        out = os.path.join(OUT, 'index.html')
    size = write_page(out, html, fragment)
    print('만듦: %s (%d바이트, 회차 %d개, 수업 자료 있는 회차 %d개, %s)' % (out, size, len(decks), n_decks,
                                                              'Artifact 에 올릴 조각' if fragment else '독립 파일'))
    return 0


def main(argv):
    if not argv or argv[0].startswith('-'):
        print(__doc__)
        return 2
    if argv[0] == 'index':
        return main_index(argv[1:])
    rid, args = argv[0], argv[1:]
    check_only = '--check' in args
    fragment = '--fragment' in args
    map_on = True if '--map' in args else (False if '--no-map' in args else None)
    out = None
    if '--out' in args:
        out = args[args.index('--out') + 1]
    try:
        rnd, qs = load_round(rid)
        html = build_html(rnd, qs, map_on=map_on)
    except BuildError as e:
        print('오류:', e)
        return 1
    if check_only:
        print('검사 통과: %s 회차, 문항 %d개 (%s)' % (rid, len(qs), ', '.join(str(q['no']) for q in qs)))
        return 0
    if out is None:
        os.makedirs(OUT, exist_ok=True)
        out = os.path.join(OUT, rnd.get('out') or (rid + '.html'))
    size = write_page(out, html, fragment)
    print('만듦: %s (%d바이트, 문항 %d개, 장 %d개, %s)' % (out, size, len(qs), html.count('<section '),
                                                  'Artifact 에 올릴 조각' if fragment else '독립 파일'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
