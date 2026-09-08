# 최종 코드·집계 독립 감사

2026-09-06 01:43 KST. 감사 대상: `join_reviews.py`, `audit_generation.py`, `prepare_extension.py`, `prepare_coverage.py`와 해당 저장 결과.

## 판정: 미해결 집계 오류 없음

Join의 저장 함수를 메모리 캡처로 대체한 비파괴 재실행에서 `joined-reviews/{face,requirements,signal-transfer,validation}.json` 네 파일이 저장본과 정확히 일치했다. 생성 감사도 파일 쓰기만 캡처하여 재실행했으며 `generation-audit.json`과 일치했다. 최신 validation의 출처 해시 45개가 모두 현재 파일과 일치했다. 감사자가 직접 실행한 agreement 16개·extension 16개 테스트도 모두 통과했다. 자료 생성 스크립트는 읽기·AST 구문 검사·산출물 대조만 했고 재실행하지 않았다.

## 분모·결측 독립 대조

| 범위 | 검증 결과 |
| --- | --- |
| AI 한 명당 얼굴 관찰 | 기존 97 = 83 고유 + 6 대조 + 8 반복; 추가 33 = 25 + 4 + 4; 보충 3 = 3 + 0 + 0 |
| 전체 얼굴 | 133 관찰 = 111 고유 + 10 대조 관찰 + 12 반복. 대조에 쓰인 서로 다른 원본은 6개 |
| 경로 | 20개 경로, 198 관측 단계 = 19 완결 × 10 + P05 부분 경로 8 |
| 최종 요구사항 | 19 완결 경로의 16 고유 최종 출력. Public ID·후보/참조 복사쌍 16개의 원본 SHA와 경로 연결 일치 |
| 기존 임계값 비교 | 기존 83 고유 후보 및 순차 70단계 / P01 제외 60단계 분모 유지. 기존 confusion 12개·확장 confusion 18개 별도 재계산 일치 |
| P05-once-triggered | 9단계 실패·10단계 미실행. 최종 severity, final 지표, 10단계 평균, 완결 비용은 null. 관측 8단계·성공 9호출·시도 10호출; 계획 비용만 11 |

참조·출력 SHA 쌍으로 고유 후보를 다시 구성했다. Controls/repeats는 본평가에서 제외되며 양 AI 원문 객체가 수정 없이 연결된다. 198은 공유 출력을 포함한 경로 관측치이지 독립 이미지 수가 아니다. 지표 캐시 113개에는 얼굴 평가 111개 외에 진단용 raw 2개가 있다. 생성은 성공 25 + 실패 1 = 26시도로, 계획 27개 완결과 구별된다. End-only 전달 곡선은 순차 1–9 + 재생성 10이며 비용 11, 동일 최종 출력의 direct one-shot은 비용 1이다.

## 수치와 해석 경계

- 111 고유 얼굴의 ordinal 일치 99/111 = 89.1892%, 선형 가중 κ 0.897412, 제곱 가중 κ 0.945428; binary severity ≥ 2 일치 107/111 = 96.3964%. 양 AI null 0.
- 기존 반복 ordinal 일치 A 7/8·B 8/8, 추가 반복 양쪽 4/4; binary 반복 전부 일치. 원본-원본 대조 관찰 10개는 양쪽 모두 severity 0이나 서로 다른 원본은 6개다.
- 요구사항 16 × 8 = 128개 조건 점수는 양쪽 128/128 일치하며, 모든 조건 score 2는 7/16이다. 이 일치 분모는 별도 overall-artificiality 항목을 포함하지 않는다.
- 원본 기반 **편집된 최종 출력 6개**는 원본-원본 대조와 다른 집합이다. 양 AI 모두 severity < 2인데 frozen MAE/SSIM/LPIPS가 모두 경보를 내므로 각 AI·각 지표에서 TP=0, FP=6, TN=0, FN=0, recall=null이다. 이는 해당 사후 하위집합의 조건부 FP 6/6이지 사람 기준 또는 일반적 오탐률 100%가 아니다. Severity 1도 여기서는 binary 음성이다.
- AI 합의는 사람 정답이 아니며 동일 기반 모델의 독립 세션이다. 원본 6명·기존 순차 7경로·공유 출력·단계 간 의존성이 있다. 새 탐지기 학습, p값, 결측 추정, aligned 임계값 적용을 하지 않았다. 낮아진 고정/정합 점수를 피부 열화 정확도로 해석하지 않는다.

## 감사 중 보완 및 최종 확인

현재 수치 오류 없이 발견된 방어검사 공백은 담당 에이전트가 해결했다: 요구사항 public ID/복사 PNG 원본 해시 재검증, validation에 public items·참조 PNG·현행 progress·import 분석 코드 해시 추가, 실패 attempt=1/retried=false/status=failed/출력 부재 assert 추가. 수정 후 위 재실행과 테스트를 다시 통과했다. 원문 신원 추론 제외 문구 정리 후 기존 agreement manifest 재생성도 검증했다.

Null 쌍 제외, 0분모 precision/recall, 0 expected-disagreement κ, 0 rank-variance Spearman 및 잘못된 severity 유형 거절을 확인했다. 결과 JSON에 NaN이 없었다. 감사의 유일한 작성 파일은 이 문서이며 원본·평가·코드·기존 결과를 수정하지 않았다. 재시도 없음은 보존된 호출 기록에 대한 판정이지 공급자 내부 동작이나 seed 재현성 보장은 아니다.

최종 감사 코드 SHA-256:
- `join_reviews.py`: `f0b54d7472a06a6f37bf5dc4e30ec746ecfa8cf21e7e1302bbae2efebee4c3fd`
- `audit_generation.py`: `e7cb02e91a09a34d1e89a275ffbe0cbbfba1e96c9b3025e9183d033ecf509418`

나머지 원본·결과 추적은 최신 `joined-reviews/validation.json`의 45개 출처 해시와 각 분석 manifest를 따른다.
