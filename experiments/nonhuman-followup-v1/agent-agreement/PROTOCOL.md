# 동결된 지표와 두 AI 시각 관찰의 일치 분석

작성일 2026-09-06. 완료된 face-a/face-b 원문과 해독표의 구조·수량을 확인한 뒤, 지표와의 결합·집계 전에 작성했다. 원래 실험의 독립 사전등록이 아닌 제한된 사후 분석이다. 이 분석의 모든 쓰기는 agent-agreement/에 한정한다. 평가 원문을 수정하거나 불일치를 재채점하지 않는다.

## 대상과 대조군

`private/face-key.json`, `reviews/face-a.json`, `reviews/face-b.json`의 97개 ID를 정확히 대조한다. 구성은 현행 최종 고유 출력 83개, 원본-원본 음성 대조 6개, 숨긴 반복 8개다. 고유 출력은 reference SHA256 + output SHA256으로 결합하고 revised-tail-v1 inputs/progress/curves 및 metrics/results.json과 일치해야 한다. 개입 전 raw 전용 출력 2개는 AI 패킷에 없으므로 AI 지표 분석에 넣지 않는다. 숨긴 반복은 duplicate_of_source로 원래 항목에 대응시킨다. 원본 대조는 동일인 식별 검사가 아닌 같은 이미지 쌍의 인위성 오탐 대조다.

## 평가자 일치

severity 0/1/2/3는 없음/약함/뚜렷함/심함, null은 판단 어려움이다. 각 AI의 숨긴 반복에 대한 ordinal exact agreement 및 severity>=2 binary agreement, 원본 대조의 severity>0와 severity>=2 false-positive 수를 보고한다. 두 AI의 고유 출력 83개만으로 4×4 ordinal 교차표, exact agreement, 선형 가중 Cohen kappa(주 분석), quadratic weighted kappa(보조), binary severity>=2 교차표와 일치율을 계산한다. 합의 정답이나 majority label을 만들지 않는다. null은 pairwise complete-case로 제외하며 원래 개수·유효 분모·제외 개수를 모두 기록한다. confidence를 가중치나 제외 기준으로 사용하지 않는다.

## 기존 임계값과의 비교

현행 순차 7경로×10단계=70기록을 대상으로 고정 ROI의 MAE>=0.0288375, SSIM<=0.842874, LPIPS>=0.0555075 세 규칙을 각각 그대로 적용한다. 규칙을 조합하거나 새 감지기를 훈련하지 않는다. 각 AI binary severity>=2를 비교 기준으로 TP/FP/TN/FN, precision, recall, specificity, binary agreement를 기술한다. 이는 AI 관찰과의 일치이며 사람 정답 기준 감지 정확도가 아니다. P01 calibration 10단계를 제외한 60기록도 별도로 보고한다. 70기록은 6인물 7종속 경로, 60기록은 5인물 6종속 경로이며 P03 두 회는 같은 인물이다.

원본 대조와 숨긴 반복은 성능·상관 본분모에서 제외한다. 각 AI마다 null stage는 지표 confusion과 correlation에서 제외하고 별도 세며, 83 unique 분석에서는 고유 이미지 한 번만 센다. 각 경로에서 처음 고정 임계값에 도달한 단계와 처음 AI severity>=2가 관찰된 단계를 나란히 보고한다. 차이=첫 alarm 단계−첫 AI clear 단계, 음수는 이번 순서상 먼저 경보가 났다는 뜻이다. 범위 내 미관측은 null로 표시하고 누락 이후 시점이나 날짜별 관측은 추정하지 않는다.

## 연속 지표의 탐색 상관

AI severity와 MAE, 1−SSIM, LPIPS의 Spearman rho를 보고한다. 1−SSIM으로 방향을 맞추어 모두 클수록 원본 차이가 커지게 한다. 고정 ROI와 NCC sigma1/3/6 정합의 rho를 같은 샘플로 비교한다. 83 unique, 순차70, P01 제외60 분모를 모두 명시하고 경로별 값도 보존한다. 동률은 평균 rank, 표본 2개 미만 또는 어느 한 쪽 0분산이면 rho=null과 이유를 저장한다. 정합 지표에 기존 임계값을 적용해 주 감지 성능을 보고하지 않는다. P04 피부 지표와 AI의 새 학습/임계값 최적화는 하지 않는다.

## 재현과 제한

분류 임계값의 등호 방향, 임의 손계산 confusion/weighted kappa, 0분산·null·0분모 처리, 목록 및 source hash, 본분모 제외, 평균 rank의 SciPy 일치, 결과 집계를 별도 테스트한다. source hashes와 환경 및 스크립트·결과·검사 해시를 남긴다. 신뢰구간·p값·bootstrap은 이번에 산출하지 않는다. 같은 경로의 단계·공유 이미지·P03 반복이 독립이 아니며 6개 인물 cluster만으로 강한 추론을 만들지 않는다.

두 평가자는 같은 기반 모델의 독립 세션이다. 방법·단계·지표·이전 평가에 가려진 관찰이지만 사람 평가가 아니고 모델 공통 편향을 공유할 수 있다. 동일 기반 모델/동일 자료의 높은 합의가 외적 타당성이나 사람 기준 성능을 보장하지 않는다. 점수로 임계값을 재보정하거나 새 정책 실행 효과를 주장하지 않는다. 사람 평가는 아직 수집하지 않았다.
