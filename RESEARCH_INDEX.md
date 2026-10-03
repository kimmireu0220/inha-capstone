# 반복 인물 이미지 편집 연구

이 저장소의 현재 결과는 [논문 원고·PDF·Word](paper/README.md)와 [현재 상태](CURRENT_STATUS.md)를 기준으로 읽는다. 연구 질문은 두 가지다. 같은 최종 편집에서 최초 원본을 다시 쓰면 순차 편집보다 얼굴을 더 보존하는가? 수정·취소가 있는 대화에서 최종 요구를 어떻게 종합해야 하며, 목표 반영과 얼굴 보존은 함께 좋아지는가?

## 논문에 사용한 자료

- [합성 인물 6명·최종 18쌍 입력 정책 비교](experiments/studio-multiperson-v1/RESULTS.md)
- [실제 인물 6명·세 편집 이력·108장 최종 요구 종합 비교](experiments/prompt-synthesis-expanded-v1/RESULTS.md)
- [실제 인물 6명·새 대화 4종·96장 자동 상태 갱신 비교](experiments/state-tracking-v2/README.md)
- [동일 조건 12장 재사용의 근거인 2인물 예비 비교](experiments/prompt-synthesis-v1/RESULTS.md)
- [실제 인물 2명 정책 예비 비교](experiments/real-people-v1/RESULTS.md)
- [사진 출처와 사용 범위](assets/people/real/README.md)

기존 논문 수치의 원자료 해시는 [검산 기록](paper/evidence.json)에 있다. 새 96장 비교의 집계와 원자료 해시는 [실험 집계](experiments/state-tracking-v2/summary.json)에 있으며, 논문 전체 검산은 진행 중인 대조까지 완료한 뒤 갱신한다. 사진·생성 이미지·프롬프트·평가 원본은 재현을 위해 보존한다. 모델 가중치와 실행 환경은 저장소 밖에서 준비한다.

## 구현과 이전 발표

- [로컬 편집기 실행 안내](local-studio/README.md)
- [갱신 중인 Google Slides](artifacts/README.md)
- [초기 10단계 연구 설계와 이전 분석](RESEARCH_DESIGN.md)

이전 발표와 실험 기록은 연구 경위를 확인하기 위한 자료다. 현재 논문의 표본 수·결론에 합산하지 않는다. Google Slides는 현재 39장으로, 완료된 자동 상태 갱신의 방법·결과·한계 3장을 추가했다. 대조 결과와 통합 결론 반영, 최종 시각 점검은 남아 있다.

## 진행 중인 추가 비교

자동 상태 갱신의 96장 비교는 생성·두 AI 평가·얼굴 측정을 완료했다. 1차 AI 목표 충족과 평균 얼굴 유사도는 자연어 종합보다 높았지만, 대화별 실패와 평가자 의존성이 있다. 독립 인간 검증은 없다. 상태 추출 결과와 초기 추출기 실패 기록은 별도로 보존한다.

[전체 대화에서 구조화된 상태를 추출하는 대조](experiments/state-format-control-v1/PROTOCOL.md)는 고정한 프롬프트로 48개 조건의 생성·1차 AI 채점·얼굴 측정을 완료했다. 목표 충족 127/288, ArcFace 0.846995이며, 중복 픽셀을 제외한 RGB 이미지는 36종이다. 2차 AI 평가는 진행 중이다. U2·U3의 배열 출력 오류까지 포함하며, 상태 관리만의 효과가 아니라 형식 준수를 포함한 시스템 비교로 해석한다. 같은 대화를 재사용한 후속 진단으로 새로운 일반화 검증은 아니다.
