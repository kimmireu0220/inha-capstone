# 자동 최종 상태 갱신 비교

[설계](PROTOCOL.md) · [새 고정 대화](benchmark.json) · [평가 기준](EVALUATION.md)

실행: `.venv-local-prompt/bin/python experiments/state-tracking-v2/prepare.py`, 이어서 `.venv-local-image/bin/python experiments/state-tracking-v2/run.py`. 가림 비교판은 `.venv-metrics/bin/python experiments/state-tracking-v2/make_blind.py`, 얼굴 분석은 같은 환경의 `analyze.py`로 실행한다.

6명·새 대화 4종·두 시드·두 방법으로 96장, 최종 48쌍을 비교한다. 정답은 자동 프롬프트 생성 후 평가에만 사용한다. 개발용 T1–T4와 이전 H1–H3 결과를 이 실험의 분모에 합치지 않는다. 모델 호출 수와 처리 시간 차이를 보고한다.

공통 실행 코드는 `../state-tracking-v1/`의 경로 인자를 받는 스크립트를 재사용한다. 1차 추출기 실패 기록은 해당 폴더의 `DEVIATIONS.md`에 있다. 현재 자동 상태 갱신은 `local-studio/request_state.py`와 연구용 CLI `local-studio/track_requests.py`에서 실행할 수 있다.

독립 인간 채점 전까지 `human-ratings.csv`는 빈 양식이다. AI 시각 판정과 사람 평가를 구분한다.

프롬프트 준비가 완료되어 `prepare-manifest.json`과 `plan.json`의 해시를 고정했다. 새 대화의 자동 상태는 턴별 186/192항목, 최종 22/24항목이 맞았다. U4의 배경·소품 교체 오류를 그대로 포함해 96장 생성을 완료했다. Codex의 48쌍 가림 평가와 출력 해시 검증·얼굴 유사도 측정도 완료했으며, 별도 로컬 AI 평가는 진행 중이다. 종합 결과는 두 평가가 모두 끝난 뒤 보고한다.

보조 AI 평가는 `.venv-local-eval/bin/python experiments/state-tracking-v2/second_ai.py`로 실행한다. 모델은 로컬 Qwen2.5-VL 3B 4bit, 런타임은 mlx-vlm 0.7.4다. 이미지 모델과 동시에 GPU에서 실행하지 않는다. 원문 응답·버전·형식 오류를 기록하며, 사람용 양식에는 자동 점수를 쓰지 않는다.
