# 반복 인물 이미지 편집 연구

최신 진행 상황은 [현재 상태](CURRENT_STATUS.md)를 기준으로 읽는다. 현재 연구 질문은 명시적인 유지·삭제 지시를 별도로 검사하면 모델의 편집 상태 갱신 오류를 줄일 수 있는가이다.

## 최신 방법과 검증

- [유지·삭제 제약과 S 검증](experiments/request-contract-v3/RESULTS.md): 기준 27/32, 유지 27/32, 삭제 28/32, 결합 29/32. 최종 대화 6/8→7/8. 개선은 한 대화의 두 턴에 집중됐다.
- [별도 T 검증](experiments/isolated-contract-v1/RESULTS.md): 기준 28/32, 유지·삭제 29/32. 최종 대화 7/8→8/8. 항목별 오류 격리를 추가한 이점은 없었다.
- [S 이미지 검증](experiments/contract-image-v3/INTERPRETATION.md): 128조건·66개 고유 이미지의 1차 평가와 검산 완료. 목표 350/384→358/384 중 증가 6개는 판단 불가→성공이다. 입력이 다른 비교는 네 쌍이다. [7B 후속 평가](experiments/contract-image-review-v1/INTERPRETATION.md)는 전체 68개 고유 평가 입력에서 372/384→374/384였다. 판단 불가는 없어졌지만 설명 모순은 남았다. 사후 분석이며 독립 정답 검증이 아니다.
- [P 이미지 결과와 해석](experiments/keep-image-v1/INTERPRETATION.md): 128조건·68개 고유 이미지. 목표 점수의 한 항목 차이만으로 뚜렷한 이미지 개선을 주장하지 않는다.

두 텍스트 검증은 개발자가 작성한 제한 문형 검사다. 서로 다른 개발 단계의 자료이며 표본 수를 합산하지 않는다. [최신 논문](paper/README.md)은 S·T와 이미지 분석을 반영했다. [40장 Google Slides](artifacts/README.md)는 아직 앞선 비교 연구 산출물이며 인증 재연결이 필요하다.

## 방법 개발 경위

- [요청 누락 검사 개발](experiments/coverage-repair-v1/RESULTS.md), [V 추가 검증](experiments/coverage-validation-v1/RESULTS.md)
- [동작 분리 개발](experiments/action-plan-v2/RESULTS.md), [N 검증](experiments/action-plan-validation-v1/RESULTS.md)
- [원본 복원 제약 개발](experiments/restore-contract-v1/PROTOCOL.md), [M 검증](experiments/restore-contract-validation-v1/RESULTS.md)
- [항목별 오류 격리 개발](experiments/slot-isolation-v1/RESULTS.md), [O 검증](experiments/slot-isolation-validation-v1/RESULTS.md)
- [유지 보호 개발](experiments/keep-contract-v1/PROTOCOL.md), [P 검증](experiments/keep-contract-validation-v1/RESULTS.md), [경계 점검](experiments/keep-contract-v1/BOUNDARIES.md), [Q 검증](experiments/keep-contract-v2/RESULTS.md)

채택되지 않은 후보와 사후 분석을 보존한다. 개발 자료에서의 개선과 코드 고정 후 별도 대화에서의 검증은 구별한다.

## 앞선 비교 연구 자료

- [합성 인물 6명·최종 18쌍 입력 정책 비교](experiments/studio-multiperson-v1/RESULTS.md)
- [실제 인물 6명·세 편집 이력·108장 최종 요구 종합](experiments/prompt-synthesis-expanded-v1/RESULTS.md)
- [실제 인물 6명·새 대화 4종·96장 자동 상태 갱신](experiments/state-tracking-v2/README.md)
- [전체 대화 상태 추출·추가 48조건 대조](experiments/state-format-control-v1/RESULTS.md)
- [동일 조건 12장 재사용의 근거인 예비 비교](experiments/prompt-synthesis-v1/RESULTS.md)
- [실제 인물 2명 정책 예비 비교](experiments/real-people-v1/RESULTS.md)
- [사진 출처와 사용 범위](assets/people/real/README.md)

앞선 자료는 후속 연구의 동기와 경위를 확인하기 위한 기록이며 S·T 표본 수나 결과에 합산하지 않는다. 사진·생성 출력·프롬프트·평가 원문은 재현을 위해 보존한다.

## 구현과 산출물

- [로컬 이미지 편집기](local-studio/README.md)
- [배포 논문 파일과 검산](paper/README.md)
- [온라인 발표 자료와 반영 상태](artifacts/README.md)
- [초기 연구 설계](RESEARCH_DESIGN.md)
