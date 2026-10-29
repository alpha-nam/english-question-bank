"""시험 하나의 문제 PDF·해설 PDF에서 문항 DB(JSON)를 만든다 (시범판, 2026-10-28).
사용: python -X utf8 -I build_exam.py <시험폴더, 예 2026.09> [--out 폴더]
입력: 기출/<시험>/영어_문제.pdf, 영어_해설.pdf (수능은 영어_홀수형_문제.pdf)
출력: 문제은행/DB/기출/<시험>/<시험>-NN.json 과 _시험.json(검증 보고)
"""
import json, os, re, sys
import pdfplumber
import pypdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CIRC = '①②③④⑤'
DINGBAT = str.maketrans('➀➁➂➃➄', '①②③④⑤')      # 일부 시험은 ⑤ 를 ➄ 로 쓴다
NOISE = [re.compile(r'^\d{1,2} ?영어 ?영역$'), re.compile(r'^영어$'), re.compile(r'^(\d{1,2} )?(영어 )?영역( \d{1,2})?$'), re.compile(r'전국연합학력평가'), re.compile(r'^어 ?영역'), re.compile(r'^※ ?확인 ?사항'), re.compile(r'^답안지의 해당란'), re.compile(r'^기입 ?\(표기\)'), re.compile(r'^하시오\.?$'), re.compile(r'^\d{1,2} ?영어$'), re.compile(r'^고 ?3 ?영어'), re.compile(r'^고 ?3$'), re.compile(r'^\d{1,2}$'), re.compile(r'^\d{1,2} \d{1,2}$'), re.compile(r'^\s*$'),
         re.compile(r'이 문제지에 관한 저작권'), re.compile(r'^영어 영역$'), re.compile(r'^\* 확인 사항'),
         re.compile(r'^○ 답안지의'), re.compile(r'^홀수형$|^짝수형$'),
         re.compile(r'대학수학능력시험 (문제지|9월|6월)|모의평가 문제지'), re.compile(r'^제 ?\d 교시$'), re.compile(r'^\d{4}학년도 대학수학능력시'), re.compile(r'^\d{4}학년도 .*(문제지|평가)$')]
IN_TEXT_STEMS = ('밑줄 친 부분 중', '들어가기에 가장 적절한 곳', '관계 없는 문장')


def pdf_text(path):
    """해설 PDF 등 한 단 문서용 글자 추출"""
    r = pypdf.PdfReader(path)
    return [(p.extract_text() or '') for p in r.pages]


def _hsegments(col):
    """단 안의 가로 선분(밑줄·빈칸 줄): (x0, x1, y) 목록. 표 테두리처럼 긴 선은 뺀다."""
    segs = set()
    width = col.bbox[2] - col.bbox[0]
    for o in list(col.lines) + list(col.rects):
        y = (o['top'] + o['bottom']) / 2
        if y < 150 or y > col.bbox[3] - 100:      # 머리글 선, 쪽 번호 상자
            continue
        if abs(o['bottom'] - o['top']) <= 1.5 and 12 < (o['x1'] - o['x0']) < width * 0.8:
            segs.add((round(o['x0'], 1), round(o['x1'], 1), round((o['top'] + o['bottom']) / 2, 1)))
    return sorted(segs)


def _col_text(col):
    """한 단의 글자를 읽되, 밑줄 친 글자는 ⟨ ⟩ 로 감싸고 빈칸 줄은 ＿＿＿ 로 바꾼다"""
    chars = [dict(c) for c in col.chars]
    extra = []
    for t in col.find_tables():                 # 표는 따로 뽑으므로 본문 글자에서는 빼고 자리에 [표] 만 남긴다
        rows = t.extract()
        if len(rows) < 2 or len(rows[0]) < 2:
            continue
        bx0, btop, bx1, bbot = t.bbox
        inside = [c for c in chars if bx0 - 1 <= c['x0'] and c['x1'] <= bx1 + 1 and btop - 1 <= c['top'] and c['bottom'] <= bbot + 1]
        if inside:
            mk = dict(inside[0])
            mk.update(text='[표]', x0=bx0, x1=bx0 + 18, top=btop, bottom=btop + 10)
            chars = [c for c in chars if c not in inside]
            extra.append(mk)
    tboxes = [t.bbox for t in col.find_tables() if len(t.extract()) >= 2]
    for x0, x1, y in _hsegments(col):
        if any(tb[0] - 2 <= x0 and x1 <= tb[2] + 2 and tb[1] - 2 <= y <= tb[3] + 2 for tb in tboxes):
            continue
        under = [c for c in chars if abs(c['bottom'] - y) <= 4.5 and c['x0'] >= x0 - 1.5 and c['x1'] <= x1 + 1.5
                 and c['text'].strip()]
        row = [c for c in chars if abs(c['bottom'] - y) <= 4.5 and c['text'].strip()]
        if under and not any(c['text'].isalnum() for c in under):
            continue                          # 쉼표·마침표 밑의 짧은 선은 밑줄이 아니다
        if under:
            a, b = under[0], under[-1]
            for ch, xx in (('⟨', a['x0'] - 0.01), ('⟩', b['x1'] + 0.01)):
                t = dict(a)
                t.update(text=ch, x0=xx, x1=xx, width=0)
                extra.append(t)
        elif row:
            before = [c for c in row if c['x1'] <= x0 + 1.5]
            ref = max(before, key=lambda c: c['x1']) if before else min(row, key=lambda c: abs(c['x0'] - x0))
            t = dict(ref)
            t.update(text='＿＿＿', x0=x0, x1=x1, width=x1 - x0)
            extra.append(t)
    # 옛 시험은 빈칸이 선이 아니라 줄 안의 큰 빈자리로 그려져 있다: 80pt 이상 벌어진 곳을 빈칸으로 본다
    for ln in col.extract_text_lines(x_tolerance=1.5, return_chars=True):
        cs = [c for c in ln['chars'] if c['text'].strip()]
        if not cs or cs[0]['text'] in CIRC or ln['text'].lstrip().startswith(('(A)', '(B)', '(C)', '(D)')):
            continue
        for a, b in zip(cs, cs[1:]):
            if b['x0'] - a['x1'] >= 80 and not any(e['text'] == '｛G｝' and abs(e['x0'] - a['x1']) < 100 and abs(e['top'] - a['top']) < 4 for e in extra):
                t = dict(a)
                t.update(text='｛G｝', x0=a['x1'] + 3, x1=b['x0'] - 3, width=b['x0'] - a['x1'] - 6)
                extra.append(t)
    # 줄 끝에서 빈칸이 줄의 나머지를 차지한 경우: 줄이 짧게 끝나고(문장이 안 끝남) 다음 줄이 소문자로 이어진다
    tl = col.extract_text_lines(x_tolerance=1.5, return_chars=True)
    ends = sorted(max(c['x1'] for c in l['chars'] if c['text'].strip()) for l in tl if any(c['text'].strip() for c in l['chars']))
    if ends:
        right = ends[int(len(ends) * 0.9)]
        for i, ln in enumerate(tl[:-1]):
            cs = [c for c in ln['chars'] if c['text'].strip()]
            txt = ln['text'].strip()
            if not cs or re.search('[가-힣]', txt) or txt.startswith(('(', '[', '*')) or cs[0]['text'] in CIRC:
                continue
            nxt = tl[i + 1]['text'].strip()
            if right - cs[-1]['x1'] >= 55 and re.search(r'[A-Za-z,]$', txt) and re.match(r'[a-z]', nxt):
                t = dict(cs[-1])
                t.update(text='｛S｝', x0=cs[-1]['x1'] + 3, x1=right - 3, width=right - cs[-1]['x1'] - 6)
                extra.append(t)
    # 문단 끝: 줄이 짧게 끝나고 문장 부호로 끝나며 다음 줄이 대문자로 시작하면 다음 줄 앞에 문단 표시 ¶ 를 붙인다
    # (주어진 문장 넣기의 '주어진 문장'과 지문을 가르는 데 쓴다)
    if ends:
        gaps = [b['top'] - a['top'] for a, b in zip(tl, tl[1:]) if 0 < b['top'] - a['top'] < 40]
        gap_med = sorted(gaps)[len(gaps) // 2] if gaps else 17
        for i, ln in enumerate(tl[:-1]):
            cs = [c for c in ln['chars'] if c['text'].strip()]
            nx = [c for c in tl[i + 1]['chars'] if c['text'].strip()]
            txt = ln['text'].strip()
            short_end = (right - cs[-1]['x1'] >= 25) if cs else False
            big_gap = (tl[i + 1]['top'] - ln['top']) > 1.45 * gap_med      # 문단 사이는 줄 간격이 더 넓다
            if cs and nx and (short_end or big_gap) and re.search('[.?!]["”’]?$', txt) and re.match('[A-Z“"‘]', nx[0]['text']) \
                    and not re.search('[가-힣]', txt) and not txt.startswith(('(', '[', '*')):
                t = dict(nx[0])
                t.update(text='¶', x0=nx[0]['x0'] - 0.6, x1=nx[0]['x0'] - 0.1, width=0.5)
                extra.append(t)
    return pdfplumber.utils.extract_text(chars + extra, x_tolerance=1.5) or ''



def a3_copy(path, exam):
    """A4로 줄여 배포된 문제지(2018.10, 2021.04, 2025.05)를 A3 크기로 키운 사본 경로. 다른 시험은 원본 경로 그대로.
    본문 쪽 판정과 밑줄·빈칸 거리 기준이 A3(가로 842pt) 기준이라 크기를 맞춘다."""
    r = pypdf.PdfReader(path)
    w = float(r.pages[0].mediabox.width)
    if w >= 700:
        return path
    out = os.path.join(HERE, '캐시', f'{exam}_A3.pdf')
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        wr = pypdf.PdfWriter()
        for pg in r.pages:
            pg.scale_by(842 / w)
            wr.add_page(pg)
        with open(out, 'wb') as f:
            wr.write(f)
    return out


def pdf_text_2col(path):
    """문제 PDF(2단 배치): 쪽마다 왼쪽 단, 오른쪽 단 순서로 글자를 읽는다(pdfplumber가 낱말 간격이 정확하다)"""
    out = []
    with pdfplumber.open(path) as pdf:
        for pg in pdf.pages:
            if not layout.normal_page(pg):
                out.append('')
                continue
            half = pg.width / 2
            parts = [_col_text(pg.crop((0, 0, half, pg.height))), _col_text(pg.crop((half, 0, pg.width, pg.height)))]
            out.append(chr(10).join(parts))
    return out


def clean_lines(pages):
    out = []
    for pi, t in enumerate(pages, 1):
        for ln in t.split('\n'):
            s = ln.rstrip().translate(DINGBAT)
            s = re.sub(r'^(\d) (\d)\. ', lambda m: m.group(1) + m.group(2) + '. ', s)          # '1 9.' 처럼 벌어진 번호
            if any(p.search(re.sub(r'\s+', ' ', re.sub('｛[GS]｝|¶|⟨|⟩', '', s)).strip()) for p in NOISE):
                continue
            out.append((pi, s))
    return out


def split_items(lines, n_items=45):
    starts = []
    exp = 1
    for i, (pi, s) in enumerate(lines):
        m = re.match(r'^(\d{1,2})\.(?!\d{1,2}(?!\d))', s)
        if m and int(m.group(1)) == exp:
            starts.append((exp, i))
            exp += 1
            if exp > n_items:
                break
    items = {}
    headers = []
    for k, (no, i) in enumerate(starts):
        j = starts[k + 1][1] if k + 1 < len(starts) else len(lines)
        blk = lines[i:j]
        for h, (_, s) in enumerate(blk):
            m = re.match(r'^\[\s*(\d+)\s*[～~]\s*(\d+)\s*\]', s)
            if m and h > 0:
                txt = ' '.join(x for _, x in blk[h:]).strip()
                headers.append((int(m.group(1)), int(m.group(2)), re.sub(r'^\[[^\]]*\]\s*', '', txt), blk[h:]))
                blk = blk[:h]
                break
        items[no] = blk
    return items, headers


def marks(text, typ):
    """밑줄 표시 ⟨ ⟩ 를 <u> </u> 로 바꾼다. 표·안내문·요약문의 칸 선은 밑줄이 아니므로 지운다."""
    t = re.sub('⟩[ \t]*' + chr(10) + '?[ \t]*⟨(?=[a-z])', '', text)   # 줄바꿈으로 끊긴 밑줄 구절(mir/ror)을 잇는다
    if any(k in (typ or '') for k in ('표', '안내문', '요약')):
        return t.replace('⟨', '').replace('⟩', '')
    t = re.sub('⟨\s*([^⟩]*?)\s*⟩', lambda m: '<u>' + m.group(1) + '</u>', t)
    return t


def resolve_blanks(text, is_blank_item):
    """선으로 그린 빈칸(＿＿＿)은 그대로 두고, 간격·줄끝으로 추정한 빈칸(｛G｝｛S｝)은 빈칸 추론 문항에서만 쓴다.
    돌려주는 값: (글, 상태) 상태는 '선' / '추정' / '불확실' / '' (빈칸 없음)"""
    g, sh = text.count('｛G｝'), text.count('｛S｝')
    line = text.count('＿＿＿')
    text = text.replace('｛G｝', chr(1)).replace('｛S｝', chr(2))
    if not is_blank_item:
        return re.sub('[]', '', text), ('선' if line else '')
    if line:
        return re.sub('[]', '', text), '선'
    if g == 1:
        return text.replace(chr(1), '＿＿＿').replace(chr(2), ''), '추정'
    if g == 0 and sh == 1:
        return text.replace(chr(2), '＿＿＿').replace(chr(1), ''), '추정'
    if g + sh == 0:
        return text, '불확실'
    return text.replace(chr(1), '＿＿＿').replace(chr(2), ''), '불확실'


def reflow(text, first_break=False):
    """줄 끝에서 끊긴 문장을 이어 붙인다. (A)(B)(C)(D) 문단, 각주(*), 번호 표시로 시작하는 줄은 새 줄로 둔다."""
    out = []
    lines = [x.strip() for x in text.split(chr(10)) if x.strip()]
    lens = sorted(len(x) for x in lines)
    median = lens[len(lens) // 2] if lens else 0
    for i, ln in enumerate(lines):
        # 주어진 문장 넣기: 첫 문단(주어진 문장)은 지문과 따로 둔다. 짧게 끝나는 줄이 문장 끝이고 다음 줄이 대문자로 시작하면 문단 끝으로 본다.
        brk = ln.startswith('¶')
        ln = ln.lstrip('¶')
        if out and not brk and not re.match(r'^(\([A-E]\)|\*|[①-⑤]|\[)', ln):
            out[-1] += ' ' + ln
        else:
            out.append(ln)
    return chr(10).join(out)


def parse_item(no, lines, group_stem=None):
    pages = sorted({pi for pi, _ in lines})
    group = None
    body = []
    for _, s in lines:
        m = re.match(r'^\[\s*(\d+)\s*[～~]\s*(\d+)\s*\]', s)
        if m:
            group = (int(m.group(1)), int(m.group(2)))
            continue          # 묶음 안내문은 다음 문항 앞에 오므로 아래에서 처리
        body.append(s)
    text = '\n'.join(body).strip()
    text = re.sub(r'^\d{1,2}\.\s*', '', text, count=1)
    pts = 3 if re.search(r'\[\s*3점\s*\]', text) else 2
    text = re.sub(r'\[\s*3점\s*\]', '', text)
    # 줄바꿈으로 끊긴 발문을 잇는다: 첫 문장(물음표·고르시오·것은? 까지)
    m = re.search(r'(.*?(?:고르시오\.|것은\?|가\?|\?))', text, re.S)
    if m and re.search(r'[가-힣]', m.group(1)) and len(m.group(1)) < 200:
        stem = re.sub(r'\s*\n\s*', ' ', m.group(1)).strip()
        rest = text[m.end():].strip()
    elif group_stem is not None:
        stem, rest = group_stem, text
    else:
        stem = text.split('\n')[0]
        rest = '\n'.join(text.split('\n')[1:]).strip()
    stem = re.sub('｛[GS]｝', '', stem.replace('¶', ''))
    choices = None
    if not any(k in stem for k in IN_TEXT_STEMS):
        idx = [rest.rfind(c) for c in CIRC]
        pos = rest.find('①')
        # 선택지 블록: 첫 ① 부터. 본문에 ①이 먼저 나오면 마지막 ① 이전의 연속 ①②③④⑤ 쌍을 찾는다
        cand = [m2.start() for m2 in re.finditer('①', rest)]
        for p in reversed(cand):
            seg = rest[p:]
            if all(c in seg for c in CIRC) and [seg.find(c) for c in CIRC] == sorted(seg.find(c) for c in CIRC):
                pos = p
                break
        if pos >= 0 and all(c in rest[pos:] for c in CIRC):
            blk = rest[pos:]
            body_txt = rest[:pos].strip()
            parts = re.split('([①②③④⑤])', blk)
            ch = []
            for i in range(1, len(parts), 2):
                ch.append(re.sub(r'\s*\n\s*', ' ', parts[i + 1]).replace('¶', '').strip())
            if len(ch) == 5:
                choices = ch
                rest = body_txt
    return {'no': no, 'pages': pages, 'points': pts, 'stem': stem, 'body': reflow(rest, first_break='주어진 문장' in stem and '들어가기' in stem), 'choices': choices,
            'choices_in_text': any(k in stem for k in IN_TEXT_STEMS), 'group': group}


def group_passage(head_lines, typ=None):
    """묶음 안내문([41～42] 다음 글을 읽고, 물음에 답하시오.) 뒤에 오는 공통 지문. 듣기 묶음처럼 지문이 없으면 ''."""
    text = chr(10).join(s for _, s in head_lines)
    m = re.match(r'^\[[^\]]*\][^\n]*?답하시오\.?', text, re.S)
    rest = text[m.end():] if m else chr(10).join(text.split(chr(10))[1:])
    rest = re.sub(r'\[\s*3점\s*\]', '', rest).strip()
    if len(rest) < 50:
        return ''
    body, _ = resolve_blanks(marks(rest, typ), False)
    body = re.sub(r'<u>\s*(\([A-E]\))\s*</u>', r'\1', body)       # 문단 기호 (A)~(D)는 밑줄이 아니다
    return reflow(body)


def group_headers(lines):
    hs = []
    for pi, s in lines:
        m = re.match(r'^\[\s*(\d+)\s*[～~]\s*(\d+)\s*\]\s*(.*)', s)
        if m:
            hs.append((int(m.group(1)), int(m.group(2)), m.group(3).strip(), pi))
    return hs


def parse_commentary(pages):
    full = '\n'.join(pages)
    ans = {int(a): b for a, b in re.findall(r'(\d{2})\.\s*([①②③④⑤])', full[:1500])}
    if len(ans) < 45:                               # 교육청 해설표: '1 ② 2 ⑤' (번호 뒤에 점이 없다)
        head = full[:1500]
        k = head.find('정 답') if '정 답' in head else head.find('정답')
        for a, b in re.findall(r'(?<!\d)(\d{1,2})\s+([①②③④⑤])', head[max(k, 0):]):
            ans.setdefault(int(a), b)
    if len(ans) < 45:                               # 옛 해설표: 번호 줄 다음에 정답이 같은 순서로 나온다
        for ln in full[:1500].split(chr(10)):
            nums = re.findall(r'(\d{2})\.', ln)
            circ = re.findall('[①②③④⑤]', ln)
            if nums and len(nums) == len(circ):
                ans.update({int(n): c for n, c in zip(nums, circ)})
    types, cm = {}, {}
    ms = list(re.finditer(r'^(\d{1,2})\.\s*\[출제\s?의도\]\s*(.+)$', full, re.M))
    for k, m in enumerate(ms):
        no = int(m.group(1))
        end = ms[k + 1].start() if k + 1 < len(ms) else len(full)
        types[no] = m.group(2).strip()
        cm[no] = full[m.end():end].strip()
    # 2026-10-29: 묶음 해설(16~17·41~42·43~45)이 앞 문항에 붙던 문제 → 떼어 내 묶음 첫 문항으로
    import fix_group_commentary as FG
    rest, gblocks = FG.split_groups(full)
    if gblocks:
        ms = list(FG.ITEM.finditer(rest))
        cm = {}
        for k, m in enumerate(ms):
            end = ms[k + 1].start() if k + 1 < len(ms) else len(rest)
            le = rest.find('\n', m.end())
            cm[int(m.group(1))] = rest[(le if le >= 0 else m.end()):end].strip()
        for first, body in gblocks.items():
            lab = {16: '[16~17]', 41: '[41~42]', 43: '[43~45]'}[first]
            cm[first] = (lab + '\n' + body + ('\n' + cm[first] if cm.get(first) else '')).strip()
    return ans, types, cm


def decode_garbled(hpages, rows):
    """글꼴이 깨진 해설표('1 Ø´ 2 Ø¾ ...')의 정답 기호를 EBSi 오답률 표(정답이 알려진 15문항)로 풀이한다.
    기호 5종이 ①~⑤ 에 하나씩 대응하고 15문항이 모두 모순 없을 때만 받아들인다."""
    head = chr(10).join(hpages)[:1500]
    sym = {int(n): c for n, c in re.findall(r'(?<!\d)(\d{1,2})\s*Ø(.)', head)}
    if len(sym) < 45:
        return {}
    mp = {}
    for r in rows:
        no, circ = r[1], r[4]
        if no in sym:
            if mp.setdefault(sym[no], circ) != circ:
                return {}
    if len(mp) != 5 or len(set(mp.values())) != 5:
        return {}
    return {n: mp[c] for n, c in sym.items() if c in mp}


def find_top_key(top, exam):
    """EBSi 오답률 표의 시험 번호: 같은 달, 4월 학평이 5월에 시행된 해는 앞 달로 찾는다"""
    y, mo = exam.split('.')
    months = [9] if exam == '2022.08' else [int(mo), int(mo) - 1]
    for m in months:
        k = next((k for k in top if k[:4] == y and int(k[4:6]) == m), None)
        if k:
            return k
    return None


def find_image(exam, no, grp):
    base = f'연계DB/문항DB/기출/{exam}/'
    names = [f'Q{no}.png']
    if grp:
        names.append(f'Q{grp[0]}-{grp[1]}.png')
    for n in names:
        if os.path.exists(os.path.join(ROOT, base + n)):
            return base + n
    return None


def image_for(exam, no, grp, pdf, regions, cache, outdir, report):
    """기존 문항 이미지가 있으면 그 경로, 없으면 시험지에서 잘라 `이미지/Q<번호>.jpg` 로 만든다"""
    old = find_image(exam, no, grp)
    if old:
        return old
    img = layout.crop_image(pdf, regions.get(no, []), resolution=200, pad=6, cache=cache)
    if img is None:
        return None
    d = os.path.join(outdir, '이미지')
    os.makedirs(d, exist_ok=True)
    img.save(os.path.join(d, f'Q{no}.jpg'), quality=88)
    report['image_made'].append(no)
    return f'문제은행/DB/기출/{exam}/이미지/Q{no}.jpg'


def main():
    exam = sys.argv[1]
    folder = os.path.join(ROOT, '기출', exam)
    q = next((f for f in ('영어_홀수형_문제.pdf', '영어_문제.pdf') if os.path.exists(os.path.join(folder, f))), None)
    form = '홀수형' if q and '홀수형' in q else ''
    qpath = a3_copy(os.path.join(folder, q), exam)
    qpages = pdf_text_2col(qpath)
    lines = clean_lines(qpages)
    items, heads = split_items(lines)
    hpages = pdf_text(os.path.join(folder, '영어_해설.pdf'))
    ans, types, comm = parse_commentary(hpages)

    y, mo = exam.split('.')
    org = '평가원' if (int(mo) in (6, 9, 11) or exam in ('2022.08', '2020.12')) else '교육청'
    top = json.load(open(os.path.join(ROOT, '문제은행', 'DB', '통계', 'ebsi_오답률TOP15_원본.json'), encoding='utf-8'))
    tkey = find_top_key(top, exam)
    wrong = {r[1]: {'순위': r[0], '오답률': r[2], '선택지비율': r[5:10]} for r in (top[tkey]['rows'] if tkey else [])}
    if len(ans) < 45 and tkey:
        ans = {**decode_garbled(hpages, top[tkey]['rows']), **ans}
    outdir = os.path.join(ROOT, '문제은행', 'DB', '기출', exam)
    os.makedirs(outdir, exist_ok=True)
    report = {'exam': exam, 'items_found': len(items), 'missing': [n for n in range(1, 46) if n not in items],
              'problems': []}
    pdf = pdfplumber.open(qpath)
    regions = layout.find_regions(pdf)
    tabs = layout.tables_by_item(pdf, regions)
    imgcache = {}
    report['image_made'] = []
    for no in range(1, 46):
        if no not in items:
            continue
        head = next((h for h in heads if h[0] <= no <= h[1]), None)
        grp = head[:3] if head else None
        it = parse_item(no, items[no], grp[2] if grp else None)
        passage = group_passage(head[3], types.get(no)) if head else ''
        it['stem'] = marks(it['stem'], types.get(no))
        it['body'] = marks(it['body'], types.get(no))
        it['body'], blank_status = resolve_blanks(it['body'], '빈칸' in it['stem'] and no in range(31, 35))
        if it['choices']:
            it['choices'] = [marks(c, types.get(no)) for c in it['choices']]
        a = ans.get(no)
        if it['choices'] and not any(c.strip() for c in it['choices']) and (tabs.get(no) or '표' in it['stem']):
            it['choices'] = None          # ①~⑤ 만 있고 내용은 표의 줄인 경우
            it['choices_in_table'] = True
        elif it['choices'] and not any(c.strip() for c in it['choices']) and '그림' in it['stem']:
            it['choices'] = None          # 그림 안에 ①~⑤ 가 있는 경우
            it['choices_in_image'] = True
        if '그림에서' in it['stem']:
            it['choices'] = None          # 그림 속 글자는 선택지가 아니다
        if it['choices'] is None and '그림에서' in it['stem']:
            it['choices_in_image'] = True
        elif it['choices'] is None and tabs.get(no) and any('Program' in (r[0] or '') or len(r) >= 4 for r in tabs[no][0]):
            it['choices_in_table'] = True
        elif it['choices'] is None and not it['choices_in_text'] and not it.get('choices_in_table'):
            report['problems'].append((no, '선택지 5개를 못 나눔'))
        if a is None:
            report['problems'].append((no, '정답 없음'))
        rec = {
            'id': f'{exam}-{no:02d}', 'exam': {'시행연도': int(y), '시행월': int(mo), '학년도': int(y) + (1 if org == '평가원' else 0), '기관': org, '형': form or '없음'},
            'no': no, 'area': '듣기' if no <= 17 else '읽기', 'group': list(grp[:2]) if grp else None,
            'type': None if (types.get(no) or '').endswith('다.') else types.get(no), 'intent': types.get(no) if (types.get(no) or '').endswith('다.') else None, 'points': it['points'], 'answer': a,
            'text': {'stem': it['stem'], 'body': it['body'], 'choices': it['choices'], 'choices_in_text': it['choices_in_text'], 'choices_in_image': it.get('choices_in_image', False), 'choices_in_table': it.get('choices_in_table', False), 'blank': blank_status,
                     'group_passage': passage or None},
            'commentary': comm.get(no),
            'wrong_rate': wrong.get(no), 'tables': tabs.get(no), 'image': image_for(exam, no, grp, pdf, regions, imgcache, outdir, report),
            'source': {'pdf': f'기출/{exam}/{q}', 'pages': it['pages']},
            'share': '비공개'}
        with open(os.path.join(outdir, f'{exam}-{no:02d}.json'), 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
    with open(os.path.join(outdir, '_시험.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
