# 사이트 다인물 비교

실제 편집기 API를 통해 가상 인물 6명 × 시드 3개에서 순차 3회와 일괄 1회를 실행한다. 출력 72개, 최종 비교 18쌍을 완료했다.

- [실험 조건](PROTOCOL.md)
- [진행 상태](running.json)
- [결과](RESULTS.md)
- [호출 기록](calls.json)

실행:

```sh
.venv-metrics/bin/python -u experiments/studio-multiperson-v1/run.py
.venv-metrics/bin/python experiments/studio-multiperson-v1/analyze.py
```

사이트가 `http://localhost:8770`에서 실행 중이어야 한다. `finish.py`가 생성 완료 후 분석을 실행한다. 결과 파일의 `complete`는 참이며, 72개 생성과 18쌍의 검증이 끝났다. 생성 이미지는 사이트 작업 목록에서도 확인할 수 있다.
