"""기출 문항을 '원래 글'로 되돌린다(유형 적합도 분석기 역검증용).
빈칸 채우기, 순서 맞추기, 주어진 문장 넣기, 무관한 문장 빼기, 어법·어휘 바로잡기, 요약문 떼기.
돌려주는 값: 문장 목록 없이 한 덩어리 글(str). 각주(*)·번호·밑줄 표시는 지운다."""
import json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CIR = '①②③④⑤'
_FIX = {}


def _fixes():
    """어법·어휘 분석 결과(jsonl)의 고친 형태: {id: (밑줄 번호, 고친 말)}"""
    if not _FIX:
        for name in ('어법', '어휘'):
            p = os.path.join(ROOT, '규격', '언어분석', '결과', f'{name}.jsonl')
            for line in open(p, encoding='utf-8'):
                r = json.loads(line)
                for it in r['items']:
                    no = str(it['no'])
                    if (it.get('correct') is False or it.get('appropriate') is False) and (no.isdigit() or no in CIR):
                        fix = re.split(r'\s*/\s*|\s*\(', it.get('fix') or '')[0].strip()   # 'weaker / lower', 'that (which)' → 첫 형태
                        _FIX[r['id']] = (int(no) if no.isdigit() else CIR.index(no) + 1, fix)
        # 분석에 들어가지 않은 스캔본 시험(시험지 정답과 원문으로 확인)
        _FIX.update({'2020.12-29': (5, 'whether'), '2020.12-30': (5, 'had'), '2020.05-29': (4, 'close')})
    return _FIX


def clean(t):
    t = re.sub(r'\n\*.*', '', t, flags=re.S)                 # 각주
    t = re.sub(r'</?u>', '', t)
    t = re.sub(r'\(\s*[①②③④⑤]\s*\)|[①②③④⑤]', ' ', t)
    t = re.sub(r'\([a-e]\)\s*', '', t)                       # 장문 지칭·어휘 표시 (a)~(e)
    t = re.sub(r'\(([A-C])\)\s*\[([^\]/]+)/([^\]]+)\]', r'\2', t)   # 네모 고르기는 앞 낱말(정답 반영은 따로)
    return re.sub(r'[ \t]+', ' ', re.sub(r'\s*\n\s*', '\n', t)).strip()


def restore(rec):
    t = rec['text']
    body, ch, typ = t.get('body') or '', t.get('choices') or [], rec.get('type_std')
    ans = CIR.index(rec['answer']) if rec.get('answer') in CIR else None
    if rec['no'] in (41, 43):
        body = t.get('group_passage') or body
    body = re.sub(r'\n\*[^\n]*', '', body)        # 각주 줄은 먼저 뺀다(순서를 바꾸면 끝에 있던 각주가 가운데로 온다)
    if typ == '빈칸 추론' and ans is not None and ch:
        body = body.replace('＿＿＿', ch[ans], 1)
    elif typ == '글의 순서 배열' and ans is not None and ch:
        given, rest = body.split('\n(A)', 1)
        segs = dict(re.findall(r'\(([ABC])\)\s*(.*?)(?=\n\([ABC]\)|$)', '(A)' + rest, re.S))
        order = re.findall(r'[ABC]', ch[ans])
        body = given + '\n' + '\n'.join(segs.get(k, '') for k in order)
    elif typ == '주어진 문장 넣기' and ans is not None:
        given, rest = body.split('\n', 1)
        parts = re.split(r'\(\s*[①②③④⑤]\s*\)', rest)
        if len(parts) == 6:
            parts[ans] = parts[ans].rstrip() + ' ' + given.strip() + ' '
            body = ''.join(parts)
    elif typ == '무관한 문장 찾기' and ans is not None and ch:
        body = body.rstrip() + ' ' + ' '.join(c for k, c in enumerate(ch) if k != ans)
    elif typ == '무관한 문장 찾기' and ans is not None:          # 선택지가 지문 속 번호(옮겨 적은 시험지)
        body = re.sub(r'%s[^①②③④⑤]*?(?=[①②③④⑤]|$)' % CIR[ans], ' ', re.sub(r'\n\*[^\n]*', '', body), count=1)
    elif typ == '어휘의 적절성' and ans is not None and ch and '…' in ch[ans] and '[' in body:
        words = [w.strip() for w in re.split(r'…+', ch[ans])]   # 네모 고르기: 정답 선택지의 낱말을 (A)(B)(C) 자리에 넣는다
        for lab, w in zip('ABC', words):
            body = re.sub(r'\(%s\)\s*\[[^\]]*\]' % lab, w, body, count=1)
    elif typ in ('어법 판단', '어휘의 적절성') and rec['id'] in _fixes():
        no, fix = _fixes()[rec['id']]
        if fix:
            body = re.sub(r'%s\s*<u>[^<]*</u>' % CIR[no - 1], fix, body, count=1)
    elif typ == '요약문 완성':
        body = body.split('\n(A) (B)')[0].split('↓')[0]   # 옮겨 적은 시험지는 요약문 앞에 ↓ 가 있다
        k = body.find('(A)')                      # 요약문: (A) 빈칸이 처음 나오는 줄(또는 화살표 기호) 앞까지가 본문
        if k > 0:
            cut = max(body.rfind('\n', 0, k), body.rfind('\U000f003b', 0, k))
            body = body[:cut] if cut > 0 else body
    return clean(body)


if __name__ == '__main__':
    import sys
    for i in sys.argv[1:]:
        r = json.load(open(os.path.join(ROOT, 'DB', '기출', i[:7], i + '.json'), encoding='utf-8'))
        print(i, r['type_std'], '\n', restore(r), '\n')
