"""만든 시험 DB를 다른 출처와 대조한다 (시범판).
1) 문항 수·번호  2) 선택지 5개/발문  3) 정답 = 해설표(이미 같은 출처이므로 기존 CSV와도 대조)
4) EBSi 오답률 TOP15의 (번호, 정답, 배점)  5) 기존 기출문항DB.csv의 정답·배점·유형  6) 이미지 파일 존재
사용: python -X utf8 -I verify_exam.py 2026.09
"""
import csv, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
exam = sys.argv[1]
d = os.path.join(ROOT, '문제은행', 'DB', '기출', exam)
recs = {}
for n in range(1, 46):
    p = os.path.join(d, f'{exam}-{n:02d}.json')
    if os.path.exists(p):
        recs[n] = json.load(open(p, encoding='utf-8'))
out = []
out.append(('문항 수', len(recs), 45, len(recs) == 45))
bad = []
for n, r in recs.items():
    c = r['text']['choices']
    ok = (c is not None and len(c) == 5 and all(c)) or r['text']['choices_in_text'] or r['text']['choices_in_image'] or r['text'].get('choices_in_table')
    if r['text'].get('text_quality') == 'ocr':      # 스캔본: 글자는 OCR 결과(참고용), 선택지는 나누지 않는다
        ok = bool(r['text'].get('ocr_text'))
    if not ok or not r['text']['stem'] or (len(r['text']['stem']) > 200 and r['text'].get('text_quality') != 'ocr'):
        bad.append(n)
out.append(('선택지·발문 이상', bad, [], not bad))
# TOP15
top = json.load(open(os.path.join(ROOT, '문제은행', 'DB', '통계', 'ebsi_오답률TOP15_원본.json'), encoding='utf-8'))
y, mo = exam.split('.')
sys.path.insert(0, HERE)
key = None
for mm in ([9] if exam == '2022.08' else [int(mo), int(mo) - 1]):
    key = next((k for k in top if k[:4] == y and int(k[4:6]) == mm), None)
    if key:
        break
if key is None:   # 6월 4일 같은 일자 표기: 연도 + 월
    cand = [k for k in top if k.startswith(y + f'{int(mo):02d}')]
    key = cand[0] if cand else None
bad = []
if key:
    for rk in top[key]['rows']:
        rank, no, rate, pts, ans = rk[:5]
        r = recs.get(no)
        if not r or r['answer'] != ans or r['points'] != pts:
            bad.append((no, ans, pts, r and (r['answer'], r['points'])))
    out.append((f'TOP15 대조({key})', len(top[key]['rows']), 15, not bad))
    out.append(('TOP15 불일치', bad, [], not bad))
else:
    out.append(('TOP15', '없음', '', False))
# 기존 CSV
csvp = os.path.join(ROOT, '연계DB', '문항DB', '기출문항DB.csv')
bad = []
for row in csv.DictReader(open(csvp, encoding='utf-8-sig')):
    if row['시험'] != exam:
        continue
    n = int(re.match(r'\d+', row['문항']).group())
    r = recs.get(n)
    if not r:
        continue
    a = '①②③④⑤'[int(row['정답']) - 1] if row['정답'].isdigit() else row['정답']
    if r['answer'] != a or str(r['points']) != row['배점'] or (r['type'] or '') != row['출제의도(유형)']:
        bad.append((n, (r['answer'], r['points'], r['type']), (a, row['배점'], row['출제의도(유형)'])))
out.append(('기존 CSV 불일치', bad, [], not bad))
miss = [n for n in recs if not recs[n]['image'] or not os.path.exists(os.path.join(ROOT, recs[n]['image']))]
out.append(('이미지 없음', miss, [], not miss))
for name, got, want, ok in out:
    print(('OK  ' if ok else 'FAIL') + f' {name}: {got}' + ('' if ok or want == [] else f' (기대 {want})'))
