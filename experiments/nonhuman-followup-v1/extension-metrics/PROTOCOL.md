# 추가 생성의 고정·정합 지표 및 정책 경로 비교

2026-09-06 작성. 신규 생성이 저장되는 동안 계산 규칙을 고정한다. 최초 계획은 신규27개이며, 수집 종료를 root가 알리고 generation/progress.json의 종료 상태가 확인되기 전에는 부분 cache만 기록한다. 사람·AI 평가 원문 및 라벨은 이번 분석에서 읽지 않는다. 모든 쓰기는 extension-metrics/ 내부다.

수집 종료 규칙 변경: P05 once-triggered stage9가 moderation_blocked로 실패하여 재시도하지 않았고, stage10은 입력 부재로 미실행이다. 실제 신규25성공+1실패=26시도, 남은1단계 미실행으로 확정한다. collection_complete=true/full_design_complete=false를 최종 조건으로 쓴다. P05 once는8개 deliverable, 성공호출9/총시도10, 계획호출11이다. stage10 최종값과10단계평균은 null, 관측8단계평균은 별도 보조값이다. 20경로 중19개10단계완결, 총198개 관측 deliverable이다. 실패 원문의 해시와 상태를 보존하고 실패 이유를 추가 추정하지 않는다.

## 출력과 재현

신규 목록은 generation/generated/*.call.json만으로 구성하고 attempt=1, 입력/출력 SHA256, 요청 key=SHA256(input_sha256+newline+prompt), 기록과 PNG 대응, 현재 10단계 state/prompt를 검사한다. 계획27개 중 성공25개는 P04 once-triggered stage7–10 4개, P05 once-triggered stage3–8 6개, P06 once-triggered stage3–10 8개, end-only의 서로 다른 원본5개(P03 두 경로 공유), P04 always-original stage1–2 2개다. generation/failures의 P05 stage9 실패1개는 이미지 지표에 넣지 않는다. 생성 실패·재시도를 숨기거나 최선 결과를 고르지 않는다.

metrics/analyze.py를 순수 모듈로 import하여 image/measure 함수를 그대로 호출한다. 고정 RGB float32 MAE, win7 SSIM, LPIPS AlexNet v0.1 CPU와 NCC 정수 이동±64, Gaussian sigma1/3/6, 기존 얼굴 ROI, P04 기존 피부3ROI/가중치는 동일하다. sigma3는 주 정합 분석이다. 정합 점수에 원래 고정 ROI 임계값을 적용하지 않는다. 네트워크 state_dict SHA256이 기존 manifest와 같아야 한다.

기존 metrics/results.json의 reference+output 해시별 85개 결과와 신규 계산을 결합한다. 최종 generation/progress가 재사용하는 출력 중 기존 cache에 없는 자료는 추가로 계산한다(예: P05/P06의 초기 rebase, P04 once stage6 raw). 그 목록은 progress의 실제 출력만을 근거로 정하며 신규 생성27개 수에 합치지 않는다. 필요 raw 후보의 호출 기록은 실제 개입 횟수와 입력 흐름을 검증할 용도이며, 과거 pocket 단계나 폐기 평가를 분석에 넣지 않는다.

## 경로와 비용

현행 revised-tail-v1 inputs/progress/curves의 9경로를 보존하고, 종료된 generation/progress의 once3경로·end7경로·P04 always-original1경로를 더해 20경로의 deliverable 곡선을 만든다. P05 once의 실패9단계와미실행10단계는 채우지 않아198개 관측 단계다. end-only deliverable은 순차1–9단계와 재생성된10단계다. 원래 순차10단계의 호출도 workflow에서는 실제 소비되므로 비용11회이고, 그 출력은 end-only의 최종 deliverable 평균에는 넣지 않는다. 원본에 최종 요구를 직접 적용하는 direct-one-shot은 같은 최종 출력 한 장/비용1회이며 중간 단계 평균을 만들지 않는다.

논리 비용: sequential10, once-triggered11, fixed3 13, P04 every-triggered18, always-original10, end-only workflow11, direct-one-shot1. 같은 입력바이트+프롬프트의 공유 출력은 물리 호출 수로 중복 계산하지 않는다. P03 두 end 경로가 같은 최종 출력인 점과 P04 end/always-original/every-triggered 최종 공유를 명시한다. 비용은 운영상 요구되는 논리 호출 수이며 현재 추가 실험에서 발생한 새 호출27개와 구분한다.

실제 호출 검증은 각 deliverable의 sidecar .call.json과 reset 전 raw 호출을 연결하여 입력·state·prompt·단계 및 요청 키를 검사한다. 기존 P04 1–8단계 reset의 raw는 동결된 prefix_rebases가 명시한 단계의 기존 decision 기록에서만 확인하고, 9–10단계는 현행 revised progress의 raw를 사용한다. once 최초 reset의 raw는 해당 현행 순차 단계다. end workflow의 마지막 순차 raw 호출도 별도로 기록한다. 항상 원본 정책은 매 단계 원본에서 1회 생성하므로 raw+rebase의 2회 호출로 세지 않는다.

## 비교와 한계

각 경로의 고정/정합 얼굴 MAE·SSIM·LPIPS 평균/최종/최대와 P04 피부 합계·각 ROI 평균/최종을 보존한다. 신규27개의 정합 이동·NCC·경계·sigma 민감도를 전부 보존한다. 최초 reset 뒤 이어진 raw 편집에서 고정 LPIPS≥0.0555075가 처음 재등장한 단계, reset 후 편집 횟수, reset 직후 점수를 기록한다. 이후 단계가 없거나 항상 원본처럼 reset 이미지를 다시 편집하지 않으면 해당 없음으로 남긴다. 재경보는 피부 열화의 사람 정답 시점이 아니다.

새 데이터·기존 cache·전달 파일의 해시와 버전을 기록하고 실행 전후 불변을 검사한다. 27개 완결성, 20경로 구성, end 평균의1–9+10 정의, 논리 호출 ledger, 공유 출력 의존성, 고정 지표 재현, 0분모/미관측 재경보 처리 등을 테스트한다. 수치상 더 낮은 원본 차이를 요구 충족·피부 자연스러움·지각 우월성으로 해석하지 않는다. 6인물, P03 두 반복과 정책별 공유 출력·종속단계라는 한계를 유지한다. 최종 요구만 아는 direct-one-shot은 실제 순차 수정 workflow의 대체 비용1회라고 주장하지 않는다.
