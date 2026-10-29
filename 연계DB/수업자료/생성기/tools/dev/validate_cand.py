# 후보 문항 검사 도구 (2026-10-26 저장. 이 폴더 안의 도구라서 어느 계정에서나 쓴다)
#
# 문항 데이터를 처음 만들 때는 정식 폴더가 아니라 문항데이터/_시안후보/<회차>/ 에 qNN.json 으로 만든다.
# 이 도구는 정식 생성기·문항 데이터를 임시 폴더에 복사하고 후보를 얹어 `build.py <회차> --check` 를 돌린다.
# 정식 폴더는 건드리지 않는다. "검사 통과"가 나온 뒤에 후보를 문항데이터/<회차>/ 로 옮긴다.
#
# 사용 (연계DB 폴더 어디서든):
#   python -X utf8 -I 수업자료/생성기/tools/dev/validate_cand.py --round=2026.06            (후보 전부)
#   python -X utf8 -I 수업자료/생성기/tools/dev/validate_cand.py --round=2026.06 q01 q02    (골라서)
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))      # 연계DB 폴더

args = [a for a in sys.argv[1:] if not a.startswith('--round=')]
rnd = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--round=')), '2026.09')
tmp = tempfile.mkdtemp(prefix='cand_')
T = os.path.join(tmp, '연계DB')
os.makedirs(os.path.join(T, '수업자료'))
ign = shutil.ignore_patterns('백업*', '*백업*', 'fixture', 'node_modules')
shutil.copytree(os.path.join(ROOT, '수업자료', '생성기'), os.path.join(T, '수업자료', '생성기'), ignore=ign)
shutil.copytree(os.path.join(ROOT, '수업자료', '문항데이터'), os.path.join(T, '수업자료', '문항데이터'), ignore=ign)
shutil.copy(os.path.join(ROOT, '연계DB_통합_전체문항.csv'), T)
cand = os.path.join(ROOT, '수업자료', '문항데이터', '_시안후보', rnd)
names = args or [f[:-5] for f in os.listdir(cand) if f.startswith('q') and f.endswith('.json')]
dest = os.path.join(T, '수업자료', '문항데이터', rnd)
os.makedirs(dest, exist_ok=True)
for n in names:
    shutil.copy(os.path.join(cand, n + '.json'), dest)
if os.path.isdir(os.path.join(cand, '이미지')):                    # 후보 그림(2026-10-26 추가): 검사용 임시 폴더로도 옮긴다
    shutil.copytree(os.path.join(cand, '이미지'), os.path.join(dest, '이미지'), dirs_exist_ok=True)
r = subprocess.run([sys.executable, '-X', 'utf8', '-I', 'build.py', rnd, '--check'],
                   cwd=os.path.join(T, '수업자료', '생성기'), capture_output=True, text=True, encoding='utf-8')
print('검사 결과 코드', r.returncode)
print((r.stdout + r.stderr).strip()[-3000:])
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(r.returncode)
