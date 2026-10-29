"""음성 대조군 표본: 읽기 문항 중 10개 대상 유형이 아닌 것(글의 목적, 심경, 도표, 세부 내용, 안내문, 장문 이야기)에서 유형마다 10지문.
가명 N001…, 대응표는 비공개/대조군_가명표.json."""
import json, glob, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import restore as R
from make_sample import sentences
CTRL = ['글의 목적 파악', '심경·분위기 파악', '도표 내용 일치', '글의 세부 내용 일치', '안내문 내용 일치', '장문: 글의 순서']
pool = {t: [] for t in CTRL}
for p in sorted(glob.glob(os.path.join(R.ROOT, 'DB', '기출', '*', '*-*.json'))):
    r = json.load(open(p, encoding='utf-8'))
    if r['exam']['기관'] == '평가원' and r.get('type_std') in CTRL and r['text'].get('text_quality') != 'ocr':
        pool[r['type_std']].append(r)
random.seed(7)
picked = [r for t in CTRL for r in random.sample(pool[t], 10)]
random.shuffle(picked)
key, rows = {}, []
for k, r in enumerate(picked, 1):
    t = r['text']
    body = t.get('group_passage') if r['no'] == 43 else t.get('body') or ''
    if r['type_std'] == '도표 내용 일치' and t.get('choices'):
        body = body + ' ' + ' '.join(t['choices'])
    if r['type_std'] == '장문: 글의 순서':          # 시험지는 (B)(C)(D)가 섞여 있으므로 43번 정답 순서로 잇는다
        segs = dict(re.findall(r'\(([A-D])\)\s*(.*?)(?=\n?\([A-D]\)|$)', body, re.S))
        order = ['A'] + re.findall(r'[B-D]', t['choices'][R.CIR.index(r['answer'])])
        body = '\n'.join(segs.get(x, '').strip() for x in order)
    pid = f'N{k:03d}'
    key[pid] = {'id': r['id'], 'type': r['type_std']}
    rows.append({'pid': pid, 'sentences': sentences(R.clean(re.sub(r'\n\*[^\n]*', '', body)))})
root = os.path.join(R.ROOT, '규격', '적합도')
with open(os.path.join(root, '입력', '대조군.jsonl'), 'w', encoding='utf-8') as f:
    for x in rows:
        f.write(json.dumps(x, ensure_ascii=False) + '\n')
json.dump(key, open(os.path.join(root, '비공개', '대조군_가명표.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(rows), {t: len(pool[t]) for t in CTRL})
