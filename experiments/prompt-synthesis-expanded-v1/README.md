# 실제 인물 6명·편집 이력 3종의 최종 요구 종합 비교

교수 피드백의 세 번째 방향인 “여러 차례 바뀐 요청을 어떻게 종합할 것인가”를 검사한다. [결과 요약](RESULTS.md), [연구 설계](PROTOCOL.md), [평가 기준](EVALUATION.md)을 참조한다. `state`는 정확한 최종 상태를 아는 상한 기준이고, `agent`는 자연어 이력만 읽는 로컬 에이전트, `history`는 이력 전문을 이미지 모델에 직접 전달하는 기준이다.

인물·이력·시드·방법의 108개 조합 중 기존 H1/R01·R02의 12개는 입력·프롬프트·출력 해시가 일치할 때만 재사용한다. 나머지 96개는 `run.py`가 생성하며 조건별 `input.png`, `prompt.txt`, `output.png`, `model.log`를 남긴다. `plan.json`은 생성 전에 고정한 입력·프롬프트와 설정의 해시를 담고 `calls.json`은 완료된 출력의 해시·소요 시간을 담는다. 실행 중단 시 같은 명령으로 완료 조건을 건너뛰고 이어 간다.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-local-prompt/bin/python experiments/prompt-synthesis-expanded-v1/run.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-metrics/bin/python experiments/prompt-synthesis-expanded-v1/analyze.py
.venv-local-prompt/bin/python experiments/prompt-synthesis-expanded-v1/report.py
```

`analyze.py`는 108개 조건의 해시와 이미지 파일을 검증하고 얼굴 유사도를 측정한 뒤 방법명을 가린 36개 비교판을 만든다. 육안 점수는 `blind-ratings.json`에 기록하고 `report.py`가 해제된 방법명과 결합한다. 생성 중 예외는 [DEVIATIONS.md](DEVIATIONS.md)에 별도로 남긴다. 실제 인물 사진의 사용 범위와 출처는 [Pexels 출처 기록](../../assets/people/real/README.md)을 참조한다.
