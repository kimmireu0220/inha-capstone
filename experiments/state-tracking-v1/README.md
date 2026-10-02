# 자동 요청 상태 갱신 실험

이 버전은 이미지 생성 전 추출기 개발 점검에서 중단했다. [중단 기록](DEVIATIONS.md)에 원인과 실행 범위를 기록했다. 아래 명령은 당시 계획이며 최종 비교 실행을 의미하지 않는다.

진행 상태와 생성 조건은 `running.json`, `plan.json`에 기록한다. [사전 설계](PROTOCOL.md)와 [고정 대화](benchmark.json), [평가 기준](EVALUATION.md)을 따른다. 성공 여부에 관계없이 96개 조건 전체를 평가한다.

실행 순서:

1. `.venv-local-prompt/bin/python local-studio/checks/test_request_state.py`
2. `.venv-local-prompt/bin/python experiments/state-tracking-v1/prepare.py`
3. `.venv-local-image/bin/python experiments/state-tracking-v1/run.py`
4. `.venv-metrics/bin/python experiments/state-tracking-v1/make_blind.py`
5. 방법명을 가린 비교판을 채점한다. AI 판정은 `ai-ratings.json`, 독립 인간 판정은 `human-ratings.csv`에 구분해 기록한다.
6. `.venv-metrics/bin/python experiments/state-tracking-v1/analyze.py`

새 자동 방법은 [request_state.py](../../local-studio/request_state.py)에 있다. 모델은 정답 상태를 받지 않고 각 자연어 요청을 변경 동작으로 추출한다. [track_requests.py](../../local-studio/track_requests.py)는 JSON 표준 입력으로 호출하는 연구용 CLI다. 기존 웹 화면의 3항목 인터페이스와 별도로 6항목 제한 어휘를 지원한다.

이미지 생성 전에 모든 프롬프트와 입력을 해시로 고정한다. `state-scores.json`의 정답 비교는 그 이후 실행한다. `human-ratings.csv`는 사람이 채점하기 전까지 빈 양식이며 독립 인간 검증 완료를 의미하지 않는다.
