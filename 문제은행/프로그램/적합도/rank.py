"""추천 순서(v2): '적합' 유형 가운데 재료가 풍부한 순.
재료 점수는 유형마다 다르게 재고, 평가원 200지문에서의 백분위로 바꿔 유형끼리 견줄 수 있게 한다."""
import bisect, collections as C, json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge as J


def richness(a, lift):
    rest = [x for x in a.get('restatements') or [] if len(x.get('sentence_nos') or []) >= 2]
    bc = a.get('blank_candidate') or {}
    os_ = a.get('order_split') or {}
    ins = [x for x in a.get('insert_candidates') or [] if x.get('gap_without') and (x.get('back_cue') or '').strip() and (x.get('forward_cue') or '').strip()]
    s, myth = a.get('structure_main'), 1 if (a.get('myth') or {}).get('exists') else 0
    sp = a.get('summary_pair') or {}
    g = a.get('grammar_candidates') or {}
    return {'빈칸 추론': len(rest) + len(bc.get('inferable_from') or []) / 2,
            '글의 순서 배열': 2 * bool(os_.get('unique')) + sum(1 for c in os_.get('cues') or [] if c.strip()),
            '주어진 문장 넣기': len(ins),
            '요지 파악': lift.get((s, '요지 파악'), 1.0),
            '주제 추론': lift.get((s, '주제 추론'), 1.0) + 0.5 * myth,
            '제목 추론': lift.get((s, '제목 추론'), 1.0) + myth,
            '요약문 완성': (sp.get('relation') in ('대조', '인과')) + len([w for w in sp.get('basic_words') or [] if w]) / 2,
            '무관한 문장 찾기': 1.0 * bool((a.get('irrelevant_room') or {}).get('possible')) + lift.get((s, '무관한 문장 찾기'), 1.0) / 4,
            '어법 판단': sum(1 for x in g.values() if (x or 0) >= 1),
            '어휘의 적절성': len(a.get('polar_words') or []) / 2}


def mean_richness(runs, pid, lift):
    rs = [richness(runs[r][pid], lift) for r in runs if pid in runs[r]]
    return {t: st.mean(x[t] for x in rs) for t in J.TYPES}


def reference(lift):
    """평가원 200지문의 유형별 재료 점수 분포(백분위 기준)"""
    runs = J.load_runs()
    pids = sorted(set.intersection(*[set(r) for r in runs.values()]))
    ref = C.defaultdict(list)
    for pid in pids:
        for t, v in mean_richness(runs, pid, lift).items():
            ref[t].append(v)
    return {t: sorted(v) for t, v in ref.items()}


def percentile(ref, t, v):
    # 같은 값이 많은 유형(대부분 최고점)이 늘 앞서지 않도록 동점은 가운데 순위로 친다
    return (bisect.bisect_left(ref[t], v) + bisect.bisect_right(ref[t], v)) / 2 / len(ref[t])


def recommend(final, rich, ref, k=3):
    fit = [t for t in J.TYPES if final[t][0] == '적합'] or [t for t in J.TYPES if final[t][0] == '조건부']
    return sorted(fit, key=lambda t: -percentile(ref, t, rich[t]))[:k]
