"""평가원 6·9·11월(수능) 시험 전부를 변환하고 검증한다. 사용: python -X utf8 -I run_all.py [시작연도]
결과: 검증보고.txt (시험마다 OK/FAIL 한 줄과 실패 내용)"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
start = int(sys.argv[1]) if len(sys.argv) > 1 else 2017
exams = []
for y in range(start, 2027):
    for m in ('06', '09', '11'):
        e = f'{y}.{m}'
        if y == 2022 and m == '09':
            e = '2022.08'          # 2022학년도 9월 모평은 8월 31일 시행
        if y == 2020 and m == '11':
            e = '2020.12'          # 2021학년도 수능은 12월 3일 시행
        if os.path.isdir(os.path.join(ROOT, '기출', e)):
            exams.append(e)
if len(sys.argv) > 2 and sys.argv[2] == '교육청':
    exams = [e for e in sorted(os.listdir(os.path.join(ROOT, '기출'))) if int(e[:4]) >= start and e[5:] in ('03', '04', '05', '07', '10')]
lines = []
for e in exams:
    def run(script):
        r = subprocess.run([sys.executable, '-X', 'utf8', '-I', script, e], cwd=HERE, capture_output=True, text=True, encoding='utf-8', errors='replace')
        return [l for l in (r.stdout + r.stderr).splitlines() if l.strip() and 'Advanced encoding' not in l and 'Warning' not in l and 't = re' not in l]
    b = run('build_exam.py')
    v = run('verify_exam.py')
    fails = [l for l in v if l.startswith('FAIL')]
    lines.append(('OK   ' if not fails else 'FAIL ') + e + (' | 변환 문제: ' + b[-1][:160] if 'problems": [[' in (b[-1] if b else '') else ''))
    lines += ['     ' + f[:230] for f in fails]
    print(lines[-1] if not fails else '\n'.join(lines[-1 - len(fails):]), flush=True)
open(os.path.join(HERE, ('검증보고_교육청.txt' if len(sys.argv) > 2 else '검증보고.txt')), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('끝:', sum(1 for l in lines if l.startswith('OK')), '/', len(exams))
