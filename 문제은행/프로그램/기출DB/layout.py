"""문제 PDF의 쪽 배치 읽기: 문항마다 차지하는 영역(쪽, 단, 위·아래)을 찾고 표를 뽑고 이미지를 자른다 (시범판)."""
import re
import pdfplumber

START = re.compile(r'^(\d{1,2})\.(?!\d{1,2}(?!\d))')
HEAD = re.compile(r'^\[\s*(\d+)\s*[～~]\s*(\d+)\s*\]')
FOOT_Y = 100      # 아래쪽 이 높이는 쪽 번호·저작권 문구
TOP_Y = 60


def normal_page(pg):
    """시험지 본문 쪽(A3 세로). 끝에 붙은 작은 부록 쪽 등은 건너뛴다"""
    return pg.width > 800 and pg.bbox[0] == 0 and pg.bbox[1] == 0


def columns(pg):
    half = pg.width / 2
    return [(0, half), (half, pg.width)]


def _marks(pdf, n_items):
    """(쪽, 단, top, 종류, 값) 목록. 종류 item=문항 시작, head=묶음 안내문 시작"""
    marks, exp = [], 1
    for pi, pg in enumerate(pdf.pages):
        if not normal_page(pg):
            continue
        for ci, (x0, x1) in enumerate(columns(pg)):
            lines = pg.crop((x0, 0, x1, pg.height)).extract_text_lines(x_tolerance=1.5)
            lines = [l for l in lines if TOP_Y < l['top'] and l['bottom'] < pg.height - FOOT_Y]
            if not lines:
                continue
            from collections import Counter
            left = Counter(round(l['x0']) for l in lines).most_common(1)[0][0]
            for ln in lines:
                if ln['x0'] > left + 12:
                    continue
                s = re.sub(r'^(\d) (\d)\. ', lambda m: m.group(1) + m.group(2) + '. ', ln['text'].strip())
                m = START.match(s)
                if m and int(m.group(1)) == exp and exp <= n_items:
                    marks.append((pi, ci, ln['top'], 'item', exp))
                    exp += 1
                    continue
                if HEAD.match(s):
                    marks.append((pi, ci, ln['top'], 'head', int(HEAD.match(s).group(1))))
    return sorted(marks, key=lambda m: (m[0], m[1], m[2]))


def find_regions(pdf, n_items=45):
    """문항 번호 -> [(쪽, 단, x0, x1, top, bottom)]. 묶음 안내문은 그 묶음의 첫 문항 앞머리로 들어간다."""
    marks = _marks(pdf, n_items)
    # 안내문의 주인은 바로 다음 item
    owners = []
    for k, mk in enumerate(marks):
        if mk[3] == 'item':
            owners.append(mk[4])
        else:
            nxt = next((m[4] for m in marks[k + 1:] if m[3] == 'item'), None)
            owners.append(nxt)
    out = {n: [] for n in range(1, n_items + 1)}
    cur = None
    for pi, pg in enumerate(pdf.pages):
        if not normal_page(pg):
            continue
        for ci, (x0, x1) in enumerate(columns(pg)):
            here = [(mk, ow) for mk, ow in zip(marks, owners) if mk[0] == pi and mk[1] == ci]
            y = TOP_Y
            bottom = pg.height - FOOT_Y
            for mk, ow in here:
                top = mk[2] - 3
                if cur is not None and top > y + 2:
                    out[cur].append((pi, ci, x0, x1, y, top))
                y = top
                cur = ow
            if cur is not None and bottom > y + 2:
                out[cur].append((pi, ci, x0, x1, y, bottom))
    return out


def tables_by_item(pdf, regions):
    """표(선으로 그려진 표)를 찾아 문항에 붙인다: 문항 -> [표(행 목록)]"""
    res = {}
    for pi, pg in enumerate(pdf.pages):
        if not normal_page(pg):
            continue
        for ci, (x0, x1) in enumerate(columns(pg)):
            col = pg.crop((x0, 0, x1, pg.height))
            for t in col.find_tables():
                rows = [[(c or '').replace(chr(10), ' ').strip() for c in r] for r in t.extract()]
                if len(rows) < 2 or len(rows[0]) < 2:
                    continue
                cy = (t.bbox[1] + t.bbox[3]) / 2
                for n, regs in regions.items():
                    if any(r[0] == pi and r[1] == ci and r[4] <= cy <= r[5] for r in regs):
                        res.setdefault(n, []).append(rows)
                        break
    return res


def _merge(regs):
    """같은 쪽·단에서 맞닿은 영역을 하나로 합친다"""
    out = []
    for r in regs:
        if out and out[-1][0] == r[0] and out[-1][1] == r[1] and r[4] - out[-1][5] <= 6:
            o = out[-1]
            out[-1] = (o[0], o[1], o[2], o[3], o[4], r[5])
        else:
            out.append(r)
    return out


def _xrange(pg, box):
    """영역 안 글자·그림의 가로 범위(여백 제외)"""
    sub = pg.crop(box)
    xs0, xs1 = [], []
    for o in list(sub.chars) + list(sub.images) + list(sub.rects) + list(sub.lines) + list(sub.curves):
        if o['x1'] - o['x0'] > (box[2] - box[0]) * 0.97:
            continue
        xs0.append(o['x0'])
        xs1.append(o['x1'])
    if not xs0:
        return box[0], box[2]
    return max(min(xs0) - 8, box[0]), min(max(xs1) + 8, box[2])


def crop_image(pdf, regs, resolution=150, pad=6, cache=None):
    """문항 영역을 위에서 아래로 이어 붙인 이미지(PIL). 쪽 전체를 그린 뒤 잘라서 선이 빠지지 않게 한다."""
    from PIL import Image
    cache = cache if cache is not None else {}
    scale = resolution / 72
    parts = []
    for pi, ci, x0, x1, top, bottom in _merge(regs):
        pg = pdf.pages[pi]
        if pi not in cache:
            cache[pi] = pg.to_image(resolution=resolution).original.convert('RGB')
        box = (x0, max(top - pad, 0), x1, min(bottom, pg.height))      # 아래는 다음 문항 번호가 걸리지 않게 여백을 두지 않는다
        a, b = _xrange(pg, box)
        parts.append(cache[pi].crop((int(a * scale), int(box[1] * scale), int(b * scale), int(box[3] * scale))))
    if not parts:
        return None
    w = max(p.width for p in parts)
    h = sum(p.height for p in parts)
    img = Image.new('RGB', (w, h), 'white')
    y = 0
    for p in parts:
        img.paste(p, (0, y))
        y += p.height
    return img
