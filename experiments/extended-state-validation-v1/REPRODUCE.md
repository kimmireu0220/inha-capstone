# 추가 검증 재현

저장소 최상위에서 실행한다. 모델 설정과 필요한 라이브러리는 `frozen.json`에 고정되어 있으며, 모델 가중치는 Hugging Face 로컬 캐시에 둔다.

```sh
.venv-local-prompt/bin/python experiments/extended-state-validation-v1/test_design.py
.venv-metrics/bin/python experiments/extended-state-validation-v1/test_report.py
.venv-local-prompt/bin/python experiments/extended-state-validation-v1/run.py
.venv-local-prompt/bin/python experiments/extended-state-validation-v1/report.py
```

실행기는 시작 시 고정한 입력 해시를 검사한다. 모델별 `transcripts-*.json`에 첫 응답과 재검토를 각각 저장하며, 저장한 응답은 재호출하지 않는다. `attempts-*.json`은 호출 시작·완료·오류를 기록한다. 한 번 추출과 검사 결합은 첫 응답만 사용한다. 재검토 응답은 비교 조건을 채점하기 위해 수집한다.

보고서는 저장 응답으로 모든 비교 점수를 재계산하고, 저장된 결과와 일치하는지 확인한다. 대화 단위 구간과 대응 무작위화 검정을 계산하며, 첫 응답 192개를 실제 실행 코드에도 재생한다. 보고서 생성과 재생에는 모델을 추가 호출하지 않는다.

`verification.json`에는 실행 입력·방법·원문 응답·분석 코드·결과 요약의 해시를 기록한다. 실패 요청도 `summary.json`의 `failures`에 모두 포함한다. 원자료는 합성 영어 대화 12개이며 네 가지 표현 틀을 공유한다.
