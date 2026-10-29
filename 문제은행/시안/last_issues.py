"""마지막 감사 기록에서 문제가 있는 곳만 요약해 보여 준다."""
import json
rec = [json.loads(l) for l in open('검토/감사기록.jsonl', encoding='utf-8')][-1]
print(rec['label'])
for d in rec['rows']:
    if 'error' in d:
        print(d)
        continue
    bad = []
    if d['hscroll']: bad.append('가로스크롤')
    for k, v in d['align'].items():
        if isinstance(v, dict) and (v.get('misaligned_rows') or v.get('uneven_gap_rows')): bad.append(f'{k}:{v}')
    if d['contrast']['fail']: bad.append(f"대비 {d['contrast']['worst'][:2]}")
    if d['targets']['under24']: bad.append(f"24미만 {d['targets']['small'][:3]}")
    if d['overflow']: bad.append(f"잘림 {d['overflow'][:2]}")
    if bad: print(d['scene'], d['w'], bad)
