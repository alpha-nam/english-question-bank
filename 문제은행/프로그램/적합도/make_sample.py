"""역검증용 지문 표본을 만든다: 10개 유형에서 유형마다 20지문(평가원, 무작위), 원래 글로 되돌려 문장 번호를 붙인다.
AI가 문항 번호·유형을 알 수 없도록 P001 같은 가명을 쓰고, 가명↔문항 대응은 비공개/ 폴더에만 둔다."""
import json, glob, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import restore as R
T = ['빈칸 추론', '글의 순서 배열', '주어진 문장 넣기', '요지 파악', '주제 추론', '제목 추론', '요약문 완성', '무관한 문장 찾기', '어법 판단', '어휘의 적절성']
SPLIT = re.compile(r'(?<!\b[A-Z]\.)(?<!\bDr\.)(?<!\bMr\.)(?<!\bMs\.)(?<!\bMrs\.)(?<!\bSt\.)(?<=[.?!])["”’)]?\s+(?=["“‘(]?[A-Z])')   # R. A. Bjork 같은 머리글자는 자르지 않는다


def sentences(text):
    out = []
    text = re.sub(r'(?<![.?!"”’])\s*\n\s*', ' ', text)      # 문장 중간에서 끊긴 줄은 잇는다
    for para in text.split('\n'):
        out += [s.strip() for s in SPLIT.split(para) if s.strip()]
    return out


pool = {t: [] for t in T}
for p in sorted(glob.glob(os.path.join(R.ROOT, 'DB', '기출', '*', '*-*.json'))):
    r = json.load(open(p, encoding='utf-8'))
    if r['exam']['기관'] == '평가원' and r.get('type_std') in T and r['no'] <= 40 and r['id'] != '2023.06-30':
        pool[r['type_std']].append(r)
random.seed(20261028)
picked = [r for t in T for r in random.sample(pool[t], 20)]
random.shuffle(picked)
key, rows = {}, []
for k, r in enumerate(picked, 1):
    pid = f'P{k:03d}'
    key[pid] = {'id': r['id'], 'type': r['type_std']}
    rows.append({'pid': pid, 'sentences': sentences(R.restore(r))})
root = os.path.join(R.ROOT, '규격', '적합도')
with open(os.path.join(root, '입력', '지문.jsonl'), 'w', encoding='utf-8') as f:
    for x in rows:
        f.write(json.dumps(x, ensure_ascii=False) + '\n')
json.dump(key, open(os.path.join(root, '비공개', '가명표.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(rows), '지문', sum(len(x['sentences']) for x in rows) / len(rows), '문장/지문')
