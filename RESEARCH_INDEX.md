# 인물 이미지 반복 편집 연구

장신구·의상·배경을 반복해서 수정할 때 생기는 얼굴 변화와, 최초 원본에 현재 요구사항을 한 번에 적용해 다시 생성하는 방법을 비교한 예비 실험입니다.

**최신 범위·수치·구현 상태: [현재 상태](CURRENT_STATUS.md)**

## 논문 원고

- [현재 실험 기반 한국어 논문: Markdown·Word·PDF](paper/README.md)
- [로컬 피부 영역·위치 보정 사후 분석](experiments/local-policy-robustness-v1/RESULTS.md)

## 발표 자료

- [초기 연구 발표 자료 PowerPoint — 후속 실험 미반영](artifacts/팀_연구_진행상황_상세본_GitHub_v2.pptx)
- [실제 프롬프트와 단계별 상세 수치](artifacts/실험_프롬프트와_상세수치.md)
- [연구 질문과 현재 범위](RESEARCH_DESIGN.md)
- [평가 형식 정리 기록](EVALUATION_CLEANUP.md)
- [프로젝트 검토](RESEARCH_REVIEW_2026-09-08.md)
- [공개 설문 코드와 운영 안내](evaluation/README.md)

## 실험 기록

- [무료 로컬 FLUX 모델의 일괄·순차 비교: 두 시드·8장](experiments/local-policy-v1/RESULTS.md)

- [공개 모델의 M1 로컬 실행 확인: 이미지 편집·한국어 요구사항 갱신](experiments/local-open-model-v1/RESULTS.md)

- [후속12개 별도 AI 평가와 사람·자동 지표 연결](experiments/followup-ai-v1/RESULTS.md)

- [두 문항 재평가를 반영한 최신 사람 평가](experiments/followup-human-v1/RECHECKED_RESULTS.md)
- [후속 12개 출력의 실제 사람 1명 최초 평가 분석](experiments/followup-human-v1/RESULTS.md)

- [2026-09-09 자율 후속 실험 종합: 새 생성 84회](experiments/autonomous-nonhuman-v1/RESULTS.md)
- [기존 종합 결과](experiments/nonhuman-followup-v1/RESULTS.md)
- [추가 실험: 한 번에 편집·순차 편집·무변경 반복 14회](experiments/edit-decomposition-v1/RESULTS.md)
- [추가 실험: 편집 순서 6종·38회와 피부 평균색 진단](experiments/edit-order-v1/RESULTS.md)
- [추가 실험: 다른 두 인물에서 일괄/순차 재현 16회](experiments/edit-replication-v1/RESULTS.md)
- [추가 실험: 색 × 재질 네 조건·세 인물·24회](experiments/edit-factors-v1/RESULTS.md)
- [추가 실험: 변경 없는 두 경로를 6단계까지 연장·새 6회](experiments/nochange-extension-v1/RESULTS.md)
- [현행 실험의 입력 이미지 목록](experiments/revised-tail-v1/inputs.json)
- [1~8단계 프롬프트가 포함된 원래 호출 기록](experiments/ten-stage-v1/calls.json)
- [수정한 9~10단계 프롬프트](experiments/revised-tail-v1/prompts.json)
- [종료 후 재생성 입력과 프롬프트](experiments/nonhuman-followup-v1/generation/end-jobs.json)
- [현행 단계별 출력과 계산값](experiments/revised-tail-v1/curves.json)
- [지표 계산 영역과 구현 조건](experiments/nonhuman-followup-v1/metrics/PROTOCOL.md)
- [단계별 AI 평가](experiments/nonhuman-followup-v1/agent-agreement/joined-stages.csv)
- [사람 평가 질문과 결과](experiments/nonhuman-followup-v1/HUMAN_EVALUATION.md)
- [사람 등급과 계산 지표의 비교](experiments/nonhuman-followup-v1/human-analysis/THRESHOLD_FREE.md)

기존 종합 결과의 원본은 생성 인물 6명이며 반복 편집은 7회입니다. 인물 3의 두 반복과 방법 간 공유 출력은 독립 표본으로 중복 계산하지 않습니다. 최종 사람 평가는 1명의 예비 결과입니다.

2026-09-08 추가 실험은 기존 P04 원본에서 세 조건을 각각 2회 실행한 6경로·14개 새 출력입니다. 사람 평가 없이 자동 지표를 계산했으며 기존 표본·사람 평가 결과에 합산하지 않습니다. 실행 전 고정한 주 분석과 결과 확인 후 추가한 피부 내부 진단을 각각 기록했습니다.

현재 결과의 1~8단계는 원래 호출 기록, 9~10단계는 위 수정 기록을 기준으로 합니다. 초기 임시 임계값을 검증된 감지 기준으로 주장하지 않습니다.

2026-09-09에는 순서38회·타 인물 재현16회·색/재질24회·무변경 연장6회, 총84개 새 출력을 추가했습니다. 앞선14개와 합쳐 저장된 새 출력은98개지만 독립 인물98명이나 사람 평가98건이 아닙니다. 기존 생성 인물 P04/P05/P06을 사용했습니다. 이 생성 캠페인 종료 당시에는 새 사람/독립AI 등급을 수집하지 않았으며, 이후 그중12개 최종 출력에 사람·별도AI 평가를 추가했습니다. 최신 결론은 위 자율 후속 종합과 각 보고서에 있으며 기존 발표 자료에는 이번84회가 아직 반영되지 않았습니다.

이 저장소는 발표 자료, 실험 기록·분석 코드·이미지, 공개 설문 소스를 포함합니다. 원본 사람 응답, 비공개 평가 매핑, 관리자 비밀번호와 로컬 DB는 제외합니다. 전체 실행 환경과 모든 과거 생성물의 배포본은 아닙니다. 원본 실행 기록의 절대 경로는 실행 당시의 경로이며, 이 저장소에서는 같은 상대 경로의 파일을 확인하면 됩니다. 기록에 등장하는 일부 미포함 생성물과 실행 의존성은 이 업로드만으로 재실행할 수 없습니다.

2026-09-09 후속 설문에서 실제24개 응답을 수집하여 별도 예비 분석을 추가했습니다. 앞선 자동 실험84회의 당시 사람 평가 미수집 기록은 유지하며, 이번12개 최종 출력의 새 평가와 구분합니다. 평가자는 이미 결과·가설을 전달받았으므로 독립 블라인드 검증으로 해석하지 않습니다.

## 로컬 편집기

- [원본 스튜디오 실행·사용 안내](local-studio/README.md): 대화 요구사항 갱신, 원본 기반 생성, 이미지·설정 버전 복원. 실제 모델을 연결한 로컬 시제품이며 인터넷 공개 서비스는 아닙니다.
