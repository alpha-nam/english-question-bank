"""표준 유형 분류 (초안, 2026-10-28).
canon_label(label, no): 평가원 해설의 공식 `[출제 의도]` 이름 -> 표준 유형
classify_stem(stem, no, body): 발문 글자로 분류(공식 이름이 없는 시험용)
"""
import re

# (정규식, 표준 유형) 순서대로 처음 맞는 것. 듣기(번호 1~17)와 읽기(18~45)를 구분해 쓴다.
LISTEN = [
    (r'그림', '그림 내용 일치'), (r'숫자|금액|지불', '숫자 정보 파악'), (r'할 일', '할 일 파악'), (r'이유', '이유 파악'),
    (r'언급|특정\s?정보', '언급 유무 파악'), (r'도표|표', '도표(표) 정보 파악'), (r'관계', '관계 파악'), (r'의견', '의견 파악'),
    (r'목적', '목적 파악'), (r'요지|주제', '요지·주제 파악'), (r'상황에\s?적절|상황 설명', '상황에 적절한 말'),
    (r'응답', '적절한 응답 고르기'), (r'세부|일치', '담화 내용 일치'),
]
READ = [
    (r'장문.*제목|제목.*장문', '장문: 제목 추론'), (r'장문.*어휘|문맥.*어휘', '장문: 어휘 추론'),
    (r'장문.*순서', '장문: 글의 순서'), (r'지칭', '장문: 지칭 추론'), (r'장문.*(세부|사실|일치)', '장문: 세부 내용 파악'),
    (r'무관|관계\s?없는', '무관한 문장 찾기'), (r'주어진\s?문장|문장\s?넣기|삽입|문장의위치', '주어진 문장 넣기'), (r'순서', '글의 순서 배열'),
    (r'요약', '요약문 완성'), (r'빈칸', '빈칸 추론'), (r'문법|어법', '어법 판단'), (r'어휘|낱말', '어휘의 적절성'),
    (r'함축', '함축 의미 추론'), (r'심경|분위기', '심경·분위기 파악'), (r'주장', '필자의 주장'), (r'목적', '글의 목적 파악'),
    (r'제목', '제목 추론'), (r'주제', '주제 추론'), (r'요지', '요지 파악'),
    (r'도표|그래프|표', '도표 내용 일치'),
    (r'안내문|실용문|공고', '안내문 내용 일치'), (r'세부|일치|사실', '글의 세부 내용 일치'),
]


def _norm(text):
    return re.sub(r'\s+', '', re.sub(r'</?u>', '', text or ''))


def _apply(rules, text):
    t = _norm(text)
    for pat, name in rules:
        if re.search(pat.replace(r'\s?', '').replace(' ', ''), t):
            return name
    return None


LONG = {'제목 추론': '장문: 제목 추론', '글의 순서 배열': '장문: 글의 순서', '글의 세부 내용 일치': '장문: 세부 내용 파악',
        '어휘의 적절성': '장문: 어휘 추론', '안내문 내용 일치': '장문: 세부 내용 파악'}


def canon_label(label, no):
    if not label:
        return None
    std = _apply(LISTEN if no <= 17 else READ, label)
    if no == 17 and std in ('언급 유무 파악', '담화 내용 일치'):
        return '담화 내용 일치'                      # 17번은 긴 담화의 세부 내용(언급 장소) 문항
    if no >= 41:
        return LONG.get(std, std)
    return std


def classify_stem(stem, no, body=''):
    s = re.sub(r'</?u>', '', stem or '')
    if no <= 17:
        # 듣기 발문
        if no == 17 or (no == 16 and '물음' in s):
            return '담화 내용 일치'
        if '그림' in s:
            return '그림 내용 일치'
        if '지불' in s or '금액' in s or '숫자' in s:
            return '숫자 정보 파악'
        if '할 일' in s:
            return '할 일 파악'
        if '이유' in s:
            return '이유 파악'
        if '언급' in s and ('않' in s or '아닌' in s):
            return '언급 유무 파악'
        if '표를' in s or '도표' in s:
            return '도표(표) 정보 파악'
        if '관계' in s:
            return '관계 파악'
        if '의견' in s:
            return '의견 파악'
        if '목적' in s:
            return '목적 파악'
        if '요지' in s or '주제' in s:
            return '요지·주제 파악'
        if '할 말' in s or '상황 설명' in s:
            return '상황에 적절한 말'
        if '응답' in s:
            return '적절한 응답 고르기'
        if '일치' in s:
            return '담화 내용 일치'
        if no >= 16 and '물음' in s:
            return '담화 내용 일치'
        return None
    # 읽기 발문
    if no >= 41 and '순서' in s:
        return '장문: 글의 순서'
    if '요약' in s:
        return '요약문 완성'
    if '빈칸' in s:
        return '빈칸 추론'
    if '어법' in s:
        return '어법 판단'
    if '낱말의 쓰임' in s or '문맥상' in s and '쓰임' in s:
        return '장문: 어휘 추론' if no >= 41 else '어휘의 적절성'
    if '관계 없는' in s or '관계없는' in s:
        return '무관한 문장 찾기'
    if '주어진 문장' in s and ('들어가기' in s or '곳' in s):
        return '주어진 문장 넣기'
    if '순서' in s and '이어질' in s:
        return '글의 순서 배열'
    if '순서' in s and no >= 41:
        return '장문: 글의 순서'
    if '가리키는' in s or '지칭' in s:
        return '장문: 지칭 추론'
    if '함축' in s or '의미하는 바' in s:
        return '함축 의미 추론'
    if '심경' in s or '분위기' in s:
        return '심경·분위기 파악'
    if '주장' in s:
        return '필자의 주장'
    if '목적' in s:
        return '글의 목적 파악'
    if '제목' in s:
        return '장문: 제목 추론' if no >= 41 else '제목 추론'
    if '주제' in s:
        return '주제 추론'
    if '요지' in s:
        return '요지 파악'
    if '도표' in s or '그래프' in s or '표의' in s:
        return '도표 내용 일치'
    if '안내문' in s or '공고' in s:
        return '안내문 내용 일치'
    if '일치' in s or '내용' in s:
        return '장문: 세부 내용 파악' if no >= 41 else '글의 세부 내용 일치'
    return None


def canon_intent(intent, no):
    """교육청 해설의 출제의도 문장('빈칸에 적절한 표현을 추론한다.')을 표준 유형으로"""
    return canon_label(intent, no) if intent else None


# 발문과 출제 의도가 모두 없을 때만 쓰는 번호 규칙(수능 영어 번호 배치는 거의 고정)
BY_NUMBER = {31: '빈칸 추론', 32: '빈칸 추론', 33: '빈칸 추론', 34: '빈칸 추론', 36: '글의 순서 배열', 37: '글의 순서 배열',
             38: '주어진 문장 넣기', 39: '주어진 문장 넣기', 40: '요약문 완성'}


def stem_template(stem):
    """발문에서 고유명사·숫자를 가린 틀. 같은 틀이면 같은 형식의 물음이다."""
    s = re.sub(r'</?u>', '', stem or '')
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\[\s*3점\s*\]', '', s)
    s = re.sub(r"[A-Za-z][A-Za-z0-9’'.\-&, ]*[A-Za-z0-9]", '<X>', s)
    s = re.sub(r'(<X>\s*)+', '<X>', s)
    s = re.sub(r'\d+', 'N', s)
    return s.strip()
