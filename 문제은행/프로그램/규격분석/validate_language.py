"""무관한 문장·어법·어휘 질적 분석(블라인드)의 오답 끌림 등급을 메가스터디 실제 선택비율과 대조한다."""
import json, os, re, statistics as st, collections as C
import numpy as np
CIR = '①②③④⑤'
ORDER = {'상': 0, '중': 1, '하': 2}



def ebsi(it):
    """EBSi 오답률 TOP15 문항만: 정답률 = 100 - 오답률, 선택비율 = EBSi 선택지 비율 (메가스터디는 쓰지 않음, 2026-10-28)"""
    w = it.get('wrong_rate')
    return {'정답률': 100 - w['오답률'], '선택비율': w['선택지비율']} if w else None

def item(i):
    return json.load(open(f'DB/기출/{i[:7]}/{i}.json', encoding='utf-8'))


def grade(s):
    m = re.match(r'\s*(상|중|하)', s or '')
    return m.group(1) if m else None


def words(s):
    return len(re.findall(r"[A-Za-z][A-Za-z'’-]*", s or ''))


out = {}
for kind in ('무관', '어법', '어휘'):
    path = f'규격/언어분석/결과/{kind}.jsonl'
    if not os.path.exists(path):
        continue
    rows = [json.loads(l) for l in open(path, encoding='utf-8') if l.strip()]
    by_grade = C.defaultdict(list); hit = n = 0; rates = []; lens = []; struct = C.defaultdict(list); hardest = []
    for r in rows:
        it = item(r['id']); ms = ebsi(it)
        if not ms:
            continue
        sel = ms['선택비율']; ans = CIR.index(it['answer'])
        g = {(CIR.index(k) if k in CIR else int(k) - 1): grade(v) for k, v in r['attraction_grades'].items()}
        for k, gr in g.items():
            by_grade[gr].append(sel[k])
        real = max((k for k in range(5) if k != ans), key=lambda k: sel[k])
        top = min(ORDER.get(v, 3) for v in g.values())
        hit += ORDER.get(g.get(real), 3) == top; n += 1
        rates.append(ms['정답률']); lens.append(words(it['text']['body']))
        struct[(r.get('passage_structure') or r.get('summary_frame') or '?').split('(')[0].split('—')[0].split('→')[0].strip()[:10]].append(ms['정답률'])
        hardest.append((ms['정답률'], r['id'], CIR[real], sel[real], g.get(real)))
    hardest.sort()
    out[kind] = {'문항수': n, '정답률 중앙값': st.median(rates), '정답률 범위': [min(rates), max(rates)],
                 'D안 분포': dict(C.Counter('하' if x >= 55 else '중' if x >= 40 else '상' for x in rates)),
                 'AI 끌림 등급별 실제 선택비율 평균': {k: [round(st.mean(v), 1), len(v)] for k, v in sorted(by_grade.items(), key=lambda x: ORDER.get(x[0], 3))},
                 '실제 최다 오답이 AI 최상위 등급에 포함': f'{hit}/{n}',
                 '본문 단어수-정답률 상관 r': round(float(np.corrcoef(lens, rates)[0, 1]), 2),
                 '어려운 문항 5개(정답률, id, 최다오답, 그 비율, AI등급)': hardest[:5]}
json.dump(out, open('규격/언어_검증.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
