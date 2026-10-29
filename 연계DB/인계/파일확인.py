#!/usr/bin/env python3
"""연계DB 폴더가 저장했던 그대로인지 확인한다. 파일은 바꾸지 않는다.

    python3 인계/파일확인.py                      (연계DB 폴더 안에서)
    python3 인계/파일확인.py <연계DB 폴더> <목록 파일>

`파일목록.tsv`의 각 줄은 sha256, 바이트 수, 연계DB 폴더 기준 경로(탭으로 나눔)입니다.
목록의 파일이 없거나, 크기나 내용이 다르면 알려 줍니다. 목록에 없는 파일은 보지 않습니다
(교재·기출 PDF, 문항 이미지처럼 PC에만 있는 큰 자료와 저장한 뒤에 새로 만든 파일).
저장한 뒤에 일부러 고친 파일은 "다름"으로 나오는 것이 정상입니다.
"""
import hashlib
import os
import sys


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_list(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip('\r\n')
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) != 3 or not parts[1].isdigit():
                raise SystemExit('목록 %d째 줄 모양이 이상합니다: %r' % (n, line[:80]))
            rows.append((parts[0], int(parts[1]), parts[2]))
    return rows


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.dirname(here)
    listing = argv[2] if len(argv) > 2 else os.path.join(here, '파일목록.tsv')
    rows = read_list(listing)
    missing, size_diff, hash_diff = [], [], []
    for digest, size, rel in rows:
        path = os.path.join(root, *rel.split('/'))
        if not os.path.isfile(path):
            missing.append(rel)
        elif os.path.getsize(path) != size:
            size_diff.append((rel, size, os.path.getsize(path)))
        elif sha256(path) != digest:
            hash_diff.append(rel)
    for rel in missing:
        print('없음  %s' % rel)
    for rel, want, got in size_diff:
        print('크기가 다름  %s (저장할 때 %d바이트, 지금 %d바이트)' % (rel, want, got))
    for rel in hash_diff:
        print('내용이 다름  %s (크기는 같음)' % rel)
    bad = len(missing) + len(size_diff) + len(hash_diff)
    print('확인한 파일 %d개 중 이상 없음 %d개, 이상 %d개 (없음 %d, 크기 다름 %d, 내용 다름 %d)'
          % (len(rows), len(rows) - bad, bad, len(missing), len(size_diff), len(hash_diff)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
