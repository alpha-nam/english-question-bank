"""EBSi 기출 영어 자료(문제·정답·해설·듣기 mp3·대본)를 `기출/<시행연도.월>/` 에 받는다.
- 목록: ebsi_기출목록.json (EBSi 기출문제 화면 단추에서 읽은 파일 경로, 2026-10-28)
- 주소: https://wdown.ebsi.co.kr/W61001/01exam<경로> (공개 주소)
- 이미 있는 파일은 건너뛴다(덮어쓰지 않음). 결과는 다운로드결과.tsv 에 적는다.
사용: python -X utf8 -I ebsi_download.py [최소연도]   (기본 2017)
"""
import json, os, re, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '기출'))
BASE = 'https://wdown.ebsi.co.kr/W61001/01exam'
MIN_YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2017
KIND = {'P': '문제', 'J': '정답', 'H': '해설', 'R': '듣기', 'D': '듣기대본'}
MAGIC = {'.pdf': b'%PDF', '.png': b'\x89PNG'}

def folder_and_form(key):
    m = re.match(r'(\d{4})\.(\d+) (.*)', key)
    y, mo, title = m.group(1), int(m.group(2)), m.group(3)
    form = '홀수형' if '홀수형' in title else '짝수형' if '짝수형' in title else ''
    return f'{y}.{mo:02d}', form, title

def target_name(kind, form, ext):
    if kind == 'H':
        return f'영어_해설{ext}'
    if kind == 'D':
        return f'영어_듣기대본{ext}'
    mid = f'_{form}' if form else ''
    name = {'P': '문제', 'J': '정답', 'R': '듣기'}[kind]
    return f'영어{mid}_{name}{ext}'

def fetch(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    tmp = dest + '.part'
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, 'wb') as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    os.replace(tmp, dest)

def main():
    items = json.load(open(os.path.join(HERE, 'ebsi_기출목록.json'), encoding='utf-8'))
    rows = []
    for key, paths in items:
        folder, form, title = folder_and_form(key)
        if int(folder[:4]) < MIN_YEAR:
            continue
        d = os.path.join(ROOT, folder)
        os.makedirs(d, exist_ok=True)
        for kind, p in paths.items():
            url = p if p.startswith('http') else BASE + p
            ext = os.path.splitext(p)[1].lower()
            name = target_name(kind, form, ext)
            dest = os.path.join(d, name)
            if os.path.exists(dest):
                rows.append((folder, name, 'skip-있음', os.path.getsize(dest)))
                continue
            try:
                fetch(url, dest)
                size = os.path.getsize(dest)
                head = open(dest, 'rb').read(4)
                ok = head.startswith(MAGIC[ext]) if ext in MAGIC else (head[:3] == b'ID3' or head[0] == 0xFF)
                rows.append((folder, name, 'ok' if ok and size > 1000 else '이상', size))
            except Exception as e:
                rows.append((folder, name, f'실패:{e}', 0))
            time.sleep(0.3)
        print(folder, flush=True)
    with open(os.path.join(HERE, '다운로드결과.tsv'), 'w', encoding='utf-8') as f:
        f.write('폴더\t파일\t결과\t크기\n')
        for r in rows:
            f.write('\t'.join(map(str, r)) + '\n')
    bad = [r for r in rows if not r[2].startswith(('ok', 'skip'))]
    print('끝:', len(rows), '개, 문제', len(bad), '개')

main()
