"""시안용 문항 데이터(_data.json)를 만든다. 2024~2026 시험.
묶음 문항(듣기 16~17, 장문 41~42, 43~45)은 한 묶음으로 합쳐 공통 지문 한 번 + 문항 여러 개(qs)로 둔다.
정답률·선택 비율은 EBSi 오답률 TOP15(wrong_rate)만 쓴다(메가스터디는 쓰지 않음)."""
import glob, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
GROUPS = {16: [16, 17], 41: [41, 42], 43: [43, 44, 45]}
SHORT = {'빈칸 추론': '빈칸', '글의 순서 배열': '순서', '주어진 문장 넣기': '삽입', '요지 파악': '요지', '주제 추론': '주제', '제목 추론': '제목',
         '요약문 완성': '요약문', '무관한 문장 찾기': '무관한 문장', '어법 판단': '어법', '어휘의 적절성': '어휘', '필자의 주장': '주장', '함축 의미 추론': '함축',
         '글의 목적 파악': '목적', '심경·분위기 파악': '심경', '도표 내용 일치': '도표', '글의 세부 내용 일치': '내용 일치', '안내문 내용 일치': '안내문',
         '장문: 제목 추론': '제목', '장문: 어휘 추론': '어휘', '장문: 글의 순서': '순서', '장문: 지칭 추론': '지칭', '장문: 세부 내용 파악': '내용 일치'}


def load(e, no):
    return json.load(open(os.path.join(ROOT, 'DB', '기출', e, f'{e}-{no:02d}.json'), encoding='utf-8'))


def top(r):
    w = r.get('wrong_rate')
    return {'rank': w['순위'], 'wr': w['오답률'], 'sel': w['선택지비율']} if w else None


rows = []
for exam in sorted(os.path.basename(d) for d in glob.glob(os.path.join(ROOT, 'DB', '기출', '202[4-6].*'))):
    done = set()
    for no in range(1, 46):
        p = os.path.join(ROOT, 'DB', '기출', exam, f'{exam}-{no:02d}.json')
        if not os.path.exists(p) or no in done:
            continue
        r = load(exam, no)
        t = r['text']
        members = GROUPS.get(no)
        if members:
            ms = [load(exam, n) for n in members if os.path.exists(os.path.join(ROOT, 'DB', '기출', exam, f'{exam}-{n:02d}.json'))]
            done.update(members)
            qs = [{'no': m['no'], 'stem': (m['text'].get('stem') or '').replace('\n', ''), 'ch': m['text'].get('choices'), 'ans': m.get('answer'),
                   'short': SHORT.get(m.get('type_std') or '', m.get('type_std') or ''), 'pts': m.get('points'), 'top': top(m)} for m in ms]
            tops = [q['top'] for q in qs if q['top']]
            if no == 16:
                body = ''
            else:
                body = t.get('group_passage') or ''
            img = r.get('image') or ''
            rows.append({'id': r['id'], 'exam': r['exam'].get('명칭'), 'org': r['exam']['기관'], 'yr': r['exam']['학년도'], 'no': no,
                         'label': f'{members[0]}~{members[-1]}번', 'type': r.get('type_std'), 'short': ('듣기 ' if no == 16 else '장문 ') + '·'.join(q['short'] for q in qs),
                         'pts': None, 'ans': None, 'top': min(tops, key=lambda x: x['rank']) if tops else None,
                         'stem': '', 'body': body, 'ch': None, 'qs': qs, 'img': ('../../' + img) if img else '',
                         'imgs': list(dict.fromkeys(('../../' + m['image']) for m in ms if m.get('image')))})
            continue
        img = r.get('image') or ''
        rows.append({'id': r['id'], 'exam': r['exam'].get('명칭'), 'org': r['exam']['기관'], 'yr': r['exam']['학년도'], 'no': no, 'type': r.get('type_std'),
                     'pts': r.get('points'), 'ans': r.get('answer'), 'top': top(r), 'stem': (t.get('stem') or '').replace('\n', ''),
                     'body': t.get('body') or '', 'ch': t.get('choices'), 'img': ('../../' + img) if img else ''})
# 연계 분석(연계DB): 평가원 2024.06~2026.09 8회, 문항마다 연계 방식·교재·쪽·근거
import csv, re
link = {}
for r in csv.DictReader(open(os.path.join(ROOT, '..', '연계DB', '연계DB_통합_전체문항.csv'), encoding='utf-8-sig')):
    m = re.match(r'(\d+)(?:\D+(\d+))?', r['문항'])
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    link[(r['시험'], a)] = {'how': r['연계방식'], 'book': r['교재'], 'page': r['쪽'], 'type': r['시험유형'], 'why': r['근거'][:160], 'change': r['바뀐점'][:160], 'last': b}
for x in rows:
    k = (x['id'][:7], x['no'])
    if k in link:
        x['lk'] = link[k]
    for q in x.get('qs') or []:                 # 2026-10-29: 묶음 안 44·45번 등 문항별 연계 근거도 살림(2025년부터 따로 적혀 있음)
        kq = (x['id'][:7], q['no'])
        if kq in link and kq != k:
            q['lk'] = link[kq]
json.dump(rows, open(os.path.join(HERE, '_data.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(len(rows), sum(1 for x in rows if x.get('qs')), sum(1 for x in rows if x['top']), sum(1 for x in rows if x.get('lk')))
