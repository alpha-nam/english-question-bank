#!/usr/bin/env python3
"""문항이 많은 가짜 회차로 연계 지도와 '이전 문항·다음 문항' 목차 줄을 만든다(화면 시험 tests/nav_click.js 용).
시안 3문항을 번호만 바꿔 되풀이하고 DB 대조는 끈다. 진짜 회차 파일이 아니므로 완성본에 두지 않는다.
  python3 -I tests/make_many.py 출력.html [문항 수(기본 9)] [--nomap]     (--nomap: 연계 지도 없이 만든다)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import build  # noqa: E402
from test_build import fake_questions  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith('--')]
if not args:
    print(__doc__)
    sys.exit(2)
map_on = '--nomap' not in sys.argv[1:]
rnd, qs = build.load_round('2026.09')
count = int(args[1]) if len(args) > 1 else build.COMPACT_NAV_OVER + 1
html = build.build_html(rnd, fake_questions(rnd, qs, count), map_on=map_on, db_check=False)
with open(args[0], 'w', encoding='utf-8', newline='\n') as f:
    f.write(html)
print('만듦:', args[0], '문항', count, '개', '(지도 있음)' if map_on else '(지도 없음)')
