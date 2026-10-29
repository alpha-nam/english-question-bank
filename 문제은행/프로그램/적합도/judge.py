"""유형 적합도 판정(v1)과 기출 역검증.
입력: 규격/적합도/결과/run{A,B,C}_{1,2}.jsonl (AI 판정 3회), sup{A,B,C}.jsonl (고친 지문 다시 판정, 있으면 이쪽을 씀)
      규격/구성분석/구성_유형_표.json (구성→유형 배율), 규격/적합도/비공개/가명표.json (정답 유형: 채점에만 씀)
출력: 규격/적합도/검증_v1.json, 화면 요약
판정: 유형마다 필수 조건(없으면 부적합)과 재료(있으면 적합, 모자라면 조건부). 3회 판정은 다수결."""
import collections as C
import glob
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
RES = os.path.join(ROOT, '규격', '적합도', '결과')
TYPES = ['빈칸 추론', '글의 순서 배열', '주어진 문장 넣기', '요지 파악', '주제 추론', '제목 추론', '요약문 완성',
         '무관한 문장 찾기', '어법 판단', '어휘의 적절성']
MAIN = {'요지 파악', '주제 추론', '제목 추론'}
SCORE = {'적합': 2, '조건부': 1, '부적합': 0}


def load_runs():
    runs = {}
    for run in 'ABC':
        rows = {}
        for f in glob.glob(os.path.join(RES, f'run{run}_*.jsonl')) + glob.glob(os.path.join(RES, f'sup{run}.jsonl')):
            for line in open(f, encoding='utf-8'):
                if line.strip():
                    r = json.loads(line)
                    rows[r['pid']] = r          # sup 파일이 뒤에 읽혀 덮어쓴다
        runs[run] = rows
    return runs


def lift_table():
    t = json.load(open(os.path.join(ROOT, '규격', '구성분석', '구성_유형_표.json'), encoding='utf-8'))
    out = {}
    for typ, rows in t['structure_main']['유형별 값(개수, 배율)'].items():
        for val, n, lift in rows:
            out[(val, typ)] = lift if n >= 3 else 1.0        # 지문 3개 미만 칸은 믿지 않는다
    return out


def verdicts(a, lift):
    """AI 판정 1건 → {유형: (판정, 근거)}"""
    v = {}
    rest = [x for x in a.get('restatements') or [] if len(x.get('sentence_nos') or []) >= 2]
    bc = a.get('blank_candidate')
    if bc and bc.get('inferable_from'):
        v['빈칸 추론'] = ('적합' if rest else '조건부', f"다시 말하기 {len(rest)}개")
    else:
        v['빈칸 추론'] = ('부적합', '추론 근거 있는 빈칸 후보 없음')
    os_ = a.get('order_split') or {}
    v['글의 순서 배열'] = (('적합' if os_.get('unique') else '조건부') if os_.get('possible') else '부적합', '단서: ' + ' / '.join(os_.get('cues') or []))
    ins = [x for x in a.get('insert_candidates') or [] if x.get('gap_without')]
    both = [x for x in ins if (x.get('back_cue') or '').strip() and (x.get('forward_cue') or '').strip()]
    v['주어진 문장 넣기'] = ('적합' if both else '조건부' if ins else '부적합', f"앞뒤로 묶인 문장 {len(both)}개")
    mi = (a.get('main_idea') or {}).get('exists')
    s = a.get('structure_main')
    for t in MAIN:
        good = lift.get((s, t), 1.0) >= 1.5 or (t == '제목 추론' and (a.get('myth') or {}).get('exists'))
        v[t] = (('적합' if good else '조건부') if mi and a.get('content') in ('논설', '설명', '연구·실험') else '부적합',
                f"구성 {s} 배율 {lift.get((s, t), 1.0)}")
    sp = a.get('summary_pair') or {}
    v['요약문 완성'] = (('적합' if len([w for w in sp.get('basic_words') or [] if w]) >= 2 else '조건부') if sp.get('possible') else '부적합',
                     f"{sp.get('A_concept', '')} / {sp.get('B_concept', '')}")
    ir = a.get('irrelevant_room') or {}
    v['무관한 문장 찾기'] = (('적합' if a.get('content') in ('논설', '설명') else '조건부') if ir.get('possible') else '부적합', ir.get('why', '')[:40])
    g = a.get('grammar_candidates') or {}
    kinds, total = sum(1 for x in g.values() if (x or 0) >= 1), sum(x or 0 for x in g.values())
    v['어법 판단'] = ('적합' if total >= 5 and kinds >= 3 else '조건부' if total >= 5 else '부적합', f"후보 {total}개 {kinds}종")
    pw = len(a.get('polar_words') or [])
    v['어휘의 적절성'] = ('적합' if pw >= 5 else '조건부' if pw >= 3 else '부적합', f"의미 방향 낱말 {pw}개")
    return v


def rank(v, a, lift):
    """추천 순서: 판정 점수, 같으면 구성 배율"""
    return sorted(TYPES, key=lambda t: (-SCORE[v[t][0]], -lift.get((a.get('structure_main'), t), 1.0)))


def main():
    runs, lift = load_runs(), lift_table()
    key = json.load(open(os.path.join(ROOT, '규격', '적합도', '비공개', '가명표.json'), encoding='utf-8'))
    pids = sorted(set.intersection(*[set(r) for r in runs.values()]))
    per_type = C.defaultdict(lambda: C.Counter())
    stable, n_fit, top3_hit, direct_hit = C.Counter(), [], C.Counter(), C.Counter()
    detail = {}
    for pid in pids:
        true = key[pid]['type']
        vs = {run: verdicts(runs[run][pid], lift) for run in runs}
        final = {}
        for t in TYPES:
            votes = C.Counter(vs[run][t][0] for run in vs)
            final[t] = votes.most_common(1)[0][0] if votes.most_common(1)[0][1] >= 2 else '조건부'
            stable['같음' if len(votes) == 1 else '다름'] += 1
        per_type[true][final[true]] += 1
        n_fit.append(sum(1 for t in TYPES if final[t] == '적합'))
        order = sorted(TYPES, key=lambda t: (-SCORE[final[t]], -lift.get((runs['A'][pid].get('structure_main'), t), 1.0)))
        top3_hit[true] += true in order[:3]
        direct_hit[true] += sum(true in [x.get('type') for x in runs[run][pid].get('direct_top3') or []] for run in runs) / len(runs)
        detail[pid] = {'정답 유형': true, '판정': final, '추천 3개': order[:3]}
    n = C.Counter(key[p]['type'] for p in pids)
    out = {'지문 수': len(pids),
           '유형별: 실제 유형 판정(적합/조건부/부적합)': {t: dict(per_type[t]) for t in TYPES},
           '실제 유형을 적합으로 본 비율 %': round(sum(per_type[t]['적합'] for t in TYPES) / len(pids) * 100, 1),
           '실제 유형을 적합 또는 조건부로 본 비율 %': round(sum(per_type[t]['적합'] + per_type[t]['조건부'] for t in TYPES) / len(pids) * 100, 1),
           '지문당 적합 유형 수 평균': round(sum(n_fit) / len(n_fit), 2),
           '추천 3개에 실제 유형이 든 비율 % (규칙)': {t: round(top3_hit[t] / n[t] * 100) for t in TYPES} | {'전체': round(sum(top3_hit.values()) / len(pids) * 100, 1)},
           '추천 3개에 실제 유형이 든 비율 % (AI가 바로 고름)': {t: round(direct_hit[t] / n[t] * 100) for t in TYPES} | {'전체': round(sum(direct_hit.values()) / len(pids) * 100, 1)},
           '3회 판정이 같은 비율 %': round(stable['같음'] / sum(stable.values()) * 100, 1)}
    json.dump({'요약': out, '지문별': detail}, open(os.path.join(ROOT, '규격', '적합도', '검증_v1.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
