#!/usr/bin/env python3
"""인계/파일목록.tsv 를 새로 만든다 (2026-10-26 저장). 파일은 바꾸지 않고 목록만 쓴다.

    python3 인계/파일목록만들기.py                      (연계DB 폴더 안에서. 기본은 인계/파일목록.tsv 에 씀)
    python3 인계/파일목록만들기.py <쓸 파일>

목록에 넣는 것: 연계DB 안의 문서·코드·데이터·완성본·시안·스크립트·글자 파일 등(이름이 '백업'으로 시작하거나 '백업'이 들어간 폴더·파일,
node_modules, __pycache__ 는 뺀다). 문항DB(이미지 400MB)와 교재·기출 PDF(연계DB 밖)는 큰 자료라 뺀다.
`파일확인.py` 가 이 목록으로 폴더가 온전한지 sha256까지 견준다. 일을 마칠 때마다 다시 만들어 두면 다음 계정이 변경을 구분하기 쉽다.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKIP_DIR = ('문항DB', 'node_modules', '__pycache__', '.git')
SKIP_EXT = ('.pyc', '.tmp')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main(argv):
    out = argv[1] if len(argv) > 1 else os.path.join(HERE, '파일목록.tsv')
    rows = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIR and '백업' not in d)
        for fn in sorted(fns):
            if '백업' in fn or fn.endswith(SKIP_EXT):
                continue
            path = os.path.join(dp, fn)
            rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
            if os.path.abspath(path) == os.path.abspath(out):
                continue
            rows.append((sha256(path), os.path.getsize(path), rel))
    rows.sort(key=lambda r: r[2])
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        for digest, size, rel in rows:
            f.write('%s\t%d\t%s\n' % (digest, size, rel))
    print('목록에 %d개 파일을 적었습니다 -> %s' % (len(rows), out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
