#!/usr/bin/env python3
"""생성기 검사. 실행: python3 -I tests/test_build.py   (생성기 폴더에서)

1. 시안 3문항(2026.09)을 만들어 마지막으로 받아들인 결과(golden/2026.09_pilot_v19_A.html)와 글자 하나까지 비교한다.
   일부러 바꾼 뒤에는 python3 -I tests/test_build.py --update-golden 으로 기준을 새로 쓴다(바뀐 곳을 눈으로 확인한 뒤에만).
2. 18판 시안(golden/2026.09_pilot_v18.html)과 비교해, 달라진 곳이 머리글 15줄과 CSS뿐인지 본다(헤더 A안 적용 때의 약속).
   도표 그림의 데이터는 18판이 EXAM/BOOK 변수, 생성기가 FIGS 목록이라 값으로 따로 비교한다. 도표 id 의 문항 번호(c-exam / c25-exam)만 같게 본다.
3) 글 표기(mk)와 데이터 검사(validate)가 잘못된 입력을 알려 주는지 본다.
4) 연계 지도 장(golden/2026.09_pilot_map.html 과 글자 하나까지 비교), 문항이 많을 때의 목차 줄, 문항 데이터와 DB(연계DB_통합_전체문항.csv)의 대조.
5) 독립 파일 틀(문서 형식 선언 등. 파일로 바로 열 때 크롬이 괴상 모드로 읽지 않게)과 Artifact 에 올리는 조각.
6) 전체 첫 화면(build.py index): 탭은 최근 회차가 왼쪽, 탭마다 지도 한 장, 수업 자료가 있는 회차만 눌리는 칸과 단추(golden/index_pilot.html 과 비교).
   문항은 번호순(round.json 의 order 가 번호순이 아니면 오류).
화면까지 똑같은지는 tests/dom_identity.js, 자동 맞춤 배율은 tests/fit_report.js 로 본다.
"""
import contextlib
import copy
import difflib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import build  # noqa: E402

GOLDEN18 = os.path.join(HERE, 'golden', '2026.09_pilot_v18.html')
GOLDEN = os.path.join(HERE, 'golden', '2026.09_pilot_v19_A.html')
GOLDEN_MAP = os.path.join(HERE, 'golden', '2026.09_pilot_map.html')   # 같은 문항에 연계 지도 장을 넣은 결과
GOLDEN_INDEX = os.path.join(HERE, 'golden', 'index_pilot.html')       # 전체 첫 화면(수업 자료는 2026.09 만 있는 것으로 고정해서 만든 결과)
V18_ORDER = [31, 3, 25]                                               # 18판은 이 순서였다. 지금은 문항을 번호순으로 둔다(제이님 요청 2026-10-23)
FIXED_DECKS = {'2026.09': {'html': '2026.09_파일럿.html', 'pdf': '2026.09_파일럿.pdf', 'ready': {3, 25, 31}}}

# 시험은 늘 시안 3문항(3·25·31번)으로 고정한 사본(tests/fixture/문항데이터)을 쓴다. 정식 문항데이터에 문항이 늘어도 기준 결과물과 어긋나지 않게 하려는 것(2026-10-24)
FIXTURE_DATA = os.path.join(HERE, 'fixture', '문항데이터')
_data_patch = mock.patch.object(build, 'DATA', FIXTURE_DATA)


def setUpModule():
    _data_patch.start()


def tearDownModule():
    _data_patch.stop()


def question(qs, no):
    """번호로 문항을 고른다(문항은 번호순이라 자리 번호로 고르면 문항이 늘 때 달라진다)"""
    return next(q for q in qs if q['no'] == no)


def cut_chart_data(s, start_marker):
    i = s.index(start_marker)
    j = s.index('/* 줄바꿈 규칙', i)
    return s[:i] + '<<도표 데이터>>\n' + s[j:], s[i:j]


class GoldenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rnd, cls.qs = build.load_round('2026.09')
        cls.out = build.build_html(cls.rnd, cls.qs, map_on=False)     # 지도 없는 결과. round.json 의 "map" 설정과 무관하게 본다
        old_order = sorted(cls.qs, key=lambda q: V18_ORDER.index(q['no']))
        cls.out18 = build.build_html(cls.rnd, old_order, map_on=False)    # 18판과 줄 단위로 비교하려고 18판의 문항 순서로 만든 것
        with open(GOLDEN, encoding='utf-8') as f:
            cls.gold = f.read()
        with open(GOLDEN18, encoding='utf-8') as f:
            cls.gold18 = f.read()

    def test_matches_accepted_snapshot(self):
        self.assertEqual(len(self.gold), len(self.out))
        self.assertTrue(self.gold == self.out, '마지막으로 받아들인 결과와 다름. 일부러 바꾼 것이면 --update-golden')

    def test_only_header_and_css_changed_since_v18(self):
        g, _ = cut_chart_data(self.gold18, 'var EXAM=')
        o, _ = cut_chart_data(self.out18, 'var FIGS=')
        o = re.sub(r'c\d+-(exam|book)', r'c-\1', o)
        # 글자 시안 C(2026-10-24): fit() 눈금을 0.03/0.02에서 0.01로 촘촘히 한 것은 일부러 바꾼 곳이라, 되돌려서 18판과 견준다
        o = o.replace('d-=.01', 'd-=.03').replace('z+=.01', 'z+=.02')
        # 쉽게 보기 장 카드 줄이기(2026-10-26)도 일부러 더한 곳이라 18판과 견줄 때는 빼고 본다
        o = re.sub(r'  /\* 쉽게 보기 장:.*?\n(?=  /\* 교사 분석 장)', '', o, flags=re.S)
        gl, ol = g.split('\n'), o.split('\n')
        style_end = gl.index('</style>')
        hd_changes, other = 0, []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, gl, ol, autojunk=False).get_opcodes():
            if tag == 'equal':
                continue
            lines = gl[i1:i2] + ol[j1:j2]
            if i1 < style_end:
                continue                                    # CSS 구간(머리글 규칙, 도표 장 보정)은 일부러 바꾼 곳
            if all('class="hd"' in l for l in lines):
                hd_changes += 1
            else:
                other.append(lines[:2])
        self.assertEqual(other, [], '머리글 밖의 본문이 18판과 다름')
        self.assertEqual(hd_changes, 15)

    def test_chart_data_same_values(self):
        _, gseg = cut_chart_data(self.gold18, 'var EXAM=')
        js = ('var calls=[];function chart(id,cfg,H,compact){calls.push({id:id,H:H,compact:!!compact,cfg:JSON.parse(JSON.stringify(cfg))})}\n'
              + gseg + '\nconsole.log(JSON.stringify(calls));')
        gold_calls = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)
        _, oseg = cut_chart_data(self.out18, 'var FIGS=')
        out_calls = json.loads(re.search(r'var FIGS=(.*?);\nFIGS\.forEach', oseg, re.S).group(1))
        norm = lambda lst: sorted(({'id': re.sub(r'c\d+-', 'c-', c['id']), 'H': c['H'], 'compact': c['compact'], 'cfg': c['cfg']} for c in lst),
                                  key=lambda c: c['id'])
        self.assertEqual(norm(gold_calls), norm(out_calls))

    def test_size_and_order(self):
        self.assertEqual([q['no'] for q in self.qs], [3, 25, 31])         # 문항은 번호순
        self.assertEqual(self.out.count('<section '), 15)
        self.assertEqual(self.out.count('<!-- ============'), 3)
        self.assertEqual(re.findall(r'<section class="slide" id="(q\d+)"', self.out), ['q3', 'q25', 'q31'])


class MarkupTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(build.mk('a <mark>b</mark> c'), 'a <mark>b</mark> c')
        self.assertEqual(build.mk('<ev>x <mark>y</mark></ev>'), '<span class="a">x <mark>y</mark></span>')
        self.assertEqual(build.mk('앞 <blank/> 뒤'), '앞 <span class="blk"></span> 뒤')
        self.assertEqual(build.mk('줄<br>바꿈'), '줄<br>바꿈')

    def test_escape(self):
        self.assertEqual(build.mk('a < b & c > d'), 'a &lt; b &amp; c &gt; d')

    def test_unbalanced(self):
        for bad in ('<mark>열고 안 닫음', '닫기만 </b>', '<b><mark>엇갈림</b></mark>'):
            with self.assertRaises(build.BuildError):
                build.mk(bad)

    def test_not_text(self):
        with self.assertRaises(build.BuildError):
            build.mk(['글이 아님'])


class ValidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rnd, cls.qs = build.load_round('2026.09')
        cls.icons = build.icon_names()

    def check(self, mutate, expect):
        q = copy.deepcopy(self.qs[0])
        mutate(q)
        with self.assertRaises(build.BuildError) as cm:
            build.validate(q, self.rnd, self.icons)
        self.assertIn(expect, str(cm.exception))

    def test_ok(self):
        for q in self.qs:
            build.validate(q, self.rnd, self.icons)

    def test_missing_stem(self):
        self.check(lambda q: q['text']['exam'].pop('stem'), 'text.exam.stem')

    def test_felt_range(self):
        self.check(lambda q: q['meta']['link'].update(felt=0), 'meta.link.felt')

    def test_choice_count(self):
        self.check(lambda q: q['text']['book']['choices']['items'].pop(), 'text.book.choices.items')

    def test_unknown_icon(self):
        self.check(lambda q: q['analysis']['easy']['book'].update(icon='nope'), 'nope')

    def test_empty_teacher_list(self):
        self.check(lambda q: q['analysis']['teacher'].update(view=[]), 'analysis.teacher.view')

    def test_answer_out_of_range(self):
        q = copy.deepcopy(self.qs[0])
        q['meta']['exam']['answer'] = 7
        with self.assertRaises(build.BuildError) as cm:
            build.build_html(self.rnd, [q] + self.qs[1:])
        self.assertIn('정답 번호', str(cm.exception))

    def test_figure_needs_labels(self):
        q = copy.deepcopy(question(self.qs, 25))                       # 도표 문항
        q['analysis']['compare'].pop('fig_labels')
        with self.assertRaises(build.BuildError) as cm:
            build.validate(q, self.rnd, self.icons)
        self.assertIn('fig_labels', str(cm.exception))


def fake_questions(rnd, qs, count):
    """문항이 많은 회차(목차 줄 줄이기)를 시험하려고, 시안 문항의 번호만 바꿔 count 개로 늘린 가짜 문항. DB 대조는 끄고 쓴다"""
    out = []
    for k in range(count):
        q = copy.deepcopy(qs[k % len(qs)])
        q['no'] = k + 1
        q['id'] = '%s-%02d' % (rnd['id'], k + 1)
        out.append(q)
    return out


def nav_of(html):
    """위 목차 줄(<nav>…</nav>)만 떼어 낸다. 앞쪽 <style>, <script> 안의 글자와 섞이지 않게"""
    return re.search(r'<nav(?: class="cn")?>.*?</nav>', html, re.S).group(0)


class MapTest(unittest.TestCase):
    """연계 지도 장(round.json 의 "map": true 또는 --map)과 목차 줄"""

    @classmethod
    def setUpClass(cls):
        cls.rnd, cls.qs = build.load_round('2026.09')
        cls.default = build.build_html(cls.rnd, cls.qs, map_on=False)
        cls.out = build.build_html(cls.rnd, cls.qs, map_on=True)

    def test_off_means_no_map(self):
        self.assertNotIn('mapslide', self.default)
        self.assertNotIn('href="#map"', self.default)
        self.assertEqual(self.default.count('<section '), 15)

    def test_on_adds_one_slide(self):
        self.assertEqual(self.out.count('<section '), 16)
        self.assertEqual(self.out.count('<section class="slide mapslide"'), 1)

    def test_cells(self):
        # 시험 문항 1~45번 칸 45개. 수업 자료가 있는 칸은 31·3·25번, 독립 출제 20칸(교재 연계 25문항)
        self.assertEqual(len(re.findall(r'class="mc ', self.out)), 45)
        self.assertEqual(sorted(re.findall(r'<a class="mc lk on" href="#(q\d+)"', self.out)), ['q25', 'q3', 'q31'])
        self.assertEqual(self.out.count('class="mc none"'), 20)
        self.assertIn('교재 연계 <b>25</b>문항', self.out)
        self.assertIn('독립 출제 <b>20</b>문항', self.out)
        self.assertIn('수업 자료 <b>3</b>문항', self.out)

    def test_felt_in_cells_matches_data(self):
        for q in self.qs:
            cell = re.search(r'<a class="mc lk on" href="#q%d".*?</a>' % q['no'], self.out, re.S).group(0)
            self.assertIn('5점 중 %d점' % q['meta']['link']['felt'], cell)

    def test_map_comes_first_and_nav_links_it(self):
        self.assertLess(self.out.index('id="map"'), self.out.index('id="q31"'))
        self.assertIn('<nav><b>2027학년도 9월 모의평가 연계 분석 시안</b><a href="#map">연계 지도</a><a href="#q3">', self.out)
        self.assertNotIn('data-go', nav_of(self.out))      # 문항이 적으면 이전·다음 단추 없이 번호 알약
        self.assertIn('--navh', self.out)                             # 폰에서 목차 줄이 장 위를 가리지 않게 하는 보정(nav.css 와 nav.js)은 지도와 함께 들어간다
        self.assertIn('scroll-margin-top:calc(var(--navh', self.out)
        self.assertNotIn('--navh', self.default)

    def test_few_questions_keep_pills(self):
        qs = fake_questions(self.rnd, self.qs, build.COMPACT_NAV_OVER)
        html = build.build_html(self.rnd, qs, map_on=True, db_check=False)
        nav = nav_of(html)
        self.assertEqual(len(re.findall(r'<a href="#q\d+">\d+번', nav)), build.COMPACT_NAV_OVER)
        self.assertNotIn('data-go', nav)

    def test_many_questions_get_prev_next(self):
        qs = fake_questions(self.rnd, self.qs, build.COMPACT_NAV_OVER + 1)
        html = build.build_html(self.rnd, qs, map_on=True, db_check=False)
        nav = nav_of(html)
        self.assertIn('<nav class="cn">', nav)
        self.assertIn('<a href="#map">연계 지도</a><a href="#map" data-go="prev">‹ 이전 문항</a><a href="#q1" data-go="next">다음 문항 ›</a>', nav)
        self.assertEqual(len(re.findall(r'<a href="#q\d+">\d+번', nav)), 0)
        self.assertIn('nav [data-go]', html)           # 이전·다음 문항을 옮기는 스크립트(template/nav.js)

    def test_many_questions_without_map(self):
        qs = fake_questions(self.rnd, self.qs, build.COMPACT_NAV_OVER + 1)
        html = build.build_html(self.rnd, qs, map_on=False, db_check=False)
        nav = nav_of(html)
        self.assertNotIn('연계 지도', nav)
        self.assertIn('<a href="#q1" data-go="prev">', nav)
        self.assertIn('nav [data-go]', html)                           # 지도가 없어도 단추를 옮기는 스크립트와 폰 목차 가림 보정은 함께 들어간다
        self.assertIn('scroll-margin-top:calc(var(--navh', html)
        self.assertNotIn('mapslide', html)

    def test_map_needs_round_in_csv(self):
        rnd = dict(self.rnd, id='1999.01')
        with self.assertRaises(build.BuildError) as cm:
            build.build_html(rnd, self.qs, map_on=True, db_check=False)
        self.assertIn('1999.01', str(cm.exception))

    def test_matches_accepted_map_snapshot(self):
        with open(GOLDEN_MAP, encoding='utf-8') as f:
            gold = f.read()
        self.assertTrue(gold == self.out, '연계 지도를 넣은 마지막 결과와 다름. 일부러 바꾼 것이면 --update-golden')


class DbCheckTest(unittest.TestCase):
    """문항 데이터가 DB(연계DB_통합_전체문항.csv)와 같은지 보는 검사"""

    @classmethod
    def setUpClass(cls):
        cls.rnd, cls.qs = build.load_round('2026.09')
        cls.rows = build.load_link_rows()

    def test_pilot_matches_db(self):
        build.check_db(self.rnd, self.qs, self.rows)

    def test_ranges_expand(self):
        cells = self.rows['2026.09']
        self.assertEqual(sorted(cells), list(range(1, 46)))
        self.assertIs(cells[16], cells[17])            # CSV 의 '16~17' 한 줄

    def differs(self, mutate, expect):
        qs = copy.deepcopy(self.qs)
        mutate(question(qs, 31))
        with self.assertRaises(build.BuildError) as cm:
            build.check_db(self.rnd, qs, self.rows)
        self.assertIn(expect, str(cm.exception))

    def test_felt_differs(self):                       # 파일럿 때 실제로 있었던 어긋남(31번 체감 1, DB 2)
        self.differs(lambda q: q['meta']['link'].update(felt=1), 'meta.link.felt')

    def test_page_differs(self):
        self.differs(lambda q: q['meta']['book'].update(page=179), 'meta.book.page')

    def test_book_differs(self):
        self.differs(lambda q: q['meta']['book'].update(name='수능완성 영어'), 'meta.book.name')

    def test_label_differs(self):
        self.differs(lambda q: q['meta']['link'].update(label='일부 변형 연계'), 'meta.link.label')

    def test_not_linked_in_db(self):
        self.differs(lambda q: q.update(no=16), '연계 문항이 아님')

    def test_build_stops_on_difference(self):
        qs = copy.deepcopy(self.qs)
        question(qs, 31)['meta']['link']['felt'] = 1
        with self.assertRaises(build.BuildError):
            build.build_html(self.rnd, qs)


class StandaloneTest(unittest.TestCase):
    """파일로 바로 여는 독립 파일(문서 형식 선언 포함)과 Artifact 에 올리는 조각"""

    @classmethod
    def setUpClass(cls):
        cls.rnd, cls.qs = build.load_round('2026.09')
        cls.fragment = build.build_html(cls.rnd, cls.qs)

    def test_fragment_has_no_document_frame(self):             # Artifact 가 틀을 따로 씌우므로 조각에는 없어야 한다
        low = self.fragment.lstrip().lower()
        self.assertTrue(low.startswith('<title>'))
        for tag in ('<!doctype', '<html', '<head>', '<body'):
            self.assertNotIn(tag, low)

    def test_standalone_wraps_fragment(self):
        page = build.standalone(self.fragment)
        self.assertTrue(page.startswith('<!doctype html>\n<html lang="ko">'))
        self.assertIn('<meta charset="utf-8">', page.split('<body>')[0])
        self.assertIn('viewport-fit=cover', page.split('<body>')[0])
        self.assertIn(self.fragment, page)
        self.assertTrue(page.endswith('</body>\n</html>\n'))
        self.assertEqual(page.lower().count('<!doctype'), 1)

    def test_cli_writes_standalone_or_fragment(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            a, b = os.path.join(d, 'a.html'), os.path.join(d, 'b.html')
            self.assertEqual(build.main(['2026.09', '--out', a]), 0)
            self.assertEqual(build.main(['2026.09', '--fragment', '--out', b]), 0)
            with open(a, encoding='utf-8') as f:
                pa = f.read()
            with open(b, encoding='utf-8') as f:
                pb = f.read()
        self.assertEqual(pa, build.standalone(pb))
        self.assertEqual(pb, self.fragment)

    def test_js_wrapper_matches(self):                          # 검사·PDF 도구(tools/skeleton.js)와 같은 틀을 쓰는지
        sample = '<title>t</title>\n<p>가나다</p>\n'
        try:
            out = subprocess.run(['node', '-e', "process.stdout.write(require('./tools/skeleton').wrap(process.argv[1]))", sample],
                                 cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30)
        except FileNotFoundError:
            self.skipTest('node 가 없음')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout, build.standalone(sample))


class TwoColumnOptionTest(unittest.TestCase):
    """body 에 "cols": 2 를 적으면 지문·대본을 2단으로 나눈다(안내문, 긴 대화용, 2026-10-24). 적지 않으면 지금까지와 같다"""

    def make(self, cols):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(FIXTURE_DATA, os.path.join(d, 'data'))
            for n, who in ((31, 'exam'), (3, 'exam')):
                pth = os.path.join(d, 'data', '2026.09', 'q%02d.json' % n)
                with open(pth, encoding='utf-8') as f:
                    q = json.load(f)
                if cols:
                    q['text'][who]['body']['cols'] = 2
                with open(pth, 'w', encoding='utf-8') as f:
                    json.dump(q, f, ensure_ascii=False)
            with mock.patch.object(build, 'DATA', os.path.join(d, 'data')), contextlib.redirect_stdout(io.StringIO()):
                out = os.path.join(d, 'o.html')
                self.assertEqual(build.main(['2026.09', '--out', out]), 0)
                with open(out, encoding='utf-8') as f:
                    return f.read()

    def test_two_columns_only_when_asked(self):
        plain = self.make(False)
        two = self.make(True)
        self.assertNotIn('class="passage cc2"', plain)
        self.assertNotIn('class="speaker cc2"', plain)
        self.assertIn('<div class="passage cc2">', two)
        self.assertIn('<div class="speaker cc2">', two)


class CoversTest(unittest.TestCase):
    """한 지문에 문항이 여럿인 장문: q43.json 하나가 44·45번까지 맡는다(covers, 2026-10-26, 제이님 요청)"""

    def test_ready_alias_and_label(self):
        qs = [{'no': 3}, {'no': 43, 'covers': [44, 45]}]
        ready, alias = build.ready_alias(qs)
        self.assertEqual(ready, {3, 43, 44, 45})
        self.assertEqual(alias, {44: 43, 45: 43})
        self.assertEqual(build.exam_label(qs[1]), '43~45')
        self.assertEqual(build.exam_label(qs[0]), '3')

    def test_map_cell_of_covered_number_points_to_the_deck_item(self):
        row = {'시험': '2026.09', '시험유형': '장문', '교재': '수능특강 영어듣기', '쪽': '135', '연계방식': '소재만', '학생체감': '1'}
        ready, alias = build.ready_alias([{'no': 43, 'covers': [44, 45]}])
        html = build.map_cell(44, row, ready, 'd.html', alias)
        self.assertIn('href="d.html#q43"', html)
        self.assertIn('href="d.html#q45"', build.map_cell(45, row, {45}, 'd.html'))     # 별칭이 없으면 자기 번호로 간다


class PictureTableTest(unittest.TestCase):
    """그림(picture)과 표(table) 본문: 옆 배치 장에 그림 이미지나 다시 그린 표가 들어간다(2026-10-26)"""
    PNG = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c63f8cfc0f01f0005000201a5f645400000000049454e44ae426082')

    def make(self, body, with_image=True):
        with tempfile.TemporaryDirectory() as d:
            shutil.copytree(FIXTURE_DATA, os.path.join(d, 'data'))
            if with_image:
                os.makedirs(os.path.join(d, 'data', '2026.09', '이미지'))
                with open(os.path.join(d, 'data', '2026.09', '이미지', 't.png'), 'wb') as f:
                    f.write(self.PNG)
            pth = os.path.join(d, 'data', '2026.09', 'q31.json')
            with open(pth, encoding='utf-8') as f:
                q = json.load(f)
            q['text']['exam']['body'] = body
            with open(pth, 'w', encoding='utf-8') as f:
                json.dump(q, f, ensure_ascii=False)
            with mock.patch.object(build, 'DATA', os.path.join(d, 'data')), contextlib.redirect_stdout(io.StringIO()):
                out = os.path.join(d, 'o.html')
                rc = build.main(['2026.09', '--out', out])
                if rc != 0:
                    return None                           # 만들기가 멈춤(오류는 화면에 안내하고 종료 코드만 돌려준다)
                with open(out, encoding='utf-8') as f:
                    return f.read()

    def test_table_is_redrawn_with_site_fonts(self):
        html = self.make({'kind': 'table', 'alt': '표', 'title': 'T', 'numbered': True, 'head': ['A', 'B'], 'rows': [['1', '2'], ['3', '4']],
                          'hl': [1], 'script': 'M: hi'})
        self.assertIn('<table class="tbl"', html)
        self.assertIn('<tr class="hl">', html)
        self.assertIn('class="n">①</td>', html)
        self.assertIn('<div class="speaker">M: hi</div>', html)

    def test_picture_is_stored_once_and_layout_is_marked(self):
        html = self.make({'kind': 'picture', 'alt': '그림', 'image': 't.png', 'script': 'M: hi'})
        self.assertIn('data-img="2026.09/t.png"', html)
        self.assertEqual(html.count('var IMGS='), 1)
        self.assertIn('class="q side s1 pic"', html)

    def test_missing_picture_file_stops_the_build(self):
        self.assertIsNone(self.make({'kind': 'picture', 'alt': '그림', 'image': 'none.png', 'script': 'M: hi'}, with_image=False))


class RoundOrderTest(unittest.TestCase):
    """문항은 번호순: order 를 적지 않으면 q*.json 을 번호순으로, 적으면 번호순이어야 한다(제이님 요청 2026-10-23)"""

    def load(self, order):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(build, 'DATA', d):
            os.makedirs(os.path.join(d, 'T.01'))
            rj = {'id': 'T.01', 'name': 'n', 'held': 'h'}
            if order is not None:
                rj['order'] = order
            with open(os.path.join(d, 'T.01', 'round.json'), 'w', encoding='utf-8') as f:
                json.dump(rj, f)
            for n in (31, 3, 25):
                with open(os.path.join(d, 'T.01', 'q%02d.json' % n), 'w', encoding='utf-8') as f:
                    json.dump({'no': n}, f)
            return [q['no'] for q in build.load_round('T.01')[1]]

    def test_default_is_ascending(self):
        self.assertEqual(self.load(None), [3, 25, 31])

    def test_ascending_subset_is_fine(self):
        self.assertEqual(self.load([3, 31]), [3, 31])

    def test_not_ascending_is_refused(self):
        for bad in ([31, 3, 25], [3, 3, 25]):
            with self.assertRaises(build.BuildError) as cm:
                self.load(bad)
            self.assertIn('번호가 작은 것부터', str(cm.exception))


def write_json(d, name, obj):
    path = os.path.join(d, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False)
    return path


class IndexTest(unittest.TestCase):
    """전체 첫 화면(build.py index): 회차 탭(최근 회차가 왼쪽), 탭마다 연계 지도 한 장과 수업 자료·PDF 단추"""

    @classmethod
    def setUpClass(cls):
        cls.rl = build.load_round_list()
        cls.rows = build.load_link_rows()
        cls.out = build.index_html(cls.rl, cls.rows, FIXED_DECKS)
        cls.panels = {m.group(1): m.group(0) for m in re.finditer(
            r'<div class="panel"[^>]*data-r="([^"]+)".*?(?=<div class="panel"|\n</div>\n\n<p class="credit">)', cls.out, re.S)}

    # ---- 탭과 칸
    def test_tabs_newest_first(self):
        ids = re.findall(r'<button type="button" role="tab" id="tab-([\d.]+)"', self.out)
        self.assertEqual(ids, ['2026.09', '2026.06', '2025.11', '2025.09', '2025.06', '2024.11', '2024.09', '2024.06'])
        labels = re.findall(r'role="tab"[^>]*>([^<]*)', self.out)
        self.assertEqual((labels[0], labels[-1]), ('2027학년도 9월', '2025학년도 6월'))
        self.assertEqual(list(self.panels), ids)                       # 패널도 같은 순서

    def test_first_tab_open_others_hidden(self):
        self.assertEqual(re.findall(r'role="tab"[^>]*aria-selected="(\w+)" tabindex="(-?\d)"', self.out),
                         [('true', '0')] + [('false', '-1')] * 7)
        self.assertEqual([rid for rid, p in self.panels.items() if ' hidden>' not in p.split('\n')[0]], ['2026.09'])

    def test_every_panel_has_a_full_map(self):
        self.assertEqual(len(self.panels), 8)
        for rid, p in self.panels.items():
            self.assertEqual(len(re.findall(r'class="mc ', p)), 45, rid)
            self.assertEqual(p.count('id="map-%s"' % rid), 1, rid)

    def test_ids_are_unique(self):
        ids = re.findall(r'\sid="([^"]+)"', self.out)
        self.assertEqual(len(ids), len(set(ids)))

    def test_only_pilot_round_links_to_deck(self):
        links = re.findall(r'<a class="mc lk on" href="([^"]+)"', self.out)
        self.assertEqual(sorted(links), ['2026.09_파일럿.html#q25', '2026.09_파일럿.html#q3', '2026.09_파일럿.html#q31'])
        self.assertEqual(len(re.findall(r'<a class="mc lk on"', self.panels['2026.09'])), 3)
        self.assertEqual(self.out.count('수업 자료 준비 중</span>'), 7)       # 자료가 없는 회차의 단추
        self.assertEqual(self.out.count('<span class="ok">자료 있음</span>'), 1)

    def test_buttons_of_pilot_round(self):
        acts = re.search(r'<div class="acts">(.*?)</div>', self.panels['2026.09'], re.S).group(1)
        self.assertEqual(acts, '<a class="btn" href="2026.09_파일럿.html">수업 자료 열기</a>'
                               '<a class="btn" href="2026.09_파일럿.pdf" download>PDF 받기</a>')

    def test_chips_match_db(self):
        self.assertIn('<span>교재 연계 <b>25</b>문항</span><span>체감 평균 <b>1.6</b></span>', self.panels['2026.09'])

    def test_no_document_frame_in_fragment(self):
        low = self.out.lstrip().lower()
        self.assertTrue(low.startswith('<title>연계 분석 수업 자료</title>'))
        for tag in ('<!doctype', '<html', '<head>', '<body'):
            self.assertNotIn(tag, low)
        self.assertIn('role=tab', self.out)                           # 탭을 바꾸는 스크립트(template/index.js)
        self.assertLess(len(self.out), 200000)                        # 아이콘은 하나만 넣는다(icons.css 전체는 88KB)

    def test_matches_accepted_index_snapshot(self):
        with open(GOLDEN_INDEX, encoding='utf-8') as f:
            gold = f.read()
        self.assertTrue(gold == self.out, '첫 화면의 마지막 결과와 다름. 일부러 바꾼 것이면 --update-golden')

    # ---- 자료 상태에 따른 모양
    def test_without_any_deck_nothing_links(self):
        out = build.index_html(self.rl, self.rows, {})
        self.assertNotIn('<a class="mc', out)
        self.assertNotIn('class="ok"', out)
        self.assertEqual(out.count('수업 자료 준비 중</span>'), 8)
        linked = sum(1 for r in self.rl['rounds'] for row in self.rows[r['id']].values() if row['연계방식'] != '비연계')
        self.assertEqual(out.count('<span class="mc lk"'), linked)                              # 연계 칸은 모두 점선(준비 중)

    def test_pdf_missing(self):
        decks = {'2026.09': dict(FIXED_DECKS['2026.09'], pdf=None)}
        out = build.index_html(self.rl, self.rows, decks)
        self.assertIn('<a class="btn" href="2026.09_파일럿.html">수업 자료 열기</a><span class="btn off">PDF 준비 중</span>', out)
        self.assertNotIn('.pdf', out)

    def test_unknown_round_in_db(self):
        rl = {'title': 't', 'sub': 's', 'rounds': [{'id': '1999.01', 'tab': 'x', 'name': 'n', 'held': 'h'}]}
        with self.assertRaises(build.BuildError) as cm:
            build.index_html(rl, self.rows, {})
        self.assertIn('1999.01', str(cm.exception))

    def test_needs_csv(self):
        with self.assertRaises(build.BuildError):
            build.index_html(self.rl, None, {})

    # ---- 회차목록.json
    def test_felt_mean(self):
        cells = {1: {'연계방식': '소재만', '학생체감': '2'}, 2: {'연계방식': '일부변형', '학생체감': '5'},
                 3: {'연계방식': '비연계', '학생체감': ''}}
        self.assertEqual(build.felt_mean(cells), 3.5)
        self.assertIsNone(build.felt_mean({3: cells[3]}))

    def test_list_is_sorted_newest_first_whatever_the_file_order(self):
        rounds = [{'id': i, 'tab': 't' + i, 'name': 'n', 'held': 'h'} for i in ('2024.11', '2026.09', '2025.06')]
        with tempfile.TemporaryDirectory() as d:
            rl = build.load_round_list(write_json(d, '목.json', {'title': 't', 'sub': 's', 'rounds': rounds}))
        self.assertEqual([r['id'] for r in rl['rounds']], ['2026.09', '2025.06', '2024.11'])

    def test_list_errors(self):
        one = {'id': '2026.09', 'tab': 'a', 'name': 'n', 'held': 'h'}
        cases = [({'sub': 's', 'rounds': [one]}, 'title'),
                 ({'title': 't', 'sub': 's', 'rounds': []}, 'rounds'),
                 ({'title': 't', 'sub': 's', 'rounds': [dict(one, tab='')]}, 'rounds[0].tab'),
                 ({'title': 't', 'sub': 's', 'rounds': [dict(one, id='2026.9')]}, '2026.09 같은 모양'),
                 ({'title': 't', 'sub': 's', 'rounds': [one, dict(one, tab='b')]}, 'id 겹침'),
                 ({'title': 't', 'sub': 's', 'rounds': [one, dict(one, id='2026.06')]}, 'tab 겹침')]
        with tempfile.TemporaryDirectory() as d:
            for obj, expect in cases:
                with self.assertRaises(build.BuildError, msg=expect) as cm:
                    build.load_round_list(write_json(d, '목.json', obj))
                self.assertIn(expect, str(cm.exception))

    # ---- 회차마다 수업 자료가 있는지
    def with_fake_data(self, name='N', held='H'):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        data, out = os.path.join(d.name, 'data'), os.path.join(d.name, 'out')
        os.makedirs(os.path.join(data, '2026.09'))
        write_json(os.path.join(data, '2026.09'), 'round.json', {'id': '2026.09', 'name': name, 'held': held, 'out': 'x.html'})
        for n in (25, 3):
            write_json(os.path.join(data, '2026.09'), 'q%02d.json' % n, {'no': n})
        return mock.patch.multiple(build, DATA=data, OUT=out), out

    def test_round_files(self):
        r = {'id': '2026.09', 'tab': 't', 'name': 'N', 'held': 'H'}
        patch, out = self.with_fake_data()
        with patch:
            self.assertIsNone(build.round_files(r, exists=lambda p: False))                  # 만든 HTML 이 아직 없음
            self.assertEqual(build.round_files(r, exists=lambda p: p == os.path.join(out, 'x.html')),
                             {'html': 'x.html', 'pdf': None, 'ready': {3, 25}, 'alias': {}})
            self.assertEqual(build.round_files(r, exists=lambda p: True), {'html': 'x.html', 'pdf': 'x.pdf', 'ready': {3, 25}, 'alias': {}})
            self.assertIsNone(build.round_files(dict(r, id='1999.01'), exists=lambda p: True))   # 문항 데이터 폴더가 없는 회차

    def test_round_files_name_must_match(self):
        r = {'id': '2026.09', 'tab': 't', 'name': 'N', 'held': 'H'}
        patch, _ = self.with_fake_data()
        with patch:
            for key in ('name', 'held'):
                with self.assertRaises(build.BuildError) as cm:
                    build.round_files(dict(r, **{key: '다른 글'}), exists=lambda p: True)
                self.assertIn(key, str(cm.exception))

    def test_icons_subset(self):
        css = build.icons_subset({'link'})
        self.assertEqual(css.count('.i-link{'), 1)
        self.assertNotIn('.i-memo{', css)
        with self.assertRaises(build.BuildError):
            build.icons_subset({'nope'})

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            a, b = os.path.join(d, 'a.html'), os.path.join(d, 'b.html')
            self.assertEqual(build.main(['index', '--check']), 0)
            self.assertEqual(build.main(['index', '--out', a]), 0)
            self.assertEqual(build.main(['index', '--fragment', '--out', b]), 0)
            with open(a, encoding='utf-8') as f:
                pa = f.read()
            with open(b, encoding='utf-8') as f:
                pb = f.read()
        self.assertEqual(pa, build.standalone(pb))
        self.assertTrue(pb.lstrip().startswith('<title>'))


if __name__ == '__main__':
    if '--update-golden' in sys.argv:
        _data_patch.start()                                  # 기준 결과물은 시안 3문항 고정 사본으로 쓴다
        rnd, qs = build.load_round('2026.09')
        for path, html in ((GOLDEN, build.build_html(rnd, qs, map_on=False)),
                           (GOLDEN_MAP, build.build_html(rnd, qs, map_on=True)),
                           (GOLDEN_INDEX, build.index_html(build.load_round_list(), build.load_link_rows(), FIXED_DECKS))):
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(html)
            print('기준을 새로 썼음:', path)
        sys.exit(0)
    unittest.main(verbosity=2)
