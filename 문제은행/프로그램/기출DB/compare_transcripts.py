"""스캔본 3중 대조: 전사A(전사_시험.json), 전사B(전사B_시험.json), 기존 OCR(ocr_text).
영어 낱말 열을 맞춰 보고, A·B가 다른 곳을 문항별로 뽑는다. OCR은 다수결 보조로만 쓴다.
사용: python -X utf8 -I compare_transcripts.py 2020.12"""
import difflib, json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
exam = sys.argv[1]
A = json.load(open(os.path.join(ROOT, 'DB', '통계', f'전사_{exam}.json'), encoding='utf-8'))
B = json.load(open(os.path.join(ROOT, 'DB', '통계', f'전사B_{exam}.json'), encoding='utf-8'))


def words(it):
    s = ' '.join([it.get('stem') or '', it.get('body') or '', it.get('group_passage') or '', ' '.join(it.get('choices') or [])])
    s = re.sub(r'<[^>]+>', ' ', s).replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return re.findall(r"[A-Za-z0-9가-힣']+|[①-⑤]", s)


report, total, agree = {}, 0, 0
for i in sorted(A):
    wa, wb = words(A[i]), words(B.get(i, {}))
    ocr = json.load(open(os.path.join(ROOT, 'DB', '기출', exam, f'{i}.json'), encoding='utf-8'))['text'].get('ocr_text') or ''
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    diffs = []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op != 'equal':
            ta, tb = ' '.join(wa[a1:a2]), ' '.join(wb[b1:b2])
            diffs.append({'A': ta, 'B': tb, 'OCR가 A와': bool(ta) and ta in ocr, 'OCR가 B와': bool(tb) and tb in ocr,
                          '앞': ' '.join(wa[max(0, a1 - 4):a1])})
    total += max(len(wa), len(wb)); agree += sum(b[2] for b in sm.get_matching_blocks())
    pts = (A[i].get('points'), B.get(i, {}).get('points'))
    if diffs or pts[0] != pts[1] or bool(A[i].get('choices')) != bool(B.get(i, {}).get('choices')):
        report[i] = {'다른곳': diffs, '배점': pts}
out = os.path.join(ROOT, 'DB', '통계', f'전사대조_{exam}.json')
json.dump(report, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(exam, '낱말 일치율', round(agree / total * 100, 2), '%', '다른 문항', len(report), '다른 곳', sum(len(v['다른곳']) for v in report.values()))
