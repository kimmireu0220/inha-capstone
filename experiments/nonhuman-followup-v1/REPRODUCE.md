# 재현과 자료 구분

작업 루트: `/Users/kimmireu/Desktop/Storage/inha-capstone`.

실제 생성은 내장 imagegen 도구로 실행했고 입력·프롬프트·출력 SHA256·호출 시각을 보존했다. 모델의 정확한 내부 버전과 시드는 도구 매개변수에 노출되지 않으므로 새 호출에서 같은 픽셀이 나오는 재현을 보장하지 않는다. 아래 명령은 저장된 이미지의 분석 재현이며 새 이미지 생성이나 사람 응답을 만들지 않는다.

```sh
.venv-metrics/bin/python experiments/nonhuman-followup-v1/generation/run.py
.venv-metrics/bin/python experiments/nonhuman-followup-v1/audit_generation.py
.venv-metrics/bin/python experiments/nonhuman-followup-v1/metrics/analyze.py
.venv-metrics/bin/python experiments/nonhuman-followup-v1/metrics/report.py
.venv-metrics/bin/python experiments/nonhuman-followup-v1/agent-agreement/analyze.py
.venv-metrics/bin/python experiments/nonhuman-followup-v1/agent-agreement/report.py
.venv-metrics/bin/python experiments/nonhuman-followup-v1/extension-metrics/analyze.py --finalize
.venv-metrics/bin/python experiments/nonhuman-followup-v1/extension-metrics/report.py
.venv-metrics/bin/python experiments/nonhuman-followup-v1/join_reviews.py
.venv-metrics/bin/python experiments/nonhuman-followup-v1/figures.py
.venv-metrics/bin/python experiments/nonhuman-followup-v1/analyze_human_final.py
.venv-metrics/bin/python -m unittest experiments/nonhuman-followup-v1/human-analysis/test_analysis.py
```

동일 해시의 생성 요청은 출력 공유 규칙에 따라 재사용한다. P05 once9단계 실패 요청은 failure 기록을 읽어 재시도하지 않는다. collection_complete=true는 수집 종료, full_design_complete=false는 계획 중 미실행이 남았음을 뜻한다.

metrics/, agent-agreement/, extension-metrics/에는 각 계산의 manifest·검사·가중치·버전 기록이 있다. join_reviews.py는 세 얼굴 패킷의 133개 항목을 각 평가자 원문과 연결하고, 비교 PNG의 원본/후보 crop이 저장된 이미지 픽셀과 정확히 같은지 검사한다. 원본 대조 10개와 숨긴 반복 12개는 고유 111개 표본에서 제외한다. 요구 조건 평가는 별도 새 세션의 16개 고유 후보를 연결한다.

평가 프롬프트는 최초 PROTOCOL.md, EXTENSION_EVALUATION.md와 blind-requirements/INSTRUCTIONS.md에 기록했다. face-a/b는 같은 기반 모델의 독립 얼굴 평가 세션, requirements-a/b는 별도 새 세션의 전체 요구 평가다. 서로의 결과·방법·단계·지표를 전달하지 않았으며 원문 JSON을 수정하거나 합의 라벨로 합치지 않았다.

그림용으로만 가상환경에 matplotlib 3.10.6을 추가했다. 설치 당시 기존 numpy 1.26.4와 pillow 10.2.0은 변경하지 않았다. 그림 코드는 JSON 점수로 그래프를 그리며 인물 원본을 수정하지 않는다. 그래프의 고정/정합 패널은 같은 y축 범위를 사용한다. 위치 정합된 지표에는 기존 고정 임계값을 적용하지 않는다.

## 핵심 파일

- RESULTS.md: 통합 해석과 논문에 남길 주장.
- generation/{progress.json,generated/,failures/}: 입력 연결·성공 출력·실패 원문.
- reviews/: 독립 AI 평가 원문. 인간 응답이 아님.
- private/: 익명 ID와 원본·출력·경로 해독표. 평가자에게 전달하지 않음.
- joined-reviews/: 고유 얼굴 111개·관측 단계 198개·고유 최종 요구 16개 결합 및 조건부 지표 진단.
- figures/: 원본 차이와 피부 관찰의 불일치, P04 정책 곡선.
- literature/: 일차 문헌·실험 대조·반대 관점 주장 검토.
- human-responses/: 제출된 사람 평가 원문.
- human-analysis/: 사람 평가 해독, 임계값 없는 ROC-AUC와 동일 인물 쌍 비교.

기존 포켓스퀘어 실패 자료와 과거 사람 응답은 현재 새 9~10단계의 근거로 재사용하지 않는다. 배제한 원문을 삭제하거나 새로운 관측으로 덮어쓰지 않는다.
