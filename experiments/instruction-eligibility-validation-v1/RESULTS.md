# 실행 대상 검사 방법의 새 요청 검증

개발에 사용한 32개와 겹치지 않는 새 합성 영어 대화 네 개, 요청 16개를 두 모델에 각각 적용하였다. 실제 모델 호출은 모델별 32회, 전체 64회다. 방법과 자료는 추론 전에 고정했다.

| 방법 | Qwen3-4B | Llama-3.2-3B |
| --- | --- | --- |
| 기준 방법 | 9/16 | 0/16 |
| 기존 유지·삭제 | 9/16 | 0/16 |
| 기존 정규화 | 9/16 | 0/16 |
| 항목별 적용 | 9/16 | 0/16 |
| 기존 정규화+항목별 적용 | 9/16 | 0/16 |
| 복원 표현 개선 | 11/16 | 0/16 |
| JSON 최초 응답 | 9/16 | 8/16 |
| JSON 재검토 우선 | 9/16 | 0/16 |
| 실행 대상 검사 결합 | 16/16 | 0/16 |

## 최종 방법의 상세 점수

| 모델 | 항목별 일치 | 최종 상태 일치 | 추가 오류 수 |
| --- | --- | --- | --- |
| Qwen3-4B | 96/96 | 4/4 | 0 |
| Llama-3.2-3B | 15/96 | 0/4 | 0 |

추가 오류 수는 기준이 맞았지만 최종 방법이 틀린 요청 수다.

## 유형별 결과

| 유형 | Qwen 기준 | Qwen 복원 표현 개선 | Qwen 최종 | Llama 기준 | Llama 복원 표현 개선 | Llama 최종 |
| --- | --- | --- | --- | --- | --- | --- |
| 뒤의 직접 지시 | 6/8 | 8/8 | 8/8 | 0/8 | 0/8 | 0/8 |
| 실행 대상 제외 | 3/8 | 3/8 | 8/8 | 0/8 | 0/8 | 0/8 |

## 최종 방법의 오류 사례

### Qwen3-4B

모든 요청의 전체 상태가 정답과 일치했다.

### Llama-3.2-3B

- E1 요청 1: {"jacket": {"expected": "green", "observed": "original"}, "top": {"expected": "ivory_crewneck", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "necklace": {"expected": "gold_round", "observed": "none"}, "background": {"expected": "office", "observed": "original"}, "prop": {"expected": "lamp", "observed": "original"}}
- E1 요청 2: {"jacket": {"expected": "gray", "observed": "original"}, "top": {"expected": "ivory_crewneck", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "necklace": {"expected": "gold_round", "observed": "none"}, "background": {"expected": "office", "observed": "original"}, "prop": {"expected": "lamp", "observed": "original"}}
- E1 요청 3: {"jacket": {"expected": "gray", "observed": "original"}, "top": {"expected": "ivory_crewneck", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "necklace": {"expected": "gold_round", "observed": "none"}, "prop": {"expected": "lamp", "observed": "original"}}
- E1 요청 4: {"jacket": {"expected": "gray", "observed": "original"}, "top": {"expected": "navy_sweater", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "necklace": {"expected": "gold_round", "observed": "none"}, "prop": {"expected": "lamp", "observed": "original"}}
- E2 요청 1: {"jacket": {"expected": "beige", "observed": "original"}, "top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "gold_square_right", "observed": "none"}, "necklace": {"expected": "silver_teardrop", "observed": "none"}, "background": {"expected": "library", "observed": "original"}, "prop": {"expected": "plant", "observed": "original"}}
- E2 요청 2: {"jacket": {"expected": "beige", "observed": "original"}, "top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "gold_square_right", "observed": "none"}, "necklace": {"expected": "silver_teardrop", "observed": "none"}, "background": {"expected": "blue_studio", "observed": "original"}, "prop": {"expected": "plant", "observed": "original"}}
- E2 요청 3: {"jacket": {"expected": "beige", "observed": "original"}, "top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "gold_square_right", "observed": "none"}, "background": {"expected": "blue_studio", "observed": "original"}, "prop": {"expected": "plant", "observed": "original"}}
- E2 요청 4: {"top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "gold_square_right", "observed": "none"}, "background": {"expected": "blue_studio", "observed": "original"}, "prop": {"expected": "plant", "observed": "original"}}
- E3 요청 1: {"jacket": {"expected": "gray", "observed": "original"}, "top": {"expected": "navy_sweater", "observed": "original"}, "pin": {"expected": "red_triangle_left", "observed": "original"}, "necklace": {"expected": "gold_round", "observed": "none"}, "background": {"expected": "garden", "observed": "original"}, "prop": {"expected": "bench", "observed": "original"}}
- E3 요청 2: {"jacket": {"expected": "gray", "observed": "original"}, "top": {"expected": "navy_sweater", "observed": "original"}, "pin": {"expected": "red_triangle_left", "observed": "original"}, "background": {"expected": "garden", "observed": "original"}, "prop": {"expected": "bench", "observed": "original"}}
- E3 요청 3: {"jacket": {"expected": "gray", "observed": "original"}, "pin": {"expected": "red_triangle_left", "observed": "original"}, "background": {"expected": "garden", "observed": "original"}, "prop": {"expected": "bench", "observed": "original"}}
- E3 요청 4: {"jacket": {"expected": "gray", "observed": "original"}, "background": {"expected": "garden", "observed": "original"}, "prop": {"expected": "bench", "observed": "original"}}
- E4 요청 1: {"jacket": {"expected": "navy", "observed": "original"}, "top": {"expected": "gray_sweater", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "necklace": {"expected": "silver_teardrop", "observed": "none"}, "background": {"expected": "brick_studio", "observed": "original"}, "prop": {"expected": "plant", "observed": "original"}}
- E4 요청 2: {"jacket": {"expected": "navy", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "necklace": {"expected": "silver_teardrop", "observed": "none"}, "background": {"expected": "brick_studio", "observed": "original"}, "prop": {"expected": "plant", "observed": "original"}}
- E4 요청 3: {"jacket": {"expected": "navy", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "necklace": {"expected": "silver_teardrop", "observed": "none"}, "background": {"expected": "brick_studio", "observed": "original"}, "prop": {"expected": "plant", "observed": "original"}}
- E4 요청 4: {"jacket": {"expected": "navy", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "background": {"expected": "brick_studio", "observed": "original"}, "prop": {"expected": "plant", "observed": "original"}}
