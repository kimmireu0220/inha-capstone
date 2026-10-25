# 지시 구절 정규화와 항목별 적용의 새 대화 검증

코드와 정답을 고정한 뒤 새 대화 네 개·요청 16개를 추론하였다. 실제 모델 응답 32개를 모든 방법이 공유한다. 각 방법의 이전 상태를 누적한다.

| 방법 | 전체 상태 일치율 | 항목별 일치율 | 최종 상태 일치율 | 새 오류 |
| --- | --- | --- | --- | --- |
| 기준 방법 | 9/16 | 86/96 | 2/4 | 0 |
| 기존 유지·삭제 | 10/16 | 87/96 | 3/4 | 0 |
| 구절 정규화 | 16/16 | 96/96 | 4/4 | 0 |
| 항목별 적용 | 10/16 | 87/96 | 3/4 | 0 |
| 정규화+항목별 적용 | 16/16 | 96/96 | 4/4 | 0 |

새 오류는 기준 방법이 맞았으나 해당 방법 적용 후 틀린 요청 수다.

## 대화별 전체 상태 일치

| 방법 | V1 | V2 | V3 | V4 |
| --- | --- | --- | --- | --- |
| 기준 방법 | 2/4 | 1/4 | 4/4 | 2/4 |
| 기존 유지·삭제 | 2/4 | 2/4 | 4/4 | 2/4 |
| 구절 정규화 | 4/4 | 4/4 | 4/4 | 4/4 |
| 항목별 적용 | 2/4 | 2/4 | 4/4 | 2/4 |
| 정규화+항목별 적용 | 4/4 | 4/4 | 4/4 | 4/4 |

## 개발 자료 재계산

아래 자료는 이미 관찰한 자료이며 추가 모델 호출 없이 재계산하였다. 새 대화 검증과 따로 집계한다.

| 자료 | 기준 방법 | 기존 유지·삭제 | 구절 정규화 | 항목별 적용 | 정규화+항목별 적용 |
| --- | --- | --- | --- | --- | --- |
| paraphrase-contract-v1 | 25/32 | 25/32 | 29/32 | 27/32 | 32/32 |
| request-contract-v3 | 27/32 | 29/32 | 29/32 | 32/32 | 32/32 |
| isolated-contract-v1 | 28/32 | 29/32 | 30/32 | 29/32 | 30/32 |

## 기준과 결합 방법의 차이

### V1 요청 3

Bring back the original shirt and necklace, preserving the gray blazer and garden setting.

기준 전체 상태 일치: False, 결합 전체 상태 일치: True.

정규화 기록: [{"original": "Bring back the original shirt and necklace", "normalized": "Restore the original shirt and necklace"}, {"original": "preserving the gray blazer and garden setting", "normalized": "Keep the gray blazer and garden background unchanged"}]

### V1 요청 4

Remove the plant. Retain the gray blazer and garden background.

기준 전체 상태 일치: False, 결합 전체 상태 일치: True.

정규화 기록: [{"original": "Retain the gray blazer and garden background", "normalized": "Keep the gray blazer and garden background unchanged"}]

### V2 요청 2

Return the sweater and necklace to the original photo, leaving the green blazer and office background as they are.

기준 전체 상태 일치: False, 결합 전체 상태 일치: True.

정규화 기록: [{"original": "leaving the green blazer and office background as they are", "normalized": "Keep the green blazer and office background unchanged"}]

### V2 요청 3

Do not change the green blazer or bench. Replace the office with a pale-blue studio and add a gold round pendant necklace.

기준 전체 상태 일치: False, 결합 전체 상태 일치: True.

정규화 기록: [{"original": "Do not change the green blazer or bench", "normalized": "Keep the green blazer and bench unchanged"}]

### V2 요청 4

Remove the necklace. Bring back the original blazer, preserving the pale-blue studio and bench.

기준 전체 상태 일치: False, 결합 전체 상태 일치: True.

정규화 기록: [{"original": "Bring back the original blazer", "normalized": "Restore the original blazer"}, {"original": "preserving the pale-blue studio and bench", "normalized": "Keep the pale-blue studio and bench unchanged"}]

### V4 요청 2

Do not change the plant or pin. Replace the navy blazer with a gray blazer and the ivory shirt with a gray sweater.

기준 전체 상태 일치: False, 결합 전체 상태 일치: True.

정규화 기록: [{"original": "Do not change the plant or pin", "normalized": "Keep the plant and pin unchanged"}]

### V4 요청 3

Restore the original blazer and shirt, preserving the red-brick studio and plant.

기준 전체 상태 일치: False, 결합 전체 상태 일치: True.

정규화 기록: [{"original": "preserving the red-brick studio and plant", "normalized": "Keep the red-brick studio and plant unchanged"}]

## 측정 범위

개발자가 작성한 영어 요청, 여섯 상태 항목, 한 종류의 추출 모델을 사용했다. 표본 단위는 대화 네 개이며 같은 대화의 요청을 독립 표본처럼 통계 검정하지 않았다. 검사 대상은 상태 기록이며, 새 이미지 생성과 인간 평가는 수행하지 않았다.
