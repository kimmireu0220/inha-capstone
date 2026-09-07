# 현행 출력의 위치·ROI 민감도 분석

작성 시점: 2026-09-06. 이 문서는 이번 분석의 출력 지표를 계산하기 전에 작성한다. 과거 진단의 알고리즘과 P04 ROI를 재사용하는 사후 분석이며, 독립적인 사전등록 연구로 부르지 않는다.

## 자료와 범위

현행 이미지 목록은 `experiments/revised-tail-v1/inputs.json`, `progress.json`, `curves.json`만으로 결정한다. 9개 경로(P01, P02, P03-r1/r2, P04, P05, P06 순차 및 P04-fixed3/triggered)의 1–10단계 최종 이미지와 progress에 명시된 9–10단계 개입 전 raw 이미지를 포함한다. inputs의 prefix와 curves의 1–8단계, progress의 final과 curves의 9–10단계를 경로와 해시로 대조한다. 과거 pocket 9–10단계 출력, 과거 audit/progress/results의 이미지 목록, 사람·에이전트 평가·라벨은 읽지 않는다. 1–8단계에서 개입으로 폐기된 raw 이미지는 이 현행 목록에 없으므로 포함하지 않는다. 중복 이미지는 reference SHA256 + output SHA256으로 계산을 공유하고, 정책 평균은 10단계씩 계산한다.

## 지표와 정합

각 인물의 reference와 얼굴 ROI는 inputs에 기록된 값을 그대로 쓴다. 기존 policy-pilot-v1/run.py의 계산을 가져오되, import 시 기록을 쓰는 부작용을 피하기 위해 순수 계산 함수로 옮긴다. RGB float32 /255, MAE, SSIM(win7, RGB, data_range1, gaussian_weights=False, use_sample_covariance=True), LPIPS AlexNet v0.1 CPU eval을 유지한다. 고정 ROI 점수는 curves의 저장값과 1e-6 허용오차로 재현해야 한다. Torch seed0, deterministic algorithms, CPU threads2를 고정한다.

평행이동은 기존 alignment/skin 진단과 같은 정수 NCC 탐색을 사용한다. RGB→회색조→Gaussian sigma1/3/6, reference 얼굴 ROI template, 출력의 같은 ROI 주변 ±64px에서 NCC 최대 위치를 선택한다. sigma3는 주 분석, sigma1/6은 민감도 분석이다. 동률은 NumPy argmax의 행 우선 첫 위치로 결정한다. Gaussian은 위치 추정에만 적용하며 지표는 보간하지 않은 원래 RGB crop에 계산한다. 크기·회전·색·형상 보정 없음. NCC, dx/dy, 경계 도달, sigma 사이 축별 최대 이동 범위를 모두 보존한다. 3px 초과 표시는 기존 보고용 휴리스틱이며 정합 정확도 기준이 아니다.

P04 피부는 과거 PROTOCOL에 원본만 보고 고정했던 세 ROI를 그대로 쓴다: forehead=[452,144,568,178], cheek_viewer_left=[412,264,448,306], cheek_viewer_right=[572,264,604,306]. 새 인물용 피부 ROI는 만들지 않는다. 고정 및 sigma1/3/6의 얼굴 이동량을 동일하게 적용한다. 피부 지표는 RGB MAE, SSIM, gray−Gaussian(gray,sigma2)의 highpass MAE이다. MAE/highpass는 영역 픽셀수, SSIM은 win7 유효 중심 픽셀수로 가중평균한다. 각 영역도 별도 보존한다. 세 ROI는 피부 전체 분할이 아니며 형태 변화 시 다른 조직을 포함할 수 있다.

## 비교·검사·해석

모든 경로의 단계별 고정/정합 MAE·SSIM·LPIPS와 10단계 평균·최종값을 보고한다. P04 3정책은 고정/정합 설정, 넓은 얼굴/피부 합계/개별 피부 영역에 따른 평균·최종 순위를 전부 보존한다. MAE/LPIPS/highpass는 작은 순, SSIM은 큰 순으로 정렬하며 유리한 설정을 골라 주 분석을 바꾸지 않는다. 순위는 지표상 원본 유사도 순위이고 실제 피부 품질·요구 충족의 순위가 아니다. 9–10단계 raw→final 차이는 이미 실행된 개입의 출력 쌍 기술통계로만 보고하며 인과 효과나 새 정책 실행으로 보지 않는다.

P04 원본 기반 대조군 11종을 코드 배열로 재현한다: 동일성, 정수 이동(+24,+35)/(-31,-20), 밝기 +0.03/+0.10, 먼 좌우 주변 교체, 피부 주변 사인 무늬 진폭0.01/0.03/0.06, Gaussian blur sigma1/2. 세 정합 sigma마다 알려진 이동의 정확한 회복, 동일 crop 지표, 밝기 잔여 차이, 먼 주변 교체 피부 불변성, 사인 무늬의 highpass 반응 증가를 검사한다. np.roll 경계가 사용 ROI/탐색창에 들어오지 않는 배열 대조이고 실제 생성 결과 수에 포함하지 않는다.

manifest에는 입력 목록·재사용 코드·프로토콜·분석 스크립트·원본·모든 출력의 SHA256 및 라이브러리/LPIPS 가중치 해시를 저장한다. 실행 전후 불변성과 목록 완전성, 기존 고정 지표 재현, ROI 경계, 단계 집계와 순위를 테스트한다. 모든 쓰기는 `experiments/nonhuman-followup-v1/metrics/` 내부 산출물에 한정한다. 원본·과거 실험·임계값·정책·평가를 바꾸지 않고 생성 도구/평가자를 호출하지 않는다.

낮아진 점수를 피부 열화 제거량·자연스러움·감지 정확도라고 해석하지 않는다. 임계값 적용·재보정·정확도 계산은 하지 않는다. 동일 6인물/9경로는 독립 표본 90개가 아니며, P03 반복과 P04 공통 prefix/공유 rebase는 의존적이다. 시각 품질 라벨과 별도 생성 실행 없이 정합 기반 정책의 효과·비용 절감·최적 개입 시점을 주장할 수 없다.
