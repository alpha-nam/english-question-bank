# 유형 적합도 분석기: AI 판정 지시문 (v1)

작업 폴더: C:\Users\user\Desktop\claude\평가원 연계내역분석\문제은행. Python은 `python -X utf8 -I`. `mcp__hearthbot__` 도구는 쓰지 않는다.
**규격/적합도/비공개/ 폴더와 DB/ 폴더, 규격/적합도/결과/ 의 다른 파일은 절대 열지 않는다.** (지문의 출처를 모르는 상태에서 판단하는 것이 이 작업의 핵심이다.)

입력: 규격/적합도/입력/지문.jsonl — 한 줄에 {"pid":"P001","sentences":["문장1", ...]}. 문장 번호는 1부터 센다.
담당 범위와 출력 파일은 지시받은 대로 따른다. 지문마다 아래 JSON 한 줄을 출력 파일(jsonl)에 쓴다. 지문 하나하나를 직접 읽고 판단한다(스크립트로 자동 판단하지 않는다. 스크립트는 파일 읽기·쓰기·형식 검사에만 쓴다).

```
{"pid": "P001",
 "content": "논설|설명|연구·실험|이야기|실용문|자료 설명|편지·광고",
 "structure_main": "통념→반박|문제→해결|대조|원인→결과|일반→예시|열거|시간 순서|주장→근거|귀납|서사|정보 나열",
 "structure_sub": "위 목록 중 하나 또는 없음",
 "main_idea": {"exists": true/false, "statement_ko": "글 전체를 한 문장으로(한국어)", "sentence_nos": [핵심 문장 번호]},
 "myth": {"exists": true/false, "sentence_nos": [글이 반박하는 통념·기존 견해가 나온 문장]},
 "restatements": [{"idea": "같은 핵심 생각", "sentence_nos": [그 생각을 다른 말로 다시 말한 문장들]}],
 "blank_candidate": {"sentence_no": n, "phrase": "빈칸으로 뚫을 핵심 표현(원문 그대로)", "inferable_from": [이 표현을 추론할 근거 문장 번호]} 또는 null,
 "order_split": {"possible": true/false, "given_last": n(주어진 글로 떼어 낼 마지막 문장 번호, 1~3),
                 "chunks": [[문장 번호들], [..], [..]], "cues": ["둘째 덩어리 첫머리 단서", "셋째", "넷째 경계 단서"], "unique": true/false(정답 순서가 하나로 정해지는가)},
 "insert_candidates": [{"sentence_no": n, "back_cue": "이 문장이 앞을 받는 표현", "forward_cue": "뒤 문장이 이 문장을 받는 표현", "gap_without": true/false(빼면 앞뒤가 끊기는가)}],
 "summary_pair": {"possible": true/false, "A_concept": "", "B_concept": "", "relation": "대조|인과|조건|기타", "basic_words": ["A를 바꿀 기본 어휘", "B를 바꿀 기본 어휘"]},
 "irrelevant_room": {"possible": true/false, "why": "한 화제로 이어지는 설명이라 같은 소재 다른 논점 문장을 끼울 여지가 있는가"},
 "grammar_candidates": {"관계사·명사절": n, "동사 자리·준동사": n, "수일치": n, "능동·수동": n, "병렬·대동사·대명사": n},
 "polar_words": [{"sentence_no": n, "word": "의미 방향(긍정/부정, 증가/감소)이 있고 반의어로 바꾸면 틀리게 되는 낱말", "evidence_sentence_nos": [그 쓰임의 근거 문장]}],
 "direct_top3": [{"type": "빈칸 추론|글의 순서 배열|주어진 문장 넣기|요지 파악|주제 추론|제목 추론|요약문 완성|무관한 문장 찾기|어법 판단|어휘의 적절성", "why": "한 줄"}],
 "note": "판단이 애매했던 점"}
```

구성 정의(판정 순서대로 먼저 맞는 것): 1 통념→반박(흔한 견해를 소개하고 뒤집음, 반박 대상이 명시) 2 문제→해결 3 대조(두 대상을 견주는 것이 중심, 한쪽이 한 문장뿐이면 아님) 4 원인→결과(원인·결과 설명이 중심, 당위 주장이 중심 문장이면 주장→근거) 5 일반→예시(사례 하나가 문장의 절반 이상) 6 주장→근거(필자의 주장·평가와 여러 이유) 7 열거(같은 층위 항목 3개 이상) 8 귀납(사실·연구를 쌓고 끝에 결론) 9 시간 순서·서사·정보 나열.

주의:
- restatements는 2회 이상 다시 말한 생각만 적는다. 없으면 [].
- insert_candidates는 gap_without이 true인 문장 위주로 최대 4개.
- polar_words는 근거가 글 안에 있는 낱말만, 최대 8개.
- direct_top3는 위의 판단과 별개로 "이 글로 문항을 만든다면 가장 잘 맞을 유형 3개"를 순서대로.
- 끝나면 출력 줄 수가 담당 지문 수와 같은지, JSON 형식과 값 목록이 맞는지 스크립트로 확인하고 마지막 응답은 3줄 요약.
