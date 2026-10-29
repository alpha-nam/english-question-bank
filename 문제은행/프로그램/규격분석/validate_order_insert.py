"""순서·삽입 질적 분석(블라인드)을 메가스터디 실제 선택비율과 대조한다."""
import json, re, statistics as st, collections as C
ROOT = '.'
CIR = '①②③④⑤'


def ebsi(it):
    """EBSi 오답률 TOP15 문항만: 정답률 = 100 - 오답률, 선택비율 = EBSi 선택지 비율 (메가스터디는 쓰지 않음, 2026-10-28)"""
    w = it.get('wrong_rate')
    return {'정답률': 100 - w['오답률'], '선택비율': w['선택지비율']} if w else None

def item(i):
    return json.load(open(f'DB/기출/{i[:7]}/{i}.json', encoding='utf-8'))

def grade(s):
    m = re.match(r'\s*(상|중|하)', s or '')
    return m.group(1) if m else None

out = {}
for kind, files in (('순서', ['순서분석/결과/순서36.jsonl', '순서분석/결과/순서37.jsonl']),
                    ('삽입', ['삽입분석/결과/삽입38.jsonl', '삽입분석/결과/삽입39.jsonl'])):
    rows = [json.loads(l) for f in files for l in open('규격/' + f, encoding='utf-8') if l.strip()]
    by_grade = C.defaultdict(list); top_hit = top_n = 0; rates = []; cue_rate = C.defaultdict(list); func_rate = C.defaultdict(list)
    for r in rows:
        it = item(r['id']); ms = ebsi(it)
        if not ms: continue
        sel = ms['선택비율']; ans = CIR.index(it['answer'])
        rates.append(ms['정답률'])
        g = {}
        if kind == '순서':
            ch = [re.sub(r'[()\s－-]', '', c) for c in it['text']['choices']]
            for w in r['wrong_orders']:
                k = ch.index(w['order'].replace('-', '').replace(' ', ''))
                g[k] = grade(w['attraction'])
            cue_rate[r.get('deciding_cue_type') or '?'].append(ms['정답률'])
            func_rate[r['given_end'].split('(')[0].strip()[:12]].append(ms['정답률'])
        else:
            for p in r['positions']:
                if p['verdict'] != '정답': g[p['pos'] - 1] = grade(p['attraction'])
            func_rate[r['given_function'].split('(')[0].split('·')[0].strip()[:8]].append(ms['정답률'])
        for k, gr in g.items(): by_grade[gr].append(sel[k])
        order = {'상': 0, '중': 1, '하': 2}
        best = min(g, key=lambda k: order.get(g[k], 3))
        real = max((k for k in range(5) if k != ans), key=lambda k: sel[k])
        top_n += 1; top_hit += (g[best] == g[real] if g[real] else 0) or best == real
    out[kind] = {'문항수': top_n, '정답률 중앙값': st.median(rates), '정답률 범위': [min(rates), max(rates)],
                 'AI 매력도별 실제 선택비율 평균': {k: [round(st.mean(v), 1), len(v)] for k, v in by_grade.items()},
                 '실제 최다 오답이 AI 최상위 등급에 포함된 비율': f'{top_hit}/{top_n}',
                 '주어진 글/문장 역할별 정답률 중앙값': {k: [st.median(v), len(v)] for k, v in sorted(func_rate.items(), key=lambda x: -len(x[1]))}}
json.dump(out, open('규격/순서삽입_검증.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
