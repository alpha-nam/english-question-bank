"""모든 문항 JSON에 표준 유형(`type_std`)과 근거(`type_std_source`)를 더한다 (초안).
근거: 공식(평가원 해설의 [출제 의도] 이름 -> 표준 유형) / 발문(발문 글자 규칙) / 없음"""
import collections, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import std_types as T
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(HERE, '..', '..', 'DB', '기출'))
cnt = collections.Counter()
rows = []
for p in sorted(glob.glob(os.path.join(DB, '*', '*-*.json'))):
    if p.endswith('_시험.json'):
        continue
    r = json.load(open(p, encoding='utf-8'))
    official = T.canon_label(r.get('type'), r['no']) if r.get('type') else None
    r['type_official_std'] = official
    r['stem_template'] = T.stem_template(r['text'].get('stem')) if r['text'].get('text_quality') != 'ocr' else None
    by_stem = T.classify_stem(r['text'].get('stem'), r['no'], r['text'].get('body')) if r['text'].get('text_quality') != 'ocr' else None
    std, src = (by_stem, '발문') if by_stem else (official, '공식')
    if std is None:
        std = T.classify_stem(r['text'].get('stem'), r['no'], r['text'].get('body')) if r['text'].get('text_quality') != 'ocr' else None
        src = '발문' if std else '없음'
        if std is None and r.get('intent'):
            std, src = T.canon_intent(r['intent'], r['no']), '출제의도'
            if std is None:
                src = '없음'
        if std is None and r['text'].get('text_quality') != 'ocr' and r['no'] in T.BY_NUMBER:
            std, src = T.BY_NUMBER[r['no']], '번호'
    r['type_std'], r['type_std_source'] = std, src
    json.dump(r, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    cnt[src] += 1
    rows.append((r['id'], r['exam'].get('기관', '평가원'), r['no'], std, src))
print(dict(cnt), len(rows))
json.dump(rows, open(os.path.join(HERE, 'type_std_표.json'), 'w', encoding='utf-8'), ensure_ascii=False)
