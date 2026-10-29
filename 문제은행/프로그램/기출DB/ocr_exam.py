"""글자층이 없는 스캔본 시험지(2020.12 수능, 2020.05·2020.04 학평)를 OCR로 변환한다 (시범판).
사용: python -X utf8 -I ocr_exam.py <시험> [문제 PDF 이름]
- 쪽을 300dpi로 그려 단(왼쪽/오른쪽)마다 한국어+영어 OCR(Tesseract)로 줄과 위치를 얻는다.
- 문항 번호 줄로 문항 영역을 나누고, 영역을 잘라 이미지로 저장하고, 영역을 다시 OCR해 `ocr_text` 로 담는다.
- 정답·유형·해설·오답률은 build_exam 과 같은 방법(해설 PDF, EBSi 오답률 표)이다.
- 글자는 OCR 결과라 틀릴 수 있다(`text_quality: ocr`). 선택지는 나누지 않고 영역 글자 전체를 둔다.
"""
import csv, json, os, re, subprocess, sys, tempfile
import pdfplumber
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_exam as B

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = B.ROOT
TESS = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TESSDATA = os.path.join(ROOT, '문제은행', '프로그램', 'ocr', 'tessdata')
DPI = 300
CACHE = os.path.join(ROOT, '문제은행', '프로그램', 'ocr', '캐시')
os.makedirs(CACHE, exist_ok=True)
MARK = re.compile(r'^\W{0,2}(\d{1,2})\s?[\.\,．·](?:\s*\S|\s*$)')
HEAD = re.compile(r'^\W{0,2}\[\s*(\d{1,2})\s*[~～\-]\s*(\d{1,2})\s*\]')


def tesseract(img, psm, tsv=False):
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, 'in.png')
        img.save(src)
        out = os.path.join(d, 'out')
        env = dict(os.environ, TESSDATA_PREFIX=TESSDATA)
        args = [TESS, src, out, '-l', 'kor+eng', '--psm', str(psm)] + (['tsv'] if tsv else [])
        subprocess.run(args, env=env, capture_output=True)
        return open(out + ('.tsv' if tsv else '.txt'), encoding='utf-8', errors='replace').read()


def ocr_lines(img):
    """(text, left, top, bottom) 줄 목록 (픽셀)"""
    rows = tesseract(img, 4, tsv=True).splitlines()[1:]
    lines = {}
    for r in rows:
        c = r.split('\t')
        if len(c) < 12 or not c[11].strip() or float(c[10]) < 0:
            continue
        key = tuple(c[2:5])
        l, t, w, h = (int(c[6]), int(c[7]), int(c[8]), int(c[9]))
        e = lines.setdefault(key, {'words': [], 'left': l, 'top': t, 'bottom': t + h})
        e['words'].append(c[11])
        e['left'] = min(e['left'], l)
        e['top'] = min(e['top'], t)
        e['bottom'] = max(e['bottom'], t + h)
    return sorted(({'text': ' '.join(v['words']), 'x0': v['left'], 'top': v['top'], 'bottom': v['bottom']}
                   for v in lines.values()), key=lambda x: x['top'])


def ink_bbox(img, margin=10):
    g = img.convert('L').point(lambda v: 0 if v > 200 else 255)
    bb = g.getbbox()
    if not bb:
        return None
    return (max(bb[0] - margin, 0), max(bb[1] - margin, 0), min(bb[2] + margin, img.width), min(bb[3] + margin, img.height))


def main():
    exam = sys.argv[1]
    folder = os.path.join(ROOT, '기출', exam)
    q = sys.argv[2] if len(sys.argv) > 2 else next(f for f in ('영어_홀수형_문제.pdf', '영어_문제.pdf') if os.path.exists(os.path.join(folder, f)))
    form = '홀수형' if '홀수형' in q else ''
    y, mo = exam.split('.')
    org = '평가원' if (int(mo) in (6, 9, 11) or exam in ('2022.08', '2020.12')) else '교육청'
    hpages = B.pdf_text(os.path.join(folder, '영어_해설.pdf'))
    ans, types, comm = B.parse_commentary(hpages)
    top = json.load(open(os.path.join(ROOT, '문제은행', 'DB', '통계', 'ebsi_오답률TOP15_원본.json'), encoding='utf-8'))
    tkey = B.find_top_key(top, exam)
    if len(ans) < 45 and tkey:
        ans = {**B.decode_garbled(hpages, top[tkey]['rows']), **ans}
    wrong = {r[1]: {'순위': r[0], '오답률': r[2], '선택지비율': r[5:10], 'points': r[3]} for r in (top[tkey]['rows'] if tkey else [])}

    # 1) 쪽·단 이미지와 OCR 줄
    cols = []        # (쪽, 단, 이미지, 줄)
    with pdfplumber.open(os.path.join(folder, q)) as pdf:
        for pi, pg in enumerate(pdf.pages):
            im = pg.to_image(resolution=DPI).original.convert('RGB')
            half = im.width // 2
            for ci, box in enumerate(((0, 0, half, im.height), (half, 0, im.width, im.height))):
                col = im.crop(box)
                ck = os.path.join(CACHE, f'{exam}_{q}_{pi}_{ci}.json')
                if os.path.exists(ck):
                    lines = json.load(open(ck, encoding='utf-8'))
                else:
                    lines = ocr_lines(col)
                    json.dump(lines, open(ck, 'w', encoding='utf-8'), ensure_ascii=False)
                cols.append((pi, ci, col, lines))
    # 2) 문항 표시(번호 줄) 찾기: 1부터 차례로
    marks, exp, gaps = [], 1, []
    for pi, ci, col, lines in cols:
        usable = [l for l in lines if 0.06 * col.height < l['top'] < 0.93 * col.height]
        if not usable:
            continue
        for ln in usable:
            if ln['x0'] > 0.45 * col.width:
                continue
            m = MARK.match(ln['text'])
            n = int(m.group(1)) if m else None
            if m and n is not None and not (exp <= n <= exp + 2) and len(str(n)) == len(str(exp)) and sum(a != b for a, b in zip(str(n), str(exp))) == 1:
                n = exp                                   # OCR이 숫자 한 글자를 잘못 읽은 번호(35 를 30 으로)
            if m and n is not None and exp <= n <= min(exp + 2, 45):
                for gap in range(exp, n):          # OCR이 못 읽은 번호: 앞 문항 영역에 함께 들어간다
                    gaps.append(gap)
                marks.append((pi, ci, ln['top'], 'item', n))
                exp = n + 1
            elif HEAD.match(ln['text']):
                marks.append((pi, ci, ln['top'], 'head', int(HEAD.match(ln['text']).group(1))))
    # 3) 영역
    owners = []
    for k, mk in enumerate(marks):
        owners.append(mk[4] if mk[3] == 'item' else next((m[4] for m in marks[k + 1:] if m[3] == 'item'), None))
    regions = {n: [] for n in range(1, 46)}
    cur = None
    for pi, ci, col, lines in cols:
        here = [(mk, ow) for mk, ow in zip(marks, owners) if mk[0] == pi and mk[1] == ci]
        y0 = int(0.06 * col.height)
        bottom = int(0.93 * col.height)
        for mk, ow in here:
            t = max(mk[2] - 12, 0)
            if cur is not None and t > y0 + 6:
                regions[cur].append((pi, ci, y0, t))
            y0 = t
            cur = ow
        if cur is not None and bottom > y0 + 6:
            regions[cur].append((pi, ci, y0, bottom))
    colimg = {(pi, ci): col for pi, ci, col, _ in cols}
    outdir = os.path.join(ROOT, '문제은행', 'DB', '기출', exam)
    os.makedirs(os.path.join(outdir, '이미지'), exist_ok=True)
    from PIL import Image
    report = {'exam': exam, 'items_found': sum(1 for n in regions if regions[n]), 'missing': [n for n in range(1, 46) if not regions[n] and n not in gaps], 'gaps_shared_with_previous': gaps, 'ocr': True}
    for g in gaps:
        regions[g] = list(regions[g - 1]) if g > 1 else []
    for no in range(1, 46):
        if not regions[no]:
            continue
        parts = []
        for pi, ci, a, b in regions[no]:
            strip = colimg[(pi, ci)].crop((0, a, colimg[(pi, ci)].width, b))
            bb = ink_bbox(strip)
            if bb:
                parts.append(strip.crop((bb[0], 0, bb[2], strip.height)))
        w = max(p.width for p in parts)
        h = sum(p.height for p in parts)
        img = Image.new('RGB', (w, h), 'white')
        yy = 0
        for p in parts:
            img.paste(p, (0, yy))
            yy += p.height
        img.save(os.path.join(outdir, '이미지', f'Q{no}.jpg'), quality=88)
        raw = tesseract(img, 6)
        text = re.sub(r'^\W{0,2}\d{1,2}\s?[\.\,．·]\s*', '', raw.strip(), count=1)
        first = text.split('\n')[0].strip()
        rec = {
            'id': f'{exam}-{no:02d}', 'exam': {'시행연도': int(y), '시행월': int(mo), '학년도': int(y) + (1 if org == '평가원' else 0), '기관': org, '형': form or '없음'},
            'no': no, 'area': '듣기' if no <= 17 else '읽기', 'group': None,
            'type': None if (types.get(no) or '').endswith('다.') else types.get(no),
            'intent': types.get(no) if (types.get(no) or '').endswith('다.') else None,
            'points': (wrong.get(no) or {}).get('points') or (3 if re.search(r'3\s?점', raw[:300]) else 2), 'answer': ans.get(no),
            'text': {'stem': first, 'body': None, 'choices': None, 'ocr_text': text, 'text_quality': 'ocr',
                     'choices_in_text': False, 'choices_in_image': False, 'choices_in_table': False},
            'commentary': comm.get(no), 'wrong_rate': wrong.get(no), 'tables': None,
            'image': f'문제은행/DB/기출/{exam}/이미지/Q{no}.jpg',
            'source': {'pdf': f'기출/{exam}/{q}', 'pages': sorted({r[0] + 1 for r in regions[no]})}, 'share': '비공개'}
        if no in gaps:
            rec['image_shared_with'] = no - 1          # 번호를 못 읽어 앞 문항과 같은 영역(그림·글자)을 쓴다
        with open(os.path.join(outdir, f'{exam}-{no:02d}.json'), 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
    with open(os.path.join(outdir, '_시험.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
