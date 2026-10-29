"""공개 저장소용 예시 자료를 만든다(2026-10-29).
실제 시험지·EBS 교재 글은 저작권 때문에 공개하지 않으므로, 화면이 어떻게 움직이는지 보여 줄 '가짜 지문'만 넣는다.
여기 있는 영어 글과 선택지, 오답률 숫자는 모두 Claude가 새로 지어낸 예시이며 실제 시험·교재·EBSi 자료가 아니다.
쓰기: python -X utf8 예시자료/만들기.py  →  예시자료/_data.json, _book_sample.json
그다음: python -X utf8 build.py --예시  →  예시_화면시안.html"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
EX, NAME = '2099.09', '9월 예시 가짜지문'

ITEMS = [
    (18, '글의 목적 파악', '다음 글의 목적으로 가장 적절한 것은?', 2, '②', None,
     "Dear Ms. Rivera, Our community garden club will hold its first seed exchange next Saturday at the old library hall. "
     "Since you have grown rare tomatoes for years, we would be honored if you could share a few seeds and a short story about how you keep them healthy. "
     "Please let me know by Wednesday whether you can join us. Warm regards, Daniel Ortiz",
     ['정원 가꾸기 강좌를 홍보하려고', '씨앗 나눔 행사 참여를 부탁하려고', '도서관 대관 일정을 변경하려고', '토마토 재배 방법을 문의하려고', '동호회 회비 납부를 안내하려고']),
    (22, '요지 파악', '다음 글의 요지로 가장 적절한 것은?', 2, '④', [9, 46.0, [6.1, 10.2, 21.7, 54.0, 8.0]],
     "When students explain an idea to a classmate, they often discover gaps they did not notice while reading alone. "
     "Speaking forces them to put steps in order and to choose words that someone else can follow. "
     "For this reason, a short pair explanation after reading can do more for understanding than a second silent reading.",
     ['혼자 읽는 시간을 늘려야 한다.', '어휘를 먼저 익혀야 이해가 깊어진다.', '친구의 설명을 들으면 집중력이 떨어진다.', '남에게 설명하는 활동이 이해를 돕는다.', '읽기 속도가 이해의 정도를 결정한다.']),
    (31, '빈칸 추론', '다음 빈칸에 들어갈 말로 가장 적절한 것을 고르시오.', 2, '①', [3, 68.4, [31.6, 24.1, 18.9, 15.0, 10.4]],
     "Maps are useful precisely because they leave things out. A city map that showed every tree, crack, and parked car would be as large and as confusing as the city itself. "
     "What makes a map helpful is its willingness to _____, keeping only what a traveler needs for a particular purpose.",
     ['ignore most details', 'record every change', 'copy the real world', 'follow old traditions', 'add personal stories']),
    (32, '빈칸 추론', '다음 빈칸에 들어갈 말로 가장 적절한 것을 고르시오.', 2, '③', [1, 77.2, [12.5, 20.3, 22.8, 30.1, 14.3]],
     "A runner who checks a watch every few seconds may actually run slower. Constant measuring pulls attention away from breathing and stride, the very things that create speed. "
     "In many skills, performance improves when we _____ for a while and let practiced movements work on their own.",
     ['set higher goals', 'compare with others', 'stop monitoring ourselves', 'change our equipment', 'increase the distance']),
    (36, '글의 순서 배열', '주어진 글 다음에 이어질 글의 순서로 가장 적절한 것은?', 2, '②', [5, 58.9, [9.8, 41.1, 20.6, 17.2, 11.3]],
     "Bread dough that sits overnight in a cool room tastes different from dough baked right away. "
     "(A) As the yeast works slowly, it produces small amounts of acids and other flavors. "
     "(B) The cold slows the yeast, giving it more time to break down starches. "
     "(C) These compounds build up hour by hour, which is why patient bakers often get richer bread.",
     ['(A)-(C)-(B)', '(B)-(A)-(C)', '(B)-(C)-(A)', '(C)-(A)-(B)', '(C)-(B)-(A)']),
    (38, '주어진 문장 넣기', '글의 흐름으로 보아, 주어진 문장이 들어가기에 가장 적절한 곳을 고르시오.', 3, '④', [2, 72.5, [8.4, 14.9, 21.1, 27.5, 28.1]],
     "Some birds hide thousands of seeds each autumn. ( ① ) Remarkably, they find most of them months later under snow. ( ② ) Scientists once thought the birds simply searched everywhere. "
     "( ③ ) Careful tests showed otherwise. ( ④ ) The birds remember landmarks such as rocks and trees around each hiding place. ( ⑤ ) When researchers moved the landmarks, the birds dug in the wrong spots.",
     ['①', '②', '③', '④', '⑤']),
]
BOOKS = [
    ('T901', 'Exercises 01 (예시-0001)', '07 제목 추론', '42', '제목',
     "Libraries today lend more than books. Some offer sewing machines, telescopes, and even fishing rods, so that people can try a hobby before buying anything."),
    ('T902', 'Exercises 02 (예시-0002)', '13 빈칸 추론', '78', '빈칸',
     "A good question can be more valuable than a quick answer, because it keeps a conversation open and invites others to think along with us."),
    ('T903', 'Exercises 01 (예시-0003)', '16 글의 순서', '96', '글의 순서',
     "Before a storm, ants often move their eggs to higher ground, a habit that protects the colony from sudden floods."),
]
TOPICS = {18: '씨앗 나눔 행사 참여 부탁', 22: '설명하기가 이해를 돕는 이유', 31: '지도가 쓸모 있는 까닭: 생략', 32: '지나친 측정이 수행을 방해함',
          36: '천천히 발효한 빵의 풍미', 38: '새들이 숨긴 씨앗을 찾는 방법'}

data = []
for no, ty, stem, pts, ans, top, body, ch in ITEMS:
    data.append({'id': f'{EX}-{no:02d}', 'exam': NAME, 'org': '평가원', 'yr': 2100, 'no': no, 'type': ty, 'pts': pts, 'ans': ans,
                 'top': ({'rank': top[0], 'wr': top[1], 'sel': top[2]} if top else None), 'stem': stem, 'body': body, 'ch': ch, 'img': '',
                 'topic': TOPICS[no], 'fake': True})
book = [{'id': i, 'code': c, 'lec': l, 'page': p, 'type': t, 'text': x, 'topic': '예시 소재(가짜)', 'fake': True} for i, c, l, p, t, x in BOOKS]
json.dump(data, open(os.path.join(HERE, '_data.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(book, open(os.path.join(HERE, '_book_sample.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('예시 문항', len(data), '교재 예시', len(book))
