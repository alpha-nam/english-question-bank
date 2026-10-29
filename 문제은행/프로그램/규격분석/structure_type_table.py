"""평가원 읽기 지문 700개의 내용·구성 분류(유형을 가리고 한 것)를 실제 출제 유형과 짝지어 센다.
입력: 규격/구성분석/결과/확정.jsonl(finalize_structure.py 결과), DB/기출 (type_std)
출력: 규격/구성분석/구성_유형_표.json, 화면 요약"""
import json, glob, collections as C, statistics as st

rows = [json.loads(l) for l in open('규격/구성분석/결과/확정.jsonl', encoding='utf-8') if l.strip()]
for r in rows:
    r['structure_main'] = r['structure_final']   # 복합은 '복합(A+B)' 그대로 한 칸으로 센다



def type_of(i):
    r = json.load(open(f'DB/기출/{i[:7]}/{i}.json', encoding='utf-8'))
    return r.get('type_std') or '미분류'


for r in rows:
    r['type'] = type_of(r['id'])
types = C.Counter(r['type'] for r in rows)
out = {'지문수': len(rows), '유형별 지문수': dict(types.most_common())}


def table(key):
    """key 값마다 실제 유형 분포, 그리고 유형마다 key 분포와 '전체 대비 배율'(lift)"""
    base = C.Counter(r[key] for r in rows)
    by_val = {v: dict(C.Counter(r['type'] for r in rows if r[key] == v).most_common()) for v in base}
    by_type = {}
    for t in types:
        sub = [r for r in rows if r['type'] == t]
        cnt = C.Counter(r[key] for r in sub)
        by_type[t] = [(v, n, round((n / len(sub)) / (base[v] / len(rows)), 1)) for v, n in cnt.most_common()]
    return {'값별 유형': by_val, '유형별 값(개수, 배율)': by_type}


for key in ('content', 'structure_main', 'main_idea_position', 'main_idea_explicit', 'abstractness'):
    out[key] = table(key)
out['유형별 숫자 평균'] = {t: {k: round(st.mean(r[k] for r in rows if r['type'] == t), 1)
                         for k in ('key_paraphrase_pairs', 'explicit_links', 'n_sentences', 'words')}
                     for t in types}
json.dump(out, open('규격/구성분석/구성_유형_표.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

READING = ['빈칸 추론', '글의 순서 배열', '주어진 문장 넣기', '요지 파악', '주제 추론', '제목 추론', '요약문 완성',
           '무관한 문장 찾기', '어법 판단', '어휘의 적절성', '필자의 주장', '함축 의미 추론']
for t in READING:
    if t not in types:
        continue
    s = out['structure_main']['유형별 값(개수, 배율)'][t][:4]
    c = out['content']['유형별 값(개수, 배율)'][t][:3]
    print(f"{t}({types[t]}): 구성 {s} | 내용 {c} | 숫자 {out['유형별 숫자 평균'][t]}")
