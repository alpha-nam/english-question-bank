"""구성 분류 확정: v1(team*), v2(v2team*), 판정자(adj*)를 합친다.
- v1 = v2 → 그 구성(확신: 일치)
- 다르면 판정자가 v2와 같으면 v2, v1과 같으면 v1(확신: 다수결)
- 셋 다 다르면 '복합'(v2 + 판정자, 확신: 애매)
나머지 칸(내용, 주제문 위치 등)은 v2 값을 쓴다. 결과: 규격/구성분석/결과/확정.jsonl"""
import json, glob, collections as C
load = lambda pat: {json.loads(l)['id']: json.loads(l) for f in glob.glob(pat) for l in open(f, encoding='utf-8')}
v1, v2, adj = load('규격/구성분석/결과/team*.jsonl'), load('규격/구성분석/결과/v2team*.jsonl'), load('규격/구성분석/결과/adj*.jsonl')
out, cnt = [], C.Counter()
for i, r in sorted(v2.items()):
    a, b = v1[i]['structure_main'], r['structure_main']
    if a == b:
        s, conf, parts = b, '일치', [b]
    elif i in adj and adj[i]['structure_main'] == b:
        s, conf, parts = b, '다수결', [b]
    elif i in adj and adj[i]['structure_main'] == a:
        s, conf, parts = a, '다수결', [a]
    elif i in adj:
        parts = sorted({b, adj[i]['structure_main']})
        s, conf = '복합(' + '+'.join(parts) + ')', '애매'
    else:
        s, conf, parts = b, '판정 대기', [b]
    cnt[conf] += 1
    out.append({**r, 'structure_final': s, 'structure_parts': parts, 'structure_confidence': conf,
                'structure_votes': {'v1': a, 'v2': b, '판정자': adj.get(i, {}).get('structure_main')}})
with open('규격/구성분석/결과/확정.jsonl', 'w', encoding='utf-8') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(dict(cnt), '복합 예:', [r['structure_final'] for r in out if r['structure_confidence'] == '애매'][:5])
