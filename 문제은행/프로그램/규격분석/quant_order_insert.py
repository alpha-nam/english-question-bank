"""글의 순서 배열(36·37번)과 주어진 문장 넣기(38·39번) 기출의 숫자 파악 (평가원 29회)."""
import collections, glob, json, os, re, statistics as S
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
CIRC = '①②③④⑤'


def words(t):
    return len(re.findall(r"[A-Za-z’']+", t))


def first_words(t, n=2):
    return ' '.join(re.findall(r"[A-Za-z’']+", t)[:n])


def load(types):
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'DB', '기출', '*', '*-*.json'))):
        if p.endswith('_시험.json'):
            continue
        r = json.load(open(p, encoding='utf-8'))
        if r['exam'].get('기관') != '평가원' or r['text'].get('text_quality') == 'ocr':
            continue
        if r['type_std'] in types and r['no'] <= 39:
            out.append(r)
    return out


def order_items():
    rows = []
    for r in load(('글의 순서 배열',)):
        body = [x for x in r['text']['body'].split('\n') if x.strip() and not x.startswith('*')]
        given = body[0]
        seg = {}
        for ln in body[1:]:
            m = re.match(r'^\(([A-C])\)\s*(.*)', ln)
            if m:
                seg[m.group(1)] = m.group(2)
        if set(seg) != set('ABC') or not r['answer']:
            continue
        ans = r['text']['choices']['①②③④⑤'.index(r['answer'])]
        perm = ''.join(re.findall(r'\(([A-C])\)', ans))
        rows.append(dict(id=r['id'], no=r['no'], given=words(given), seg={k: words(v) for k, v in seg.items()}, perm=perm,
                         first=first_words(seg[perm[0]], 2), starts={k: first_words(v, 2) for k, v in seg.items()},
                         rate=(100 - r['wrong_rate']['오답률'] if r.get('wrong_rate') else None), offered=sorted(''.join(re.findall(r'\(([A-C])\)', c)) for c in r['text']['choices'])))
    return rows


def insert_items():
    rows = []
    for r in load(('주어진 문장 넣기',)):
        body = [x for x in r['text']['body'].split('\n') if x.strip() and not x.startswith('*')]
        if len(body) < 2 or not r['answer']:
            continue
        given, passage = body[0], ' '.join(body[1:])
        pos = [m.start() for m in re.finditer(r'\(\s*[①②③④⑤]\s*\)', passage)]
        if len(pos) != 5:
            continue
        ans = CIRC.index(r['answer'])
        # 정답 위치 앞뒤 문장
        rows.append(dict(id=r['id'], no=r['no'], given_words=words(given), passage_words=words(passage), ans=ans + 1,
                         given_start=first_words(given, 2), rate=(100 - r['wrong_rate']['오답률'] if r.get('wrong_rate') else None),
                         ans_rel=round(pos[ans] / len(passage), 2)))
    return rows


if __name__ == '__main__':
    o = order_items()
    print('글의 순서 배열', len(o), '문항')
    print(' 주어진 글 단어', round(S.mean(x['given'] for x in o)), '| 각 문단 단어', {k: round(S.mean(x['seg'][k] for x in o)) for k in 'ABC'},
          '| 전체', round(S.mean(x['given'] + sum(x['seg'].values()) for x in o)))
    print(' 정답 순서', collections.Counter(x['perm'] for x in o).most_common())
    print(' 정답의 첫 문단', collections.Counter(x['perm'][0] for x in o).most_common())
    print(' 정답 첫 문단의 시작 낱말', collections.Counter(x['first'] for x in o).most_common(12))
    print(' 선택지에 안 나온 순열', collections.Counter(''.join(sorted(set(['ABC', 'ACB', 'BAC', 'BCA', 'CAB', 'CBA']) - set(x['offered']))) for x in o).most_common(6))
    rs = [x['rate'] for x in o if x['rate'] is not None]
    print(' 정답률 평균', round(S.mean(rs), 1), '범위', min(rs), max(rs), '| 번호별', {n: round(S.mean(x['rate'] for x in o if x['no'] == n and x['rate'] is not None), 1) for n in (36, 37)})
    ins = insert_items()
    print('주어진 문장 넣기', len(ins), '문항')
    print(' 주어진 문장 단어', round(S.mean(x['given_words'] for x in ins)), '| 지문 단어', round(S.mean(x['passage_words'] for x in ins)))
    print(' 정답 위치', sorted(collections.Counter(x['ans'] for x in ins).items()))
    print(' 주어진 문장 시작', collections.Counter(x['given_start'] for x in ins).most_common(14))
    rs = [x['rate'] for x in ins if x['rate'] is not None]
    print(' 정답률 평균', round(S.mean(rs), 1), '범위', min(rs), max(rs), '| 번호별', {n: round(S.mean(x['rate'] for x in ins if x['no'] == n and x['rate'] is not None), 1) for n in (38, 39)})
    by = collections.defaultdict(list)
    for x in ins:
        by[x['ans']].append(x['rate'])
    print(' 정답 위치별 평균 정답률', {k: round(S.mean(v), 1) for k, v in sorted(by.items())})
