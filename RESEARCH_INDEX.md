# 반복 인물 이미지 편집 연구

이 저장소의 현재 결과는 [논문 원고·PDF·Word](paper/README.md)와 [현재 상태](CURRENT_STATUS.md)를 기준으로 읽는다. 연구 질문은 두 가지다. 같은 최종 편집에서 최초 원본을 다시 쓰면 순차 편집보다 얼굴을 더 보존하는가? 수정·취소가 있는 대화에서 최종 요구를 어떻게 종합해야 하며, 목표 반영과 얼굴 보존은 함께 좋아지는가?

## 논문에 사용한 자료

- [합성 인물 6명·최종 18쌍 입력 정책 비교](experiments/studio-multiperson-v1/RESULTS.md)
- [실제 인물 6명·세 편집 이력·108장 최종 요구 종합 비교](experiments/prompt-synthesis-expanded-v1/RESULTS.md)
- [동일 조건 12장 재사용의 근거인 2인물 예비 비교](experiments/prompt-synthesis-v1/RESULTS.md)
- [실제 인물 2명 정책 예비 비교](experiments/real-people-v1/RESULTS.md)
- [사진 출처와 사용 범위](assets/people/real/README.md)

논문 수치의 원자료 해시는 [검산 기록](paper/evidence.json)에 있다. 사진·생성 이미지·프롬프트·평가 원본은 재현을 위해 보존한다. 모델 가중치와 실행 환경은 저장소 밖에서 준비한다.

## 구현과 이전 발표

- [로컬 편집기 실행 안내](local-studio/README.md)
- [이전 Google Slides 위치](artifacts/README.md)
- [초기 10단계 연구 설계와 이전 분석](RESEARCH_DESIGN.md)

이전 발표와 실험 기록은 연구 경위를 확인하기 위한 자료다. 현재 논문의 표본 수·결론에 합산하지 않으며, 슬라이드는 새 논문의 발표본으로 갱신되지 않았다.
