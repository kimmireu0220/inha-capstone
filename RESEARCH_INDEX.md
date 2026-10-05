# 반복 인물 이미지 편집 연구

이 저장소의 현재 결과는 [논문 원고·PDF·Word](paper/README.md)와 [현재 상태](CURRENT_STATUS.md)를 기준으로 읽는다. 연구 질문은 두 가지다. 같은 최종 편집에서 최초 원본을 다시 쓰면 순차 편집보다 얼굴을 더 보존하는가? 수정·취소가 있는 대화에서 최종 요구를 어떻게 종합해야 하며, 목표 반영과 얼굴 보존은 함께 좋아지는가?

## 논문에 사용한 자료

후속 방법 연구는 계속 진행 중이다. [동작 분리 N 고정 검증](experiments/action-plan-validation-v1/RESULTS.md)은 20/24에서 22/24의 제한적 개선을 보였지만, 남은 복원 오류를 보완한 [M 고정 검증](experiments/restore-contract-validation-v1/RESULTS.md)은 19/24로 동일한 복원 제약을 적용한 일반 대조의20/24를 넘지 못했다. [항목별 오류 격리의 O 고정 검증](experiments/slot-isolation-validation-v1/RESULTS.md)은29→30/32였지만 예정된 이미지 시점의 프롬프트가 모두 같았다. 현재 명시적 유지 제약을 보완한 [P 고정 검증](experiments/keep-contract-validation-v1/PROTOCOL.md)을 실행 중이며 이미지 계획에 모든 턴을 포함한다. 실패한 후보와 사후 개발 결과를 보존하며, 이미지 성능까지 검증하기 전 기존 논문의 확정된 해결 방법으로 반영하지 않는다.

현재 논문 이후의 방법 개발은 [요청 검사 파일럿](experiments/coverage-repair-v1/RESULTS.md)과 [고정 방법의 추가 대화 검증](experiments/coverage-validation-v1/RESULTS.md)으로 구분한다. 추가 검증에서 누락 검사의 개선이 재현되지 않아 후보를 채택하지 않았으며, 논문 본문에 확정된 개선 방법으로 반영하지 않는다. [오류 분석](experiments/coverage-validation-v1/INTERPRETATION.md)에 다음 연구에서 해결해야 할 동작 해석 문제를 기록했다.

- [합성 인물 6명·최종 18쌍 입력 정책 비교](experiments/studio-multiperson-v1/RESULTS.md)
- [실제 인물 6명·세 편집 이력·108장 최종 요구 종합 비교](experiments/prompt-synthesis-expanded-v1/RESULTS.md)
- [실제 인물 6명·새 대화 4종·96장 자동 상태 갱신 비교](experiments/state-tracking-v2/README.md)
- [전체 대화 상태 추출·추가 48개 조건 비교](experiments/state-format-control-v1/RESULTS.md)
- [동일 조건 12장 재사용의 근거인 2인물 예비 비교](experiments/prompt-synthesis-v1/RESULTS.md)
- [실제 인물 2명 정책 예비 비교](experiments/real-people-v1/RESULTS.md)
- [사진 출처와 사용 범위](assets/people/real/README.md)

기존 논문 수치의 원자료 해시는 [검산 기록](paper/evidence.json)에 있다. 새 96장 비교의 집계와 원자료 해시는 [실험 집계](experiments/state-tracking-v2/summary.json)에 있으며, 완료된 추가 대조까지 논문 전체 수치와 원자료 해시를 대조했다. 사진·생성 이미지·프롬프트·평가 원본은 재현을 위해 보존한다. 모델 가중치와 실행 환경은 저장소 밖에서 준비한다.

## 구현과 이전 발표

- [로컬 편집기 실행 안내](local-studio/README.md)
- [완료된 결과를 반영한 Google Slides](artifacts/README.md)
- [초기 10단계 연구 설계와 이전 분석](RESEARCH_DESIGN.md)

이전 발표와 실험 기록은 연구 경위를 확인하기 위한 자료다. 현재 논문의 표본 수·결론에 합산하지 않는다. Google Slides는 현재 40장으로, 자동 상태 갱신과 추가 대조의 완료된 결과, 실패와 평가 한계를 반영했다. 통합 결론과 발표자 노트도 갱신하고 전체 40장을 시각 확인했다.

## 완료된 추가 비교

자동 상태 갱신의 96장 비교는 생성·두 AI 평가·얼굴 측정을 완료했다. 1차 AI 목표 충족과 평균 얼굴 유사도는 자연어 종합보다 높았지만, 대화별 실패와 평가자 의존성이 있다. 상태 추출 결과와 초기 추출기 실패 기록은 별도로 보존한다.

[전체 대화에서 구조화된 상태를 추출하는 대조](experiments/state-format-control-v1/PROTOCOL.md)는 고정한 프롬프트로 48개 조건의 생성·1차 AI 채점·얼굴 측정을 완료했다. 목표 충족 127/288, ArcFace 0.846995이며, 중복 픽셀을 제외한 RGB 이미지는 36종이다. 2차 AI 평가도 완료했으며 목표 충족은 142/288이다. U2·U3의 배열 출력 오류까지 포함하며, 상태 관리만의 효과가 아니라 형식 준수를 포함한 시스템 비교로 해석한다. 같은 대화를 재사용한 후속 진단으로 새로운 일반화 검증은 아니다.
