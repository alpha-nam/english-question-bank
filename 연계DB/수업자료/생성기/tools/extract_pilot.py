#!/usr/bin/env python3
"""기준본(18판 시안 HTML)에서 문항 데이터(JSON)를 뽑는다.

처음 데이터를 만들 때 한 번 쓴 도구다. 이후에는 JSON 이 원본이고, HTML 을 거꾸로 읽는 일은 하지 않는다.
  python3 -I extract_pilot.py <기준본.html> <나갈 폴더>
  예: python3 -I extract_pilot.py ../tests/golden/2026.09_pilot_v18.html ../../문항데이터/2026.09
나갈 폴더에 round.json 과 qNN.json 이 만들어진다(이미 있으면 덮어쓴다).
"""
import json
import os
import re
import subprocess
import sys


# ---------- 글 바꾸기: HTML 조각 -> 데이터 글 표기 ----------
def h2m(h, where=''):
    """build.py 의 mk() 와 거꾸로. <span class="a"> -> <ev>, <span class="blk"></span> -> <blank/>"""
    h = h.replace('<span class="blk"></span>', '<blank/>')
    spans = re.findall(r'<span[^>]*>', h)
    bad = [s for s in spans if s != '<span class="a">']
    if bad:
        raise SystemExit('%s: 알 수 없는 span %r' % (where, bad))
    h = h.replace('<span class="a">', '<ev>')
    h = h.replace('</span>', '</ev>')
    if '&nbsp;' in h:
        raise SystemExit('%s: 글 안에 &nbsp; 가 있음: %s' % (where, h[:60]))
    return h.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')


def one(pat, s, where, flags=re.S):
    m = re.search(pat, s, flags)
    if not m:
        raise SystemExit('%s: 못 찾음: %s' % (where, pat[:60]))
    return m


def parse_stem(sec, expect_no, where):
    inner = one(r'<p class="stem">(.*?)</p>', sec, where).group(1)
    m = re.fullmatch(r'(\d+)\. (.*?)(?:&nbsp;<small>\[(\d+)점\]</small>)?', inner, re.S)
    if not m or int(m.group(1)) != expect_no:
        raise SystemExit('%s: 문제 머리가 이상함: %s' % (where, inner[:60]))
    return h2m(m.group(2), where + '.stem'), (int(m.group(3)) if m.group(3) else None)


def parse_choices(sec, where):
    m = one(r'<ol class="(ch[^"]*)">(.*?)</ol>', sec, where)
    cls = m.group(1).split()
    lis = re.findall(r'<li( class="ok")?><i>(.)</i>(.*?)</li>', m.group(2), re.S)
    items = [h2m(t, where + '.choices') for _, _, t in lis]
    ok = [i + 1 for i, (o, _, _) in enumerate(lis) if o]
    if len(items) != 5 or len(ok) != 1:
        raise SystemExit('%s: 선택지 수/정답 표시가 이상함 %d/%s' % (where, len(items), ok))
    ch = {'items': items}
    if 'en' in cls:
        ch['lang'] = 'en'
    cols = [int(c[3:]) for c in cls if re.fullmatch(r'col\d', c)]
    if cols:
        ch['cols'] = cols[0]
    return ch, ok[0]


def parse_paragraph(inner, where):
    m = re.fullmatch(r'(.*?)(?:<span class="fn">(.*?)</span>)?', inner, re.S)
    p = {'t': h2m(m.group(1), where)}
    if m.group(2):
        p['fn'] = m.group(2).split(' &nbsp;')
    return p


def parse_answer(sec, where):
    t = one(r'<div class="foot"><div class="ans">정답 (.)(?: · (.*?))?</div></div>', sec, where)
    return '①②③④⑤'.index(t.group(1)) + 1, (t.group(2) or '')


def parse_chart_calls(script, where):
    """기준본 스크립트의 EXAM/BOOK 정의와 chart(...) 호출을 node 로 실행해 그대로 받는다."""
    i = script.index('var EXAM=')
    j = script.index('/* 줄바꿈 규칙')
    seg = script[i:j]
    js = ('var calls=[];function chart(id,cfg,H,compact){calls.push({id:id,H:H,compact:!!compact,'
          'cfg:JSON.parse(JSON.stringify(cfg))})}\n' + seg + '\nconsole.log(JSON.stringify(calls));')
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit('%s: node 실행 실패: %s' % (where, out.stderr[:200]))
    return {c['id']: c for c in json.loads(out.stdout)}


# ---------- JSON 예쁘게 쓰기: 짧고 단순한 목록·사전은 한 줄 ----------
def dump(o, ind=0):
    pad = '  ' * ind
    if isinstance(o, dict):
        if not o:
            return '{}'
        flat = all(not isinstance(v, (dict, list)) for v in o.values())
        one_line = '{' + ', '.join('%s: %s' % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False)) for k, v in o.items()) + '}'
        if flat and len(one_line) <= 110:
            return one_line
        return '{\n' + ',\n'.join('%s  %s: %s' % (pad, json.dumps(k, ensure_ascii=False), dump(v, ind + 1)) for k, v in o.items()) + '\n' + pad + '}'
    if isinstance(o, list):
        if not o:
            return '[]'
        one_line = json.dumps(o, ensure_ascii=False, separators=(', ', ': '))
        if all(not isinstance(v, (dict, list)) for v in o) and len(one_line) <= 110:
            return one_line
        return '[\n' + ',\n'.join('%s  %s' % (pad, dump(v, ind + 1)) for v in o) + '\n' + pad + ']'
    return json.dumps(o, ensure_ascii=False)


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    src, outdir = argv
    s = open(src, encoding='utf-8').read()
    title = one(r'<title>(.*?)</title>', s, 'title').group(1)
    nav = one(r'<nav><b>(.*?)</b>((?:<a href="#q\d+">.*?</a>)+)<span class="legend">', s, 'nav')
    links = re.findall(r'<a href="#q(\d+)">(\d+)번 (.*?)</a>', nav.group(2))
    order = [int(a) for a, _, _ in links]
    tags = {int(a): t for a, _, t in links}
    script = s[s.index('<script>\n'):]
    calls = parse_chart_calls(script, 'script')

    i0 = s.index('<!-- ============')
    i1 = s.index('<p class="credit">')
    body = s[i0:i1]
    blocks = re.split(r'<!-- ============ (\d+)번 ============ -->\n', body)
    # blocks = ['', no, text, no, text, ...]
    rnd = None
    os.makedirs(outdir, exist_ok=True)
    for k in range(1, len(blocks), 2):
        no = int(blocks[k])
        secs = re.findall(r'<section class="([^"]*)"[^>]*>\n(.*?)\n</section>', blocks[k + 1], re.S)
        if [c.split()[0] for c, _ in secs] != ['slide'] * 5 or len(secs) != 5:
            raise SystemExit('%d번: 장이 5개가 아님' % no)
        ex_c, ex = secs[0]
        bk_c, bk = secs[1]
        cmp_c, cm = secs[2]
        ez_c, ez = secs[3]
        tc_c, tc = secs[4]
        where = '%d번' % no

        # ----- 메타 -----
        x = one(r'<span class="chip x on">.*?<em>(.*?)</em><small>(.*?)</small></span><b>(\d+)번</b>', ex, where + '.chip.x').groups()
        b = one(r'<span class="chip b on">.*?<em>(.*?) (\d+)쪽</em><small>(.*?)</small></span><b>(\d+)번</b>', bk, where + '.chip.b').groups()
        if int(x[2]) != no:
            raise SystemExit('%s: 시험 칩 번호 %s' % (where, x[2]))
        this_rnd = {'name': x[0], 'held': x[1]}
        if rnd is None:
            rnd = this_rnd
        elif rnd != this_rnd:
            raise SystemExit('%s: 회차 이름이 문항마다 다름' % where)
        link = one(r'<span class="lk">.*?<small>(.*?)</small></span>', ex, where + '.lk').group(1)
        kd_x = one(r'<span class="kd"><b>시험 문항</b><small>(.*?)</small></span>', ex, where + '.kd').group(1)
        kd_b = one(r'<span class="kd"><b>교재 원문항</b><small>(.*?)</small></span>', bk, where + '.kd').group(1)
        listening = kd_x.endswith(' · 듣기')
        ex_type = kd_x[:-len(' · 듣기')] if listening else kd_x
        if listening:
            if not kd_b.endswith(' · 읽기'):
                raise SystemExit('%s: 듣기 문항인데 교재 쪽 유형에 읽기 표시가 없음' % where)
            bk_type = kd_b[:-len(' · 읽기')]
        else:
            bk_type = kd_b
        felt = one(r'<span class="kd"><b>비교<small>체감 (●*)○*</small></b>', cm, where + '.felt').group(1).count('●')
        ex_ans, ex_note = parse_answer(ex, where + '.exam')
        bk_ans, bk_note = parse_answer(bk, where + '.book')

        q = {'schema': 1, 'id': '%s-%02d' % ('2026.09', no), 'round': '2026.09', 'no': no, 'tag': tags[no]}
        q['meta'] = {
            'exam': {'type': ex_type, 'mode': '듣기' if listening else '읽기', 'answer': ex_ans},
            'book': {'name': b[0], 'page': int(b[1]), 'unit': b[2], 'no': int(b[3]), 'type': bk_type, 'answer': bk_ans},
            'link': {'label': link, 'felt': felt},
        }

        # ----- 시험·교재 원문항 -----
        text = {}
        for which, sec, cls, n in (('exam', ex, ex_c, no), ('book', bk, bk_c, int(b[3]))):
            w = '%s.%s' % (where, which)
            tb = {}
            if '<div class="q side ' in sec:
                side = one(r'<div class="q side (s\d)">', sec, w).group(1)
                stem, pts = parse_stem(sec, n, w)
                fig = one(r'<div class="fig"><svg id="(c-\w+)" viewBox="0 0 580 (\d+)" role="img" aria-label="(.*?)"></svg></div>', sec, w)
                cid = fig.group(1)
                if cid != 'c-' + which or int(fig.group(2)) != 440:
                    raise SystemExit('%s: 도표 id/높이가 이상함' % w)
                passage = one(r'<div class="passage">(.*?)</div>', sec, w).group(1)
                paras = [parse_paragraph(p, w + '.passage') for p in re.findall(r'<p>(.*?)</p>', passage, re.S)]
                ch, ok = parse_choices(sec, w)
                body_d = {'kind': 'figure', 'side': side, 'alt': h2m(fig.group(3)), 'chart': calls[cid]['cfg'], 'passage': paras}
                if cid != 'c-' + which or calls[cid]['H'] != 440 or calls[cid]['compact']:
                    raise SystemExit('%s: 큰 도표 호출이 기준본과 다름' % w)
                c2 = calls[cid + '2']
                if c2['H'] != 300 or not c2['compact']:
                    raise SystemExit('%s: 비교용 도표 호출이 이상함' % w)
                over = {k: v for k, v in c2['cfg'].items() if calls[cid]['cfg'].get(k) != v}
                missing = [k for k in calls[cid]['cfg'] if k not in c2['cfg']]
                if missing:
                    raise SystemExit('%s: 비교용 도표에서 빠진 설정 %s' % (w, missing))
                if over:
                    body_d['compact_override'] = over
            else:
                stem, pts = parse_stem(sec, n, w)
                if '<div class="speaker">' in sec:
                    body_d = {'kind': 'speaker', 'text': h2m(one(r'<div class="speaker">(.*?)</div>', sec, w).group(1), w + '.speaker')}
                else:
                    passage = one(r'<div class="passage">\n(.*?)\n    </div>', sec, w).group(1)
                    ps = re.findall(r'^      <p>(.*?)</p>$', passage, re.M)
                    if len(ps) != passage.count('\n') + 1:
                        raise SystemExit('%s: 지문 문단 나누기가 이상함' % w)
                    body_d = {'kind': 'passage', 'paragraphs': [parse_paragraph(p, w + '.paragraphs') for p in ps]}
                ch, ok = parse_choices(sec, w)
            if ok != (ex_ans if which == 'exam' else bk_ans):
                raise SystemExit('%s: 선택지의 정답 표시(%d)와 아래 정답 칸이 다름' % (w, ok))
            if 'tight' in cls.split():
                body_d['tight'] = True
            tb['stem'] = stem
            if pts:
                tb['points'] = pts
            tb['body'] = body_d
            tb['choices'] = ch
            text[which] = tb

        # ----- 비교 장: 인용 -----
        compare = {}
        if 'twofig' in cm:
            labels = re.findall(r'<div class="note [xb]">(?:시험|교재) \d+번 · (.*?)</div>', cm)
            quotes = re.findall(r'<div class="cap">(.*?)</div>', cm, re.S)
            if len(labels) != 2 or len(quotes) != 2:
                raise SystemExit('%s: 도표 비교 장 모양이 이상함' % where)
            text['quotes'] = {'exam': [h2m(quotes[0])], 'book': [h2m(quotes[1])]}
            compare['fig_labels'] = {'exam': labels[0], 'book': labels[1]}
        else:
            cols = re.findall(r'<div class="col [xb]"><h3>(.*?)</h3>\n      <div class="passage">(.*?)</div></div>', cm, re.S)
            if len(cols) != 2:
                raise SystemExit('%s: 비교 장 칸이 2개가 아님' % where)
            text['quotes'] = {'exam': [h2m(p, where) for p in re.findall(r'<p>(.*?)</p>', cols[0][1], re.S)],
                              'book': [h2m(p, where) for p in re.findall(r'<p>(.*?)</p>', cols[1][1], re.S)]}
        same = one(r'<div class="s"><b><span class="ic i-check" aria-hidden="true"></span>같은 것</b>(.*?)</div>', cm, where).group(1)
        diff = one(r'<div class="d"><b><span class="ic i-cycle" aria-hidden="true"></span>달라진 것</b>(.*?)</div>\n  </div>', cm, where).group(1)
        compare = dict([('same', h2m(same, where + '.same')), ('diff', h2m(diff, where + '.diff'))] + list(compare.items()))

        # ----- 쉽게 보기 -----
        easy = {}
        for who, c in (('book', 'b'), ('exam', 'x')):
            m = one(r'<div class="ecard %s"><div class="ico"><span class="ic i-(\w+)" aria-hidden="true"></span></div><h3>%s</h3><p>(.*?)</p></div>'
                    % (c, '교재 이야기' if who == 'book' else '시험 이야기'), ez, where + '.easy.' + who)
            easy[who] = {'icon': m.group(1), 'text': h2m(m.group(2), where + '.easy.' + who)}
        sd = one(r'<div class="sd"><div class="same"><b>같아요</b><span>(.*?)</span></div><div class="dif"><b>달라요</b><span>(.*?)</span></div></div>', ez, where)
        easy['same'], easy['diff'] = h2m(sd.group(1), where), h2m(sd.group(2), where)
        easy['sum'] = h2m(one(r'<p class="sum">(.*?)</p>', ez, where).group(1), where + '.sum')

        # ----- 교사 분석 -----
        teacher = {}
        for key, cls_, ic in (('evidence', 'r1', 'magnify'), ('changed', 'r2', 'cycle'), ('view', 'r3', 'cap')):
            m = one(r'<div class="row %s"><h3><span class="ic i-%s" aria-hidden="true"></span>.*?</h3><ul>\n(.*?)\n    </ul></div>' % (cls_, ic), tc, where + '.teacher.' + key)
            lis = re.findall(r'^      <li>(.*?)</li>$', m.group(1), re.M)
            if len(lis) != m.group(1).count('\n') + 1:
                raise SystemExit('%s: 교사 분석 줄 나누기가 이상함' % where)
            teacher[key] = [h2m(t, where + '.teacher.' + key) for t in lis]

        analysis = {}
        notes = {k: v for k, v in (('exam', ex_note), ('book', bk_note)) if v}
        if notes:
            analysis['answer_note'] = notes
        analysis['compare'] = compare
        analysis['easy'] = easy
        analysis['teacher'] = teacher
        q['text'] = text
        q['analysis'] = analysis
        fn = os.path.join(outdir, 'q%02d.json' % no)
        with open(fn, 'w', encoding='utf-8', newline='\n') as f:
            f.write(dump(q) + '\n')
        print('썼음:', fn)

    rid = '2026.09'
    r = {'schema': 1, 'id': rid, 'name': rnd['name'], 'held': rnd['held'], 'title': title, 'nav_title': nav.group(1),
         'order': order, 'out': '2026.09_파일럿.html'}
    fn = os.path.join(outdir, 'round.json')
    with open(fn, 'w', encoding='utf-8', newline='\n') as f:
        f.write(dump(r) + '\n')
    print('썼음:', fn)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
