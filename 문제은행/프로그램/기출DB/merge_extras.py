"""변환(build_exam) 뒤에 따로 붙이는 정보를 문항 JSON에 다시 합친다: 빈칸 분석 결과의 빈칸 위치, 스캔본 전사, 수동 입력, EBSi TOP15 표시, 시험 이름.
변환을 다시 돌리면 이 칸이 지워지므로 `run_all` 뒤에 `apply_std_types.py`, `merge_extras.py` 순서로 실행한다."""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import std_types
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DB = os.path.join(ROOT, 'DB', '기출')
# 메가스터디 정답률은 쓰지 않는다(2026-10-28 제이님 결정: 이용자 채점 집계라 상위권 쏠림, EBSi보다 평균 13.4점 높음).
# 원본은 DB/통계/megastudy_정답률_영어_원본.json 에 기록용으로만 남긴다. 예전에 붙인 칸은 아래에서 지운다.
b = 0
for k in range(1, 5):
    fp = os.path.join(ROOT, '규격', '빈칸분석', '결과', f'team{k}.jsonl')
    if not os.path.exists(fp):
        continue
    for line in open(fp, encoding='utf-8'):
        r = json.loads(line)
        p = os.path.join(DB, r['id'][:7], r['id'] + '.json')
        rec = json.load(open(p, encoding='utf-8'))
        rec['blank_info'] = {'sentence_no': r['blank']['sentence_no'], 'n_sentences': r['blank']['n_sentences'], 'position': r['blank']['position'],
                             'sentence': r['blank']['sentence'], 'confirmed_by': r['blank']['confirmed_by']}
        body = rec['text'].get('body') or ''
        if '＿＿＿' not in body and '＿＿＿' in r['blank']['sentence']:      # 변환에서 빈칸 자리를 못 찾은 옛 시험: 분석 결과의 빈칸 문장으로 표시를 넣는다
            pre, post = [x.strip() for x in r['blank']['sentence'].split('＿＿＿', 1)]
            m = re.search(re.escape(pre[-25:]) + r'\s*(?=' + re.escape(post[:15] or '.') + ')', body) if pre else None
            if m:
                rec['text']['body'] = body[:m.end()] + ' ＿＿＿ ' + body[m.end():]
                rec['text']['blank'] = '분석으로 복원'
        json.dump(rec, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        b += 1
print('빈칸 정보', b)

# 스캔본 이미지 전사(2026-10-28): AI 2명이 따로 옮겨 적고(전사_*.json, 전사B_*.json) compare_transcripts.py 로 대조한 결과.
# 영어 본문이 두 전사에서 일치한 시험만 반영한다. 직접 붙여넣은 수동입력이 있으면 그쪽이 우선(아래에서 다시 덮어씀).
for fa in glob.glob(os.path.join(ROOT, 'DB', '통계', '전사_*.json')):
    ex = os.path.basename(fa)[3:-5]
    if not os.path.exists(os.path.join(ROOT, 'DB', '통계', f'전사대조_{ex}.json')):
        continue
    tr = json.load(open(fa, encoding='utf-8'))
    for i, v in tr.items():
        p = os.path.join(DB, ex, i + '.json')
        if not os.path.exists(p):
            continue
        rec = json.load(open(p, encoding='utf-8'))
        rec['text'].update(stem=v.get('stem'), body=v.get('body') or '', choices=v.get('choices'),
                           group_passage=v.get('group_passage') or None, text_quality='transcribed',
                           choices_in_text=v.get('choices') is None,
                           transcribe_note='시험지 이미지를 AI 2명이 따로 옮겨 적고 대조(DB/통계/전사대조_%s.json)' % ex)
        if v.get('points'):
            rec['points'] = v['points']
        t = std_types.classify_stem(v.get('stem') or '', rec['no'], v.get('body') or '')   # OCR 해설 유형이 밀린 경우가 있어 옮겨 적은 발문으로 다시 정한다
        if t:
            rec['type_std'], rec['type_std_source'] = t, '발문(전사)'
            rec['stem_template'] = std_types.stem_template(v.get('stem') or '')
        json.dump(rec, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('전사 반영', ex, len(tr))

# 제이님이 직접 붙여넣은 문항 글자(스캔본 OCR이 못 읽은 문항). OCR 재변환 뒤에도 다시 덮어쓴다.
man = json.load(open(os.path.join(ROOT, 'DB', '통계', '수동입력_문항글자.json'), encoding='utf-8'))
for i, v in man.items():
    p = os.path.join(DB, i[:7], i + '.json')
    rec = json.load(open(p, encoding='utf-8'))
    rec['text'].update({k: v[k] for k in ('stem', 'body', 'choices')}, text_quality='manual', manual_source=v['입력'], choices_in_text=v['choices'] is None)
    if v.get('type_std'):
        rec['type_std'], rec['type_std_source'] = v['type_std'], '수동'
    json.dump(rec, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('수동 입력', len(man))

# 난이도 표시(2026-10-28 제이님 결정): 등급을 매기지 않고 EBSi 오답률 TOP15 여부만 둔다.
# TOP15 문항은 EBSi가 공개한 순위·오답률·선택지 비율(wrong_rate)을 그대로 보여 주고, 나머지는 '없음'.
# (EBSi 오답률도 공식 정답률이 아니라 EBSi 이용자 채점 집계다.)
cleared = 0
for p in glob.glob(os.path.join(DB, '*', '*-*.json')):
    rec = json.load(open(p, encoding='utf-8'))
    old = {k: rec.pop(k) for k in ('megastudy', 'difficulty') if k in rec}
    rec['ebsi_top15'] = bool(rec.get('wrong_rate'))
    json.dump(rec, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    cleared += bool(old)
print('메가스터디·난이도 칸 지움', cleared, 'TOP15 표시 완료')

# 시험의 원래 이름(2026-10-28): 폴더는 실제 시행 연·월이라, 코로나 등으로 미뤄진 시험은 이름과 달라진다.
# 예) 2020.05 폴더 = 4월 학평(경기, 5.21 시행), 2020.04 = 3월 학평(서울, 4.24 시행), 2022.08 = 9월 모평, 2020.12 = 수능
titles = {}
src = json.dumps(json.load(open(os.path.join(ROOT, '프로그램', '수집', 'ebsi_기출목록.json'), encoding='utf-8')), ensure_ascii=False)
for t in re.findall(r'"(20\d\d)\.(\d+) 고3 ([^"]*?) 영어"', src):
    titles[f'{t[0]}.{int(t[1]):02d}'] = t[2]
named = 0
for p in glob.glob(os.path.join(DB, '*', '*-*.json')):
    rec = json.load(open(p, encoding='utf-8'))
    folder = os.path.basename(os.path.dirname(p))
    mo = int(folder[5:])
    default = '수능' if mo in (11, 12) else (f'{mo}월 모평' if mo in (6, 9) else f'{mo}월 학평')
    rec['exam']['명칭'] = titles.get(folder, default)
    json.dump(rec, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    named += 1
print('시험 명칭', named, '목록에서 찾은 시험', len(titles))
