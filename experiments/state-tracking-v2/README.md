# 자동 최종 상태 갱신 비교

[설계](PROTOCOL.md) · [새 고정 대화](benchmark.json) · [평가 기준](EVALUATION.md)

실행: `.venv-local-prompt/bin/python experiments/state-tracking-v2/prepare.py`, 이어서 `.venv-local-image/bin/python experiments/state-tracking-v2/run.py`. 가림 비교판은 `.venv-metrics/bin/python experiments/state-tracking-v2/make_blind.py`, 얼굴 분석은 같은 환경의 `analyze.py`로 실행한다.

6명·새 대화 4종·두 시드·두 방법으로 96장, 최종 48쌍을 비교한다. 정답은 자동 프롬프트 생성 후 평가에만 사용한다. 개발용 T1–T4와 이전 H1–H3 결과를 이 실험의 분모에 합치지 않는다. 모델 호출 수와 처리 시간 차이를 보고한다.

공통 실행 코드는 `../state-tracking-v1/`의 경로 인자를 받는 스크립트를 재사용한다. 1차 추출기 실패 기록은 해당 폴더의 `DEVIATIONS.md`에 있다. 현재 자동 상태 갱신은 `local-studio/request_state.py`와 연구용 CLI `local-studio/track_requests.py`에서 실행할 수 있다.

독립 인간 채점 전까지 `human-ratings.csv`는 빈 양식이다. AI 시각 판정과 사람 평가를 구분한다.
