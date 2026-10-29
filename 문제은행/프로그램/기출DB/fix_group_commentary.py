"""묶음 문항(16~17, 41~42, 43~45) 해설이 앞 문항에 붙어 있던 문제를 고친다 (2026-10-29).

원인: parse_commentary 가 'NN. [출제의도]' 표시로만 해설을 나눠서, 그 앞에 오는 묶음 머리
('[41~42] [해석] …' 또는 '41∼42 장문의 이해 [해석] …')와 지문 해석이 바로 앞 문항(15·40·42 등)에 붙었다.
교육청 해설은 두 단 배치라 묶음 덩어리가 엉뚱한 문항 사이에 끼기도 한다.

방법: 해설 전체에서 묶음 덩어리(머리 줄 ~ 다음 'NN. [출제의도]' 또는 다음 묶음 머리 직전)를 먼저 떼어 낸 뒤
문항별로 나누고, 떼어 낸 덩어리는 묶음 첫 문항(16·41·43) 해설 앞에 붙인다.
DB JSON 은 commentary 칸만 바꾼다(다른 칸은 손대지 않음). 바꾸기 전 파일은 백업 폴더에 둔다.

쓰기: python -X utf8 fix_group_commentary.py [--dry]  → 결과를 fix_group_commentary.log 에 남김
"""
import json, os, re, shutil, sys
sys.argv = sys.argv[:1] + [a for a in sys.argv[1:]]
DRY = '--dry' in sys.argv
import build_exam as B

# 머리 모양: '[41~42]', '41∼42 장문의 이해', '[43-45]', '41~42. [출제의도] …', '1 6 ~1 7 긴 담화 듣기'
HEAD = re.compile(r'^\[?\s*(1\s?6|4\s?1|4\s?3)\s*[~～∼\-]\s*(1\s?7|4\s?2|4\s?5)\s*\]?\.?[ \t]*(?:긴\s*담화\s*듣기|장문의\s*이해|\[출제\s?의도\][^\n]*)?[ \t]*(?=$|\[해석\]|\[풀이\]|\[출제)', re.M)
ITEM = re.compile(r'^(\d{1,2})\.\s*\[출제\s?의도\]', re.M)


def split_groups(full):
    """해설 전체 → (묶음 덩어리를 뺀 글, {첫 문항 번호: 덩어리 글})"""
    blocks, cut = {}, []
    hs = list(HEAD.finditer(full))
    for k, h in enumerate(hs):
        nxt = [m.start() for m in ITEM.finditer(full, h.end())][:1]
        ends = nxt + ([hs[k + 1].start()] if k + 1 < len(hs) else [])
        end = min(ends) if ends else len(full)
        first = int(h.group(1).replace(' ', ''))
        body = full[h.end():end].strip()
        if first in blocks:                      # 같은 묶음 머리가 두 번 나오면 둘 다 살린다
            blocks[first] += '\n' + body
        else:
            blocks[first] = body
        cut.append((h.start(), end))
    out, pos = [], 0
    for a, b in sorted(cut):
        out.append(full[pos:a]); pos = b
    out.append(full[pos:])
    return ''.join(out), blocks


def commentary_for(exam):
    full = '\n'.join(B.pdf_text(os.path.join(B.ROOT, '기출', exam, '영어_해설.pdf')))
    rest, blocks = split_groups(full)
    ms = list(ITEM.finditer(rest))
    cm = {}
    for k, m in enumerate(ms):
        no = int(m.group(1))
        end = ms[k + 1].start() if k + 1 < len(ms) else len(rest)
        line_end = rest.find('\n', m.end())
        cm[no] = rest[(line_end if line_end >= 0 else m.end()):end].strip()
    for first, body in blocks.items():
        lab = {16: '[16~17]', 41: '[41~42]', 43: '[43~45]'}[first]
        cm[first] = (lab + '\n' + body + ('\n' + cm[first] if cm.get(first) else '')).strip()
    return cm, blocks


def main():
    dbroot = os.path.join(B.ROOT, '문제은행', 'DB', '기출')
    bak = os.path.join(B.ROOT, '문제은행', 'DB', '백업_해설묶음_20261029')
    log = []
    exams = sorted(d for d in os.listdir(dbroot) if os.path.isdir(os.path.join(dbroot, d)) and re.match(r'\d{4}\.\d{2}$', d))
    for ex in exams:
        try:
            cm, blocks = commentary_for(ex)
        except Exception as e:                   # 해설 PDF가 없거나 읽기 실패
            log.append(f'{ex}\t실패\t{e}'); continue
        changed = []
        for no in range(1, 46):
            p = os.path.join(dbroot, ex, f'{ex}-{no:02d}.json')
            if not os.path.exists(p):
                continue
            d = json.load(open(p, encoding='utf-8'))
            new = cm.get(no)
            old = d.get('commentary')
            if (new or '') == (old or ''):
                continue
            changed.append(no)
            if not DRY:
                os.makedirs(os.path.join(bak, ex), exist_ok=True)
                if not os.path.exists(os.path.join(bak, ex, os.path.basename(p))):
                    shutil.copy2(p, os.path.join(bak, ex, os.path.basename(p)))
                d['commentary'] = new
                json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        log.append(f'{ex}\t묶음 {sorted(blocks)}\t바뀐 문항 {changed}')
    open(os.path.join(os.path.dirname(__file__), 'fix_group_commentary.log'), 'w', encoding='utf-8').write('\n'.join(log))
    print('\n'.join(log[-5:]), '\n총', len(exams))


if __name__ == '__main__':
    main()
