# 인물 이미지 반복 편집 연구

장신구·의상·배경을 반복해서 수정할 때 생기는 얼굴 변화와, 최초 원본에 현재 요구사항을 한 번에 적용해 다시 생성하는 방법을 비교한 예비 실험입니다.

**최신 범위·수치·구현 상태: [현재 상태](CURRENT_STATUS.md)**

## 논문 원고

- [현재 실험 기반 한국어 논문: Markdown·Word·PDF](paper/README.md)
- [로컬 피부 영역·위치 보정 사후 분석](experiments/local-policy-robustness-v1/RESULTS.md)

## 발표 자료

- [기존 Google Slides — 종합설계_9월](https://docs.google.com/presentation/d/1UjTZ-HbxiGbb3QH2mnUWeFUk-_o9POx3Ay134fZ9qb8/edit)
- [발표 자료 위치와 수정 기록](artifacts/README.md)
- [실제 프롬프트와 단계별 상세 수치](artifacts/실험_프롬프트와_상세수치.md)
- [연구 질문과 현재 범위](RESEARCH_DESIGN.md)

## 실험 기록

- [웹 편집기 다인물 확대 비교: 6명·3시드·72장](experiments/studio-multiperson-v1/README.md)

- [웹 편집기 순차 생성·일괄 재생성 비교: 두 시드·8장](experiments/studio-policy-v1/RESULTS.md)

- [무료 로컬 FLUX 모델의 일괄·순차 비교: 두 시드·8장](experiments/local-policy-v1/RESULTS.md)

- [공개 모델의 M1 로컬 실행 확인: 이미지 편집·한국어 요구사항 갱신](experiments/local-open-model-v1/RESULTS.md)

- [후속12개 별도 AI 평가와 자동 지표 연결](experiments/followup-ai-v1/RESULTS.md)


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

기존 종합 결과의 원본은 생성 인물 6명이며 반복 편집은 7회입니다. 인물 3의 두 반복과 방법 간 공유 출력은 독립 표본으로 중복 계산하지 않습니다.

이 저장소는 논문, Google Slides 링크, 실험 기록·분석 코드·이미지와 로컬 편집기 소스를 포함합니다. 실행 환경·모델 가중치는 별도로 준비해야 합니다.

## 로컬 편집기

- [원본 스튜디오 실행·사용 안내](local-studio/README.md): 대화 요구사항 갱신, 순차 생성·일괄 재생성 선택, 두 버전 비교, 시드 저장, 이미지·설정 버전 복원. 실제 모델을 연결한 로컬 시제품이며 인터넷 공개 서비스는 아닙니다.
