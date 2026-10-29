"""교재 20지문 분석 결과를 제이님 확인용 표(md)로 만든다. 원래 교재 유형은 맨 끝에 따로 둔다(먼저 보지 않고 판단하시도록)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge as J, rank as K, judge_sets as S

lift = J.lift_table()
ref = K.reference(lift)
runs = S.load('book', None)
key = json.load(open(os.path.join(J.ROOT, '규격', '적합도', '비공개', '교재20_가명표.json'), encoding='utf-8'))
src = {json.loads(l)['pid']: json.loads(l) for l in open(os.path.join(J.ROOT, '규격', '적합도', '입력', '교재20.jsonl'), encoding='utf-8')}
short = {'빈칸 추론': '빈칸', '글의 순서 배열': '순서', '주어진 문장 넣기': '삽입', '요지 파악': '요지', '주제 추론': '주제', '제목 추론': '제목',
         '요약문 완성': '요약문', '무관한 문장 찾기': '무관', '어법 판단': '어법', '어휘의 적절성': '어휘'}
L = ['# 유형 적합도 분석기: 2027 수능특강 20지문 확인표', '',
     '지문마다 **추천 3개**가 이 글로 만들기에 괜찮은지 O / X 로 표시해 주세요. 더 어울리는 유형이 있으면 적어 주세요.',
     '원래 교재에서 어떤 유형이었는지는 맨 아래에 있습니다. 먼저 보지 않고 판단해 주시면 검증이 정확해집니다.', '']
summary = []
for pid in sorted(src):
    f = S.finalize(runs, pid, lift, J.verdicts)
    rich = K.mean_richness(runs, pid, lift)
    rec = K.recommend(f, rich, ref)
    a = runs['A'][pid]
    text = ' '.join(src[pid]['sentences'])
    L += [f'## {pid}', '', f'> {text}', '',
          f"- 글: {a.get('content')} / 구성: {a.get('structure_main')}" + (f" (+{a.get('structure_sub')})" if a.get('structure_sub') not in (None, '없음') else ''),
          f"- 중심 생각: {(a.get('main_idea') or {}).get('statement_ko', '')}", '',
          '| 추천 | 근거 | O/X |', '|---|---|---|']
    for t in rec:
        L.append(f'| {short[t]} | {f[t][1]} | |')
    L += ['', '판정 전체: ' + ', '.join(f'{short[t]} {f[t][0]}' for t in J.TYPES), '', '더 어울리는 유형: ', '']
    summary.append((pid, [short[t] for t in rec], key[pid]['원래 유형'], f"{key[pid]['쪽']}쪽 {key[pid].get('강', '')} {key[pid].get('번호', '')}"))
L += ['---', '', '## 정답 공개: 원래 교재 유형', '', '| 지문 | 추천 3개 | 원래 교재 유형 | 출처 |', '|---|---|---|---|']
L += [f'| {p} | {", ".join(r)} | {o} | {s} |' for p, r, o, s in summary]
hit = sum(1 for p, r, o, s in summary if any(short.get(o, o) in x or x in o for x in r))
L += ['', f'참고: 원래 교재 유형이 추천 3개에 든 지문 {hit}/20. (원래 유형만 정답인 것은 아니므로 이 숫자보다 선생님 O/X가 기준입니다.)']
out = os.path.join(J.ROOT, '규격', '적합도', '교재20_확인표.md')
open(out, 'w', encoding='utf-8').write('\n'.join(L))
print(out, hit)
