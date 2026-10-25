# 반복 인물 이미지 편집 연구

최신 진행 상황은 [현재 상태](CURRENT_STATUS.md)를 기준으로 읽는다. 현재 연구 질문은 한 번의 변경 사항 추출에 지시 구절 정규화와 실행 대상 검사를 적용하면 정확도와 필요한 모델 호출 횟수를 개선할 수 있는가이다.

## 반복 편집 관찰과 프롬프트 정리

- [초기 6인물 이미지 실험](experiments/nonhuman-followup-v1/RESULTS.md): 인물마다 같은 10단계 순차 편집. 최종 동일 요구의 원본 기반 결과와 비교해 위치 보정 MAE·SSIM·LPIPS가 모두 6/6쌍에서 원본 기반에 유리했다. [수치 재계산](paper/initial-portrait-verification.json)은 출력·원본 해시를 대조하고 오차 0을 확인했다.
- [전체 요청 이력과 현재 조건의 생성 비교](experiments/prompt-state-image-v1/RESULTS.md): Qwen3 최초 응답 기반, 실제 인물 두 명·기존 대화 세 개·세 방식, 첫 생성 이미지 18장. 마지막 요청에서 평균 204.00→122.67토큰. 얼굴 코사인·정렬 MAE·SSIM·LPIPS와 두 AI 모델의 요청 충족 평가를 분리했다. [분석 재현](experiments/prompt-state-image-v1/REPRODUCE.md).

## 최신 방법과 검증

[96개 새 요청의 추가 검증](experiments/extended-state-validation-v1/RESULTS.md). 추가 검증은 코드와 모델 설정을 유지한 새 합성 영어 대화 12개, 요청 96개이다. Qwen3의 첫 응답 단순 적용은 52/96, 한 번 추출과 지시 검사는 96/96이었다. Llama의 첫 응답 단순 적용은 27/96, 한 번 추출과 지시 검사는 93/96이었다. 모델별 점수를 따로 집계하고 대화 단위 정확도 차이의 95% 구간과 대응 검정을 계산했다. 원문 응답 384개와 모든 실패 사례를 보존했으며, 첫 응답 192개를 실제 실행 코드에 재생한 상태도 실험 결과와 일치했다.


- [한 번 추출과 지시 검사의 새 요청 검증](experiments/single-extraction-validation-v1/RESULTS.md): 새 요청 12개를 Qwen3와 Llama에 각각 적용. 단순 최초 응답은 두 모델 모두 3/12, 한 번 추출과 지시 검사는 모두 12/12. 두 번 호출한 검사 결합은 각각 12/12와 4/12. 실제 비교 실험은 총 48회 호출했다.
- [실행 대상 검사의 새 요청 검증](experiments/instruction-eligibility-validation-v1/RESULTS.md): 새 요청 16개, 총 64회 호출. Qwen3 9/16에서 16/16, Llama는 초기 재검토 오류로 0/16. 같은 요청을 두 모델에 각각 적용했다.
- [복원 표현 개선의 두 모델 검증](experiments/operation-scope-validation-v1/RESULTS.md): 새 요청 32개, 총 128회 호출. Qwen3 14/32에서 28/32, Llama 7/32에서 17/32.
- [복원 표현 개발](experiments/operation-scope-v2/RESULTS.md)과 [실행 대상 검사 개발](experiments/instruction-eligibility-v1/RESULTS.md): 앞선 자료의 재계산이며 새 모델 호출은 0회다. 최종 코드 검사 1323개도 실제 모델 관측과 구분한다.

## 앞선 구성요소 검증

- [표현과 지시 순서 추가 검증](experiments/instruction-transfer-v1/RESULTS.md)은 기존 구현을 고정하고 대화 12개, 요청 48개에 실제 모델 호출 96회를 수행했다. 기준 24/48, 기존 유지·삭제 27/48, 정규화 36/48이었다. 서로 다른 요청 문장은 32개다. 표현을 바꾼 요청에서는 정규화가 기존 어휘의 새 조합과 앞 지시의 수정에서 각각 8/8, 규칙에 없는 표현에서 0/8이었다. 새로운 복원 표현을 유지로 해석한 오류가 후속 요청에도 남았다.

- [같은 목표의 문장 구조 대조](experiments/clause-factorial-v1/RESULTS.md): 세 목표 구성·네 문장 구조·단계 세 번, 대화 12개·요청 36회. 실제 호출 72회, 서로 다른 요청 문장은 18개다. 기준 18/36, 기존 유지·삭제 26/36, 단순 JSON 적용 28/36, 정규화 36/36. 기존 코드는 고정한 채 사용했다.

- [구절 정규화의 새 대화 검증](experiments/clause-normalization-v1/RESULTS.md): 코드 고정 후 대화 네 개·요청 16개, 실제 추론 32회. 기준 9/16, 기존 유지·삭제 10/16, 정규화 16/16. 항목별 적용은 10/16, 정규화와 결합하면 16/16. 개선은 세 대화에서 나타났으며 새 오류는 0건이다.
- [동일 목표의 표현 변화 검사](experiments/paraphrase-contract-v1/RESULTS.md): 기존 T와 목표를 공유하는 32개 대응 요청, 실제 추론 64회. 기존 네 방법은 모두 25/32였다. 이 결과를 구절 정규화 개발에 사용하였다. 개발 재계산과 새 대화 검증을 구분한다.

- [포즈·표정 확장 C와 동작 대조](experiments/compound-edit-v1/RESULTS.md): 대화 12개, 요청 48개. 혼합 조건은 재검토 4/16, 규칙 보정 16/16이며 삭제 규칙만으로 동일한 결과. 사후 짧은 대조 8개는 7/8. 정답 요청 이미지 6장은 평가 오류를 기록했다. S·T와 별도 구현이다.
- [유지·삭제 제약과 S 검증](experiments/request-contract-v3/RESULTS.md): 기준 27/32, 유지 27/32, 삭제 28/32, 결합 29/32. 최종 상태 일치율 6/8→7/8. 개선은 한 대화의 두 요청에 집중됐다.
- [별도 T 검증](experiments/isolated-contract-v1/RESULTS.md): 기준 28/32, 유지·삭제 29/32. 최종 상태 일치율 7/8→8/8. 변경을 항목별로 적용하는 처리를 추가해도 결과는 같았다.
- [S 이미지 검증](experiments/contract-image-v3/INTERPRETATION.md): 128조건·66개 고유 이미지의 1차 평가와 검산 완료. 목표 350/384→358/384 중 증가 6개는 판단 불가→성공이다. 입력이 다른 비교는 네 쌍이다. [7B 후속 평가](experiments/contract-image-review-v1/INTERPRETATION.md)는 전체 68개 고유 평가 입력에서 372/384→374/384였다. 판단 불가는 없어졌지만 설명 모순은 남았다. 같은 계열의 두 모델을 이용한 사후 판정 비교이다.
- [P 이미지 결과와 해석](experiments/keep-image-v1/INTERPRETATION.md): 128조건·68개 고유 이미지. 점수 차이는 판단 불가였던 한 항목이 성공으로 바뀐 결과다.

텍스트 검증은 개발자가 작성한 제한 문형 검사다. 서로 다른 개발 단계의 자료이며 표본 수는 실험별로 집계한다. [최신 논문](paper/README.md)은 기존 규칙·복합 요청·이미지 분석에 표현 변화 검사와 구절 정규화 검증을 반영했다. [10장 Google Slides](artifacts/README.md)도 같은 범위의 결과와 한계를 반영했다.

## 방법 개발 경위

- [요청 누락 검사 개발](experiments/coverage-repair-v1/RESULTS.md), [V 추가 검증](experiments/coverage-validation-v1/RESULTS.md)
- [동작 분리 개발](experiments/action-plan-v2/RESULTS.md), [N 검증](experiments/action-plan-validation-v1/RESULTS.md)
- [원본 복원 제약 개발](experiments/restore-contract-v1/PROTOCOL.md), [M 검증](experiments/restore-contract-validation-v1/RESULTS.md)
- [항목별 오류 격리 개발](experiments/slot-isolation-v1/RESULTS.md), [O 검증](experiments/slot-isolation-validation-v1/RESULTS.md)
- [유지 규칙 개발](experiments/keep-contract-v1/PROTOCOL.md), [P 검증](experiments/keep-contract-validation-v1/RESULTS.md), [경계 점검](experiments/keep-contract-v1/BOUNDARIES.md), [Q 검증](experiments/keep-contract-v2/RESULTS.md)

채택되지 않은 후보와 사후 분석을 보존한다. 개발 자료에서의 개선과 코드 고정 후 별도 대화에서의 검증은 구별한다.

## 앞선 비교 연구 자료

- [합성 인물 6명·최종 18쌍 입력 정책 비교](experiments/studio-multiperson-v1/RESULTS.md)
- [실제 인물 6명·세 편집 이력·108장 최종 요구 종합](experiments/prompt-synthesis-expanded-v1/RESULTS.md)
- [실제 인물 6명·새 대화 4종·96장 자동 상태 갱신](experiments/state-tracking-v2/README.md)
- [전체 대화 상태 추출·추가 48조건 대조](experiments/state-format-control-v1/RESULTS.md)
- [동일 조건 12장 재사용의 근거인 예비 비교](experiments/prompt-synthesis-v1/RESULTS.md)
- [실제 인물 2명 정책 예비 비교](experiments/real-people-v1/RESULTS.md)
- [사진 출처와 사용 범위](assets/people/real/README.md)

앞선 자료는 후속 연구의 동기와 경위를 확인하기 위한 기록이며 실험별 표본 수와 결과를 따로 집계한다. 사진·생성 출력·프롬프트·평가 원문은 재현을 위해 보존한다.

## 구현과 산출물

- [로컬 이미지 편집기](local-studio/README.md)
- [배포 논문 파일과 검산](paper/README.md)
- [온라인 발표 자료와 반영 상태](artifacts/README.md)
- [초기 연구 설계](RESEARCH_DESIGN.md)
