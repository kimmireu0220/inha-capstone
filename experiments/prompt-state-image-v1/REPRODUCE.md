# 분석 재현

작업 위치는 저장소 최상위이다. `prepared.json`은 기존 텍스트 응답·요청·원본 사진·변환 코드의 해시와 생성 프롬프트 18개를 고정한다. `calls.json`은 첫 생성 출력의 위치·해시를 연결한다. 이미지 생성 자체는 내장 image_gen 도구로 수행하였다.

```sh
.venv-metrics/bin/python experiments/prompt-state-image-v1/prepare.py
.venv-metrics/bin/python experiments/prompt-state-image-v1/manage.py status
.venv-local-prompt/bin/python experiments/prompt-state-image-v1/measure_lengths.py
.venv-metrics/bin/python experiments/prompt-state-image-v1/measure_faces.py
.venv-local-eval/bin/python experiments/action-image-v1/evaluate.py experiments/prompt-state-image-v1
.venv-local-eval/bin/python experiments/prompt-state-image-v1/evaluate_secondary.py
.venv-metrics/bin/python experiments/prompt-state-image-v1/figure.py
.venv-metrics/bin/python experiments/prompt-state-image-v1/report.py
```

두 평가 스크립트는 각각 저장된 응답 18개를 재사용한다. 완료된 평가를 다시 실행해도 모델을 새로 호출하지 않는다. 원문과 형식 오류를 보존한다. 얼굴 측정은 저장된 원본과 출력만 사용하며 MLX 언어 모델을 호출하지 않는다. 토큰 측정도 고정 토크나이저만 사용한다. 가중치는 로컬 캐시에 보관하고 저장소에는 넣지 않는다.

이 실험은 모든 이미지를 최초 원본에서 생성하였다. 대화 접두 이력 12개에서 문자열 길이를 계산했지만 이미지 생성은 세 대화의 마지막 요청만 대상으로 했다. 순차 이미지 열화 실험의 10단계 수치와 이 실험의 얼굴 정렬 수치를 별도로 제시한다.

7B 평가 과정의 실행 중단과 재개는 `evaluation-interruptions.json`에 기록했다. 이미 저장한 응답은 재사용하고 미완료 항목만 이어서 평가했다. 완료 응답 수와 정확히 관측하지 못한 추론 시도 수를 구분한다.
