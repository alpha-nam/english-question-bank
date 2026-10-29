"""여러 지문 묶음(본 표본, 음성 대조군, 교재 20)에 같은 판정 규칙을 적용해 결과를 모은다.
사용: python -X utf8 -I judge_sets.py [v1|v2]"""
import collections as C, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge as J

SETS = {'대조군': ('ctrl', 'supctrl', '대조군_가명표.json'), '교재20': ('book', None, '교재20_가명표.json')}


def load(prefix, sup):
    runs = {}
    for run in 'ABC':
        rows = {}
        files = glob.glob(os.path.join(J.RES, f'{prefix}{run}.jsonl')) + (glob.glob(os.path.join(J.RES, f'{sup}{run}.jsonl')) if sup else [])
        for f in files:
            for line in open(f, encoding='utf-8'):
                if line.strip():
                    r = json.loads(line)
                    rows[r['pid']] = r
        runs[run] = rows
    return runs


def finalize(runs, pid, lift, verdict_fn):
    vs = [verdict_fn(runs[r][pid], lift) for r in runs if pid in runs[r]]
    out = {}
    for t in J.TYPES:
        votes = C.Counter(v[t][0] for v in vs)
        top, n = votes.most_common(1)[0]
        out[t] = (top if n * 2 > len(vs) else '조건부', vs[0][t][1])
    return out


def controls(verdict_fn=J.verdicts):
    lift = J.lift_table()
    runs = load('ctrl', 'supctrl')
    key = json.load(open(os.path.join(J.ROOT, '규격', '적합도', '비공개', '대조군_가명표.json'), encoding='utf-8'))
    pids = sorted(set.intersection(*[set(r) for r in runs.values()]))
    per_cat, per_type = C.defaultdict(list), C.Counter()
    for pid in pids:
        f = finalize(runs, pid, lift, verdict_fn)
        fit = [t for t in J.TYPES if f[t][0] == '적합']
        per_cat[key[pid]['type']].append(len(fit))
        per_type.update(fit)
    return {'지문 수': len(pids), '지문당 적합 유형 수(대조군 종류별 평균)': {k: round(sum(v) / len(v), 1) for k, v in per_cat.items()},
            '전체 평균': round(sum(sum(v) for v in per_cat.values()) / len(pids), 2),
            '대조군에서 적합이 나온 유형(지문 수)': dict(per_type.most_common())}


if __name__ == '__main__':
    print(json.dumps(controls(), ensure_ascii=False, indent=1))
