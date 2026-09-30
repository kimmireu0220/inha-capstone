# 편집 대화 최종 요구 종합 실험

[결과](RESULTS.md) · [고정 조건](PROTOCOL.md) · [8개 요청](history.json) · [최종 상태](final-state.json) · [에이전트 수행 기록](agent-transcript.json)

8개 요청 중 조건을 바꾸거나 취소하는 사례에서 전체 대화 전달, 구조화 상태 정리, 로컬 에이전트 종합을 비교했다. 실제 인물 2명 × 시드 2개 × 방법 3개로 새 출력 12장과 4개 가림 비교판을 만들었다. 사진과 출력은 로컬 모델에만 입력했다.

재현 절차(로컬 모델 환경 준비 후):

```sh
.venv-local-prompt/bin/python experiments/prompt-synthesis-v1/prepare.py
.venv-metrics/bin/python -u experiments/prompt-synthesis-v1/run.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv-metrics/bin/python experiments/prompt-synthesis-v1/analyze.py
.venv-metrics/bin/python experiments/prompt-synthesis-v1/report.py
```

`prepare.py`는 프롬프트가 이미 있으면 재작성하지 않는다. 새로운 반복은 별도 디렉터리에서 한다. 채점은 방법명과 얼굴 유사도 결과를 보기 전에 `blind/` 비교판을 보고 `blind-ratings.json`에 저장한다. 현재 결과는 한 평가자의 탐색적 육안 점수다.
