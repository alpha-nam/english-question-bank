"""구성 분류 일치율: 같은 70지문을 원래 팀 + check1~4가 독립 분류한 결과를 비교한다.
지표: 칸마다 (1) 두 명씩 짝지은 단순 일치율 평균, (2) Fleiss' kappa(우연 일치를 뺀 일치도), (3) 다수결 동의 지문 비율."""
import json, glob, os, itertools, collections as C
ids = json.load(open('규격/구성분석/배정/check1.json', encoding='utf-8'))['ids']
orig = {json.loads(l)['id']: json.loads(l) for f in glob.glob('규격/구성분석/결과/team*.jsonl') for l in open(f, encoding='utf-8')}
import sys
want = sys.argv[1].split(',') if len(sys.argv) > 1 else None   # 예: check1,check2,check3,check4
raters = {} if want else {'원래': orig}
for f in sorted(glob.glob('규격/구성분석/결과/check*.jsonl')):
    if want and os.path.basename(f)[:-6] not in want:
        continue
    raters[os.path.basename(f)[:-6]] = {json.loads(l)['id']: json.loads(l) for l in open(f, encoding='utf-8')}


def fleiss(table):
    n = len(table[0]) and sum(table[0].values())
    N = len(table)
    cats = set(k for t in table for k in t)
    p = {c: sum(t.get(c, 0) for t in table) / (N * n) for c in cats}
    P = [(sum(v * v for v in t.values()) - n) / (n * (n - 1)) for t in table]
    Pb, Pe = sum(P) / N, sum(v * v for v in p.values())
    return round((Pb - Pe) / (1 - Pe), 3) if Pe < 1 else 1.0


out = {'평가자': list(raters), '지문수': len(ids)}
for key in ('content', 'structure_main', 'main_idea_position', 'main_idea_explicit', 'abstractness', 'topic_area'):
    rows = [[raters[r][i][key] for r in raters] for i in ids]
    pair = [sum(a == b for a, b in itertools.combinations(row, 2)) / (len(row) * (len(row) - 1) / 2) for row in rows]
    major = [C.Counter(row).most_common(1)[0][1] for row in rows]
    out[key] = {'짝 일치율 %': round(sum(pair) / len(pair) * 100, 1), 'Fleiss kappa': fleiss([C.Counter(r) for r in rows]),
                '과반(3/5 이상) 동의 지문 %': round(sum(m * 2 > len(raters) for m in major) / len(ids) * 100, 1),
                '전원 일치 지문 %': round(sum(m == len(raters) for m in major) / len(ids) * 100, 1)}
# 구성(structure_main)이 갈린 지문 목록과 의견들
split = {i: C.Counter(raters[r][i]['structure_main'] for r in raters) for i in ids}
out['구성 갈린 지문'] = {i: dict(c) for i, c in split.items() if c.most_common(1)[0][1] * 2 <= len(raters)}
out['구성 혼동 짝'] = C.Counter(tuple(sorted(p)) for c in split.values() for p in itertools.combinations(list(c.elements()), 2) if p[0] != p[1]).most_common(10)
json.dump(out, open('규격/구성분석/일치율' + ('_' + sys.argv[1].replace(',', '_') if want else '') + '.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
for k, v in out.items():
    if k not in ('구성 갈린 지문',):
        print(k, v)
