"""빈칸 추론 변형 문항 규칙 검사 (시범판). 사용: python -X utf8 -I check_blank.py <변형 JSON>
검사: 길이·문장 수·빈칸 1개, 선택지 5개와 형식 통일, a/an, 5개를 빈칸에 넣은 문장(문법 검토용), 어휘(기출에 없는 낱말), 요령 배제(정답 길이·본문 낱말 겹침)."""
import glob, json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BL = '＿＿＿'
STOP = set('a an the of to in on at for with by from as is are was were be been being and or but that this these those it its they them their he she his her we our you your i not no so if when while than then there here which who whom whose what how also can could will would may might do does did have has had'.split())


def words(text):
    return re.findall(r"[A-Za-z]+(?:'[a-z]+)?", text)


def corpus():
    vocab = collections.Counter()
    for p in glob.glob(os.path.join(ROOT, 'DB', '기출', '*', '*-*.json')):
        if p.endswith('_시험.json'):
            continue
        r = json.load(open(p, encoding='utf-8'))
        if r['text'].get('text_quality') == 'ocr':
            continue
        t = (r['text'].get('body') or '') + ' ' + ' '.join(r['text'].get('choices') or [])
        for w in words(t):
            vocab[w.lower()] += 1
    return vocab


def form_class(choice):
    w = choice.split()[0].lower()
    if w in ('a', 'an', 'the'):
        return 'DET'
    if w.endswith('s') and not w.endswith('ss'):
        return 'VERB_S'
    return 'BASE'


def an_errors(text):
    errs = []
    for m in re.finditer(r"\b(a|an)\s+([A-Za-z]+)", text, re.I):
        art, nxt = m.group(1).lower(), m.group(2).lower()
        vowel = nxt[0] in 'aeiou'
        if nxt.startswith(('hour', 'honest', 'heir')):
            vowel = True
        if nxt.startswith(('uni', 'use', 'usu', 'one', 'eu', 'ubiq')):
            vowel = False
        if (art == 'a' and vowel) or (art == 'an' and not vowel):
            errs.append(m.group(0))
    return errs


def check(item, vocab):
    out = {'id': item['id'], 'tier': item['tier'], 'problems': [], 'info': {}}
    P = item['passage']
    text = ' '.join(P)
    nw = len(words(text))
    out['info']['단어 수'] = nw
    out['info']['문장 수'] = len(P)
    if not 120 <= nw <= 190:
        out['problems'].append(f'지문 단어 수 {nw}: 120~190 범위 밖')
    if not 4 <= len(P) <= 13:
        out['problems'].append(f'문장 수 {len(P)}')
    nb = text.count(BL)
    if nb != 1:
        out['problems'].append(f'빈칸 {nb}개')
    idx = next((i for i, s in enumerate(P) if BL in s), None)
    if idx is not None:
        r = (idx + 1) / len(P)
        out['info']['빈칸 문장'] = f'{idx + 1}/{len(P)}'
        out['info']['빈칸 위치'] = '앞' if r <= 1 / 3 else ('중간' if r <= 2 / 3 else '뒤')
        if not P[idx].rstrip().endswith(('.', '?', '!', '."')):
            out['problems'].append('빈칸 문장이 마침표로 끝나지 않음')
    ch = item['choices']
    if len(ch) != 5 or len({c.strip().lower() for c in ch}) != 5:
        out['problems'].append('선택지가 5개가 아니거나 중복')
    forms = [form_class(c) for c in ch]
    out['info']['선택지 형식'] = forms
    if len(set(forms)) != 1:
        out['problems'].append(f'선택지 형식이 다름: {forms}')
    pre = P[idx].split(BL)[0].rstrip().split()[-1].lower() if idx is not None and P[idx].split(BL)[0].strip() else ''
    out['info']['빈칸 바로 앞 낱말'] = pre
    if pre in ('a', 'an'):
        for c in ch:
            v = c.split()[0].lower()[0] in 'aeiou'
            if (pre == 'an') != v:
                out['problems'].append(f'빈칸 앞 {pre} 와 선택지 "{c}" 의 모음/자음 불일치')
    errs = an_errors(text + ' ' + ' '.join(ch))
    if errs:
        out['problems'].append(f'a/an 오류 의심: {errs}')
    out['filled'] = [P[idx].replace(BL, c) for c in ch] if idx is not None else []
    # 어휘
    unseen = sorted({w.lower() for w in words(text + ' ' + ' '.join(ch)) if vocab[w.lower()] == 0})
    out['info']['기출에 없는 낱말(검토용)'] = unseen
    # 요령 배제
    a = item['answer'] - 1
    lens = [len(words(c)) for c in ch]
    out['info']['선택지 단어 수'] = lens
    cl = [len(c) for c in ch]
    out['info']['선택지 글자 수'] = cl
    # 기출 268문항: 정답이 글자 수로 유일하게 가장 긴 경우는 13%(무작위면 20%)이므로 정답이 가장 긴 것을 금지한다
    if cl[a] == max(cl):
        out['problems'].append('정답이 글자 수로 가장 긴 선택지(요령 단서)')
    pc = {w.lower() for w in words(text)} - STOP
    ov = [len({w.lower() for w in words(c)} - STOP & pc) for c in ch]
    out['info']['본문 낱말과 겹치는 내용어 수'] = ov
    others = [o for i, o in enumerate(ov) if i != a]
    if ov[a] < min(others):
        out['info']['요령 참고'] = '정답이 본문 낱말과 가장 적게 겹침(기출 정답 경향과 같음)'
    elif ov[a] > max(others) + 1:
        out['problems'].append('정답이 본문 낱말과 가장 많이 겹침(낱말 겹침 요령으로 풀릴 수 있음)')
    return out


if __name__ == '__main__':
    d = json.load(open(sys.argv[1], encoding='utf-8'))
    vocab = corpus()
    res = [check(i, vocab) for i in d['items']]
    json.dump(res, open(sys.argv[1].replace('.json', '_규칙검사.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in res:
        print('==', r['id'], '문제:', r['problems'] or '없음')
        for k, v in r['info'].items():
            print('   ', k, ':', v)
