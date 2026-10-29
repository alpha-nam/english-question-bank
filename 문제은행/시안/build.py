"""시안 만들기(한 파일로 계속 고침, 2026-10-29부터 번호 없음): 시안.template.html 에 데이터를 넣는다. 독해 지문마다 '내용이 비슷한 기출'(TF-IDF 코사인 상위 4개)을 계산해 sim 칸으로 붙인다."""
import json, math, os, re
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
t = open(os.path.join(HERE, '시안.template.html'), encoding='utf-8').read()
import sys
EXAMPLE = '--예시' in sys.argv          # 공개용: 예시자료/의 가짜 지문으로 만든다
SRC = os.path.join(HERE, '예시자료') if EXAMPLE else HERE
data = json.load(open(os.path.join(SRC, '_data.json'), encoding='utf-8'))
book = json.load(open(os.path.join(SRC, '_book_sample.json'), encoding='utf-8'))
bp = json.load(open(os.path.join(HERE, '_blueprint.json'), encoding='utf-8'))

STOP = set('''a an the and or but if of to in on at by for with from as is are was were be been being it its this that these those he she they we you i his her their our your my me him them us not no nor so than then there here what which who whom whose when where why how all any both each few more most other some such only own same too very can will just should would could may might must do does did have has had having into over under again further once about against between through during before after above below up down out off also because while until even though although whether however therefore thus one two'''.split())


def toks(s):
    return [w for w in re.findall(r"[a-z]+", (s or '').lower()) if len(w) > 2 and w not in STOP]


docs = [(i, d) for i, d in enumerate(data) if int(d.get('no') or 0) >= 18 and len(d.get('body') or '') >= 300]
tf = {i: Counter(toks(d['body'])) for i, d in docs}
df = Counter(w for c in tf.values() for w in c)
N = len(docs)
vec = {}
for i, c in tf.items():
    v = {w: (1 + math.log(n)) * math.log(N / df[w]) for w, n in c.items() if df[w] > 1}
    norm = math.sqrt(sum(x * x for x in v.values())) or 1
    vec[i] = {w: x / norm for w, x in v.items()}
for i, d in docs:
    vi = vec[i]
    sc = []
    for j, e in docs:
        if j == i or e['id'] == d['id']:
            continue
        vj = vec[j]
        small, big = (vi, vj) if len(vi) < len(vj) else (vj, vi)
        s = sum(x * big.get(w, 0) for w, x in small.items())
        if s >= 0.12:
            sc.append((s, e['id']))
    sc.sort(reverse=True)
    d['sim'] = [[k, round(s, 2)] for s, k in sc[:4]]
topics = json.load(open(os.path.join(HERE, '_topics.json'), encoding='utf-8'))
for d in data:
    if d['id'] in topics:
        d['topic'] = topics[d['id']]
BK = os.path.join(HERE, '..', 'DB', '교재', '2027특강영어')
for b in book:
    m = re.search(r'\((\d{5}-\d{4})\)', b.get('code', ''))
    p = os.path.join(BK, m.group(1) + '.json') if m else ''
    if p and os.path.exists(p):
        hs = json.load(open(p, encoding='utf-8')).get('해설') or ''
        t2 = re.search(r'\[소재\]\s*([^\n\[]+)', hs)
        if t2:
            b['topic'] = re.sub(r'Exercises.*$', '', t2.group(1)).strip()  # 26005-0057 소재 끝에 붙은 'Exercises본문 74~75쪽' 제거
print('소재: 기출', sum(1 for d in data if d.get('topic')), '교재', sum(1 for b in book if b.get('topic')), '/', len(book))
print('지문', N, '비슷한 짝 있는 지문', sum(1 for _, d in docs if d.get('sim')))
j = lambda x: json.dumps(x, ensure_ascii=False).replace('</', '<\\/')
out = t.replace('__DATA__', j(data)).replace('__BOOK__', j(book)).replace('__BP__', j(bp))
open(os.path.join(HERE, '예시_화면시안.html' if EXAMPLE else '문제은행_화면시안.html'), 'w', encoding='utf-8').write(out)
print(len(out) // 1024, 'KB')
