# 인물 이미지 반복 편집 연구

장신구·의상·배경을 반복해서 수정할 때 생기는 얼굴 변화와, 최초 원본에 현재 요구사항을 한 번에 적용해 다시 생성하는 방법을 비교한 예비 실험입니다.

## 발표 자료

- [상세 발표 자료 PowerPoint](artifacts/팀_연구_진행상황_상세본_GitHub_v2.pptx)
- [실제 프롬프트와 단계별 상세 수치](artifacts/실험_프롬프트와_상세수치.md)
- [연구 질문과 현재 범위](RESEARCH_DESIGN.md)

## 실험 기록

- [종합 결과](experiments/nonhuman-followup-v1/RESULTS.md)
- [현행 실험의 입력 이미지 목록](experiments/revised-tail-v1/inputs.json)
- [1~8단계 프롬프트가 포함된 원래 호출 기록](experiments/ten-stage-v1/calls.json)
- [수정한 9~10단계 프롬프트](experiments/revised-tail-v1/prompts.json)
- [종료 후 재생성 입력과 프롬프트](experiments/nonhuman-followup-v1/generation/end-jobs.json)
- [현행 단계별 출력과 계산값](experiments/revised-tail-v1/curves.json)
- [지표 계산 영역과 구현 조건](experiments/nonhuman-followup-v1/metrics/PROTOCOL.md)
- [단계별 AI 평가](experiments/nonhuman-followup-v1/agent-agreement/joined-stages.csv)
- [사람 평가 질문과 결과](experiments/nonhuman-followup-v1/HUMAN_EVALUATION.md)
- [사람 등급과 계산 지표의 비교](experiments/nonhuman-followup-v1/human-analysis/THRESHOLD_FREE.md)

원본은 생성 인물 6명이며 반복 편집은 7회입니다. 인물 3의 두 반복과 방법 간 공유 출력은 독립 표본으로 중복 계산하지 않습니다. 최종 사람 평가는 1명의 예비 결과입니다.

현재 결과의 1~8단계는 원래 호출 기록, 9~10단계는 위 수정 기록을 기준으로 합니다. 초기 임시 임계값을 검증된 감지 기준으로 주장하지 않습니다.

이 업로드는 발표 자료와 근거 기록, 발표에 사용한 이미지를 공유하기 위한 것입니다. 전체 실행 환경과 모든 과거 생성물의 배포본은 아닙니다. 원본 실행 기록의 절대 경로는 실행 당시의 경로이며, 이 저장소에서는 같은 상대 경로의 파일을 확인하면 됩니다. 기록에 등장하는 일부 미포함 생성물과 실행 의존성은 이 업로드만으로 재실행할 수 없습니다.
