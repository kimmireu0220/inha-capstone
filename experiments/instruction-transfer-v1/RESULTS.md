# 표현과 지시 순서를 바꾼 추가 검증

구현을 고정한 상태에서 대화 12개, 요청 48개를 처리했다. 실제 모델 호출은 96회이며 서로 다른 요청 문장은 32개다. 네 가지 편집 목표를 세 표현 유형으로 요청했다. 같은 초기 설정과 후속 요청이 반복된다. 연구자가 구성한 합성 영어 대화다.

| 방법 | 전체 상태 일치 | 항목별 일치 | 최종 상태 일치 | 추가 오류 수 |
| --- | --- | --- | --- | --- |
| 기준 방법 | 24/48 | 246/288 | 4/12 | 0 |
| 기존 유지·삭제 | 27/48 | 252/288 | 5/12 | 0 |
| 구절 정규화 | 36/48 | 264/288 | 8/12 | 0 |
| 항목별 적용 | 27/48 | 255/288 | 5/12 | 0 |
| 정규화+항목별 적용 | 36/48 | 264/288 | 8/12 | 0 |
| JSON 최초 응답 | 15/48 | 228/288 | 1/12 | 9 |
| JSON 재검토 우선 | 15/48 | 228/288 | 1/12 | 9 |

추가 오류 수는 기준 방법이 맞았지만 해당 방법이 틀린 요청 수다. JSON 최초 응답 조건은 저장한 첫 응답만 사용한다. 나머지 방법은 추출·재검토 응답을 사용한다.

## 표현을 바꾼 두 번째와 세 번째 요청

| 표현 유형 | 기준 방법 | 기존 유지·삭제 | 구절 정규화 | JSON 최초 응답 | JSON 재검토 우선 |
| --- | --- | --- | --- | --- | --- |
| 기존 어휘의 새 조합 | 2/8 | 2/8 | 8/8 | 2/8 | 2/8 |
| 규칙에 없는 표현 | 0/8 | 0/8 | 0/8 | 0/8 | 0/8 |
| 앞 지시의 수정 | 6/8 | 8/8 | 8/8 | 0/8 | 0/8 |

## 오류 사례

- A__unseen 요청 2: {"top": {"expected": "original", "observed": "navy_sweater"}, "pin": {"expected": "original", "observed": "red_triangle_left"}}
- A__unseen 요청 3: {"top": {"expected": "original", "observed": "navy_sweater"}, "pin": {"expected": "original", "observed": "red_triangle_left"}}
- A__unseen 요청 4: {"top": {"expected": "original", "observed": "navy_sweater"}, "pin": {"expected": "original", "observed": "red_triangle_left"}}
- B__unseen 요청 2: {"jacket": {"expected": "original", "observed": "navy"}, "necklace": {"expected": "original", "observed": "silver_teardrop"}}
- B__unseen 요청 3: {"jacket": {"expected": "original", "observed": "navy"}, "necklace": {"expected": "original", "observed": "silver_teardrop"}}
- B__unseen 요청 4: {"jacket": {"expected": "original", "observed": "navy"}, "necklace": {"expected": "original", "observed": "silver_teardrop"}}
- C__unseen 요청 2: {"top": {"expected": "original", "observed": "white_crewneck"}, "necklace": {"expected": "original", "observed": "gold_round"}}
- C__unseen 요청 3: {"top": {"expected": "original", "observed": "white_crewneck"}, "necklace": {"expected": "original", "observed": "gold_round"}}
- C__unseen 요청 4: {"top": {"expected": "original", "observed": "white_crewneck"}, "necklace": {"expected": "original", "observed": "gold_round"}}
- D__unseen 요청 2: {"top": {"expected": "original", "observed": "gray_sweater"}, "pin": {"expected": "original", "observed": "blue_circle_left"}}
- D__unseen 요청 3: {"top": {"expected": "original", "observed": "gray_sweater"}, "pin": {"expected": "original", "observed": "blue_circle_left"}}
- D__unseen 요청 4: {"top": {"expected": "original", "observed": "gray_sweater"}, "pin": {"expected": "original", "observed": "blue_circle_left"}}
