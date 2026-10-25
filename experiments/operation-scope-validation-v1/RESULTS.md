# 두 모델에서의 복원 표현 처리 검증

같은 합성 영어 대화 8개, 요청 32개를 두 모델에 각각 적용했다. 문장 32개는 모두 서로 다르다. 모델별 호출은 64회이며 총 128회다. 앞선 개발 자료와 요청이 겹치지 않는다. 모든 방법은 각 모델이 반환한 같은 응답을 사용했다.

| 방법 | Qwen3-4B | Llama-3.2-3B |
| --- | --- | --- |
| 기준 방법 | 14/32 | 7/32 |
| 기존 유지·삭제 | 14/32 | 7/32 |
| 기존 정규화 | 17/32 | 9/32 |
| 항목별 적용 | 14/32 | 6/32 |
| 기존 정규화+항목별 적용 | 17/32 | 8/32 |
| 개선 정규화 | 28/32 | 17/32 |
| JSON 최초 응답 | 16/32 | 7/32 |
| JSON 재검토 우선 | 17/32 | 4/32 |

## 항목별 일치와 최종 상태

| 모델 | 방법 | 항목별 일치 | 최종 상태 일치 | 추가 오류 수 |
| --- | --- | --- | --- | --- |
| Qwen3-4B | 기준 방법 | 162/192 | 1/8 | 0 |
| Qwen3-4B | 기존 유지·삭제 | 165/192 | 1/8 | 0 |
| Qwen3-4B | 기존 정규화 | 170/192 | 2/8 | 0 |
| Qwen3-4B | 항목별 적용 | 165/192 | 1/8 | 0 |
| Qwen3-4B | 기존 정규화+항목별 적용 | 170/192 | 2/8 | 0 |
| Qwen3-4B | 개선 정규화 | 187/192 | 6/8 | 0 |
| Qwen3-4B | JSON 최초 응답 | 159/192 | 2/8 | 1 |
| Qwen3-4B | JSON 재검토 우선 | 163/192 | 2/8 | 0 |
| Llama-3.2-3B | 기준 방법 | 121/192 | 1/8 | 0 |
| Llama-3.2-3B | 기존 유지·삭제 | 121/192 | 1/8 | 0 |
| Llama-3.2-3B | 기존 정규화 | 125/192 | 1/8 | 1 |
| Llama-3.2-3B | 항목별 적용 | 114/192 | 1/8 | 1 |
| Llama-3.2-3B | 기존 정규화+항목별 적용 | 118/192 | 1/8 | 2 |
| Llama-3.2-3B | 개선 정규화 | 140/192 | 3/8 | 1 |
| Llama-3.2-3B | JSON 최초 응답 | 131/192 | 0/8 | 2 |
| Llama-3.2-3B | JSON 재검토 우선 | 100/192 | 0/8 | 3 |

추가 오류 수는 기준 방법이 맞았지만 해당 방법이 틀린 요청 수다. JSON 최초 응답은 첫 응답만 사용하고, 나머지는 추출·재검토 응답을 사용한다.

## 요청 유형별 전체 상태

| 유형 | Qwen 기준 | Qwen 기존 정규화 | Qwen 개선 | Llama 기준 | Llama 기존 정규화 | Llama 개선 |
| --- | --- | --- | --- | --- | --- | --- |
| 변경과 복원 혼합 | 5/8 | 8/8 | 8/8 | 2/8 | 5/8 | 8/8 |
| 복원 표현 | 2/8 | 2/8 | 8/8 | 2/8 | 1/8 | 4/8 |
| 부정·조건·인용 | 4/8 | 4/8 | 4/8 | 2/8 | 2/8 | 2/8 |
| 앞 지시의 수정 | 3/8 | 3/8 | 8/8 | 1/8 | 1/8 | 3/8 |

## 개선 방법의 오류 사례

### Qwen3-4B

- G1 요청 3: {"necklace": {"expected": "silver_teardrop", "observed": "original"}}
- G1 요청 4: {"pin": {"expected": "blue_circle_left", "observed": "none"}, "necklace": {"expected": "silver_teardrop", "observed": "original"}}
- G2 요청 3: {"prop": {"expected": "lamp", "observed": "none"}}
- G2 요청 4: {"prop": {"expected": "lamp", "observed": "none"}}

### Llama-3.2-3B

- R2 요청 1: {"jacket": {"expected": "gray", "observed": "original"}, "top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "gold_square_right", "observed": "original"}, "necklace": {"expected": "gold_round", "observed": "none"}, "background": {"expected": "brick_studio", "observed": "original"}, "prop": {"expected": "lamp", "observed": "original"}}
- R2 요청 2: {"jacket": {"expected": "gray", "observed": "original"}, "necklace": {"expected": "gold_round", "observed": "none"}, "background": {"expected": "brick_studio", "observed": "original"}, "prop": {"expected": "lamp", "observed": "original"}}
- R2 요청 3: {"jacket": {"expected": "gray", "observed": "original"}, "background": {"expected": "brick_studio", "observed": "original"}, "prop": {"expected": "lamp", "observed": "original"}}
- R2 요청 4: {"jacket": {"expected": "gray", "observed": "original"}, "prop": {"expected": "lamp", "observed": "original"}}
- C1 요청 1: {"jacket": {"expected": "navy", "observed": "original"}, "top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "necklace": {"expected": "silver_teardrop", "observed": "none"}, "background": {"expected": "garden", "observed": "original"}, "prop": {"expected": "bench", "observed": "original"}}
- C1 요청 2: {"jacket": {"expected": "navy", "observed": "original"}, "pin": {"expected": "blue_circle_left", "observed": "original"}, "necklace": {"expected": "silver_teardrop", "observed": "none"}, "background": {"expected": "garden", "observed": "original"}, "prop": {"expected": "bench", "observed": "original"}}
- C1 요청 3: {"jacket": {"expected": "navy", "observed": "original"}, "necklace": {"expected": "silver_teardrop", "observed": "none"}, "background": {"expected": "garden", "observed": "original"}, "prop": {"expected": "bench", "observed": "original"}}
- C1 요청 4: {"jacket": {"expected": "navy", "observed": "original"}, "necklace": {"expected": "silver_teardrop", "observed": "none"}, "background": {"expected": "library", "observed": "original"}, "prop": {"expected": "bench", "observed": "original"}}
- C2 요청 4: {"background": {"expected": "blue_studio", "observed": "library"}}
- G1 요청 3: {"necklace": {"expected": "silver_teardrop", "observed": "original"}}
- G1 요청 4: {"necklace": {"expected": "silver_teardrop", "observed": "original"}}
- G2 요청 1: {"jacket": {"expected": "green", "observed": "original"}, "top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "red_triangle_left", "observed": "original"}}
- G2 요청 2: {"jacket": {"expected": "green", "observed": "original"}, "top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "red_triangle_left", "observed": "original"}}
- G2 요청 3: {"jacket": {"expected": "green", "observed": "original"}, "top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "red_triangle_left", "observed": "original"}, "prop": {"expected": "lamp", "observed": "none"}}
- G2 요청 4: {"jacket": {"expected": "green", "observed": "original"}, "top": {"expected": "white_crewneck", "observed": "original"}, "pin": {"expected": "red_triangle_left", "observed": "original"}, "necklace": {"expected": "gold_round", "observed": "original"}, "prop": {"expected": "lamp", "observed": "none"}}

## 실험 구성

앞선 48개 요청은 개선에 사용한 개발 자료이며 그 재계산은 operation-scope-v2에 기록했다. 본 검증의 코드·요청·정답·모델 배포 버전을 추론 전에 고정했다. 두 모델의 결과는 같은 요청에 대한 대응 비교이며 모델별 분모 32개를 사용한다. 상태를 정답과 자동 대조하였다. 모델 가중치는 저장소에 포함하지 않는다.

Llama 실행 모델: https://huggingface.co/mlx-community/Llama-3.2-3B-Instruct-4bit
원 모델 설명: https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
