# 논문 원고

[논문 PDF](manuscript.inha.pdf) · [논문 Word](manuscript.inha.docx) · [한국어 원본](manuscript.ko.md) · [국영문 통합본](manuscript.inha.md)

제목은 「반복 인물 이미지 편집에서 지시 검사를 이용한 상태 갱신」이다. 변경 사항을 한 번 추출한 뒤 복원·유지·삭제의 적용 대상과 현재 실행할 지시를 검사한다. 새 합성 요청 12개에서 같은 최초 응답을 단순 JSON으로 적용하면 Qwen3와 Llama 모두 3/12, 제안 방법은 모두 12/12였다. 추출·재검토와 같은 검사를 결합하면 각각 12/12와 4/12였다. 제안 방법 실행에는 요청당 모델 호출 한 번이 필요하다.

[96개 새 요청의 추가 검증](../experiments/extended-state-validation-v1/RESULTS.md). 추가 검증은 코드와 모델 설정을 유지한 새 합성 영어 대화 12개, 요청 96개이다. Qwen3의 첫 응답 단순 적용은 52/96, 한 번 추출과 지시 검사는 96/96이었다. Llama의 첫 응답 단순 적용은 27/96, 한 번 추출과 지시 검사는 93/96이었다. 모델별 점수를 따로 집계하고 대화 단위 정확도 차이의 95% 구간과 대응 검정을 계산했다. 원문 응답 384개와 모든 실패 사례를 보존했으며, 첫 응답 192개를 실제 실행 코드에 재생한 상태도 실험 결과와 일치했다.

초기 합성 인물 6명의 10단계 순차 출력 60장과 원본 기반 최종 출력 6장의 지표를 재계산했다. 위치 보정 MAE·SSIM·LPIPS는 최종 6쌍 모두 원본 기반 방식에 유리했다. 이 결과를 원본에 적용할 현재 조건을 정리하는 후속 연구의 출발점으로 연결했다.

후속 이미지 비교는 실제 인물 두 명·대화 세 개·세 입력 방식의 18장이다. 마지막 요청에서 전체 이력 평균 204.00토큰을 현재 조건 122.67토큰으로 줄였다. 7B AI 목표 충족 수는 전체 이력 34/36, 검사 전 24/36, 검사 후 36/36이었다. 얼굴 코사인·정렬 MAE·SSIM·LPIPS의 변화 방향은 달랐다. 두 AI 평가의 원문·형식 오류·실행 중단 기록을 보존했다.

구성요소별 검증도 보존했다. 복원 표현 검증 32개에서는 Qwen3 14/32에서 28/32, Llama 7/32에서 17/32로 증가했다. 실행 대상 검사 검증 16개에서는 Qwen3 9/16에서 16/16, Llama는 재검토의 초기 설정 오류로 0/16이었다. 세 검증은 서로 다른 새 요청을 사용하고 같은 요청을 두 모델에 각각 입력했다. 실제 비교 실험의 호출은 각각 128회, 64회, 48회다. 실패 응답과 개발 자료 재계산도 보존한다.

최신 실행 코드는 [한 번 추출하는 처리 절차](../local-studio/instruction_pipeline.py), 사용법은 [로컬 구현 안내](../local-studio/README.md)에 있다. 최종 코드 검사 1323개는 직접 구성한 상태 검사이고, 저장한 최초 응답 24개의 재생은 실행 코드와 실험 구현의 연결 검사다. 실제 모델 응답을 사용한 새 요청 검증과 구분한다.

서론은 연구 배경·문제·목적을 연결하고, 관련 연구는 자연어 이미지 편집·대화형 얼굴 편집·상태 갱신·응답 재검토의 네 절로 구성했다. 논의에서는 상태 정확도와 이미지 지표의 해석을 구분한다.

원고는 9쪽이며 표 10개, 비교 그림 2개, 참고문헌 12개를 포함한다. 실제 인물 사진의 편집 사례와 AI 평가 설명·점수 불일치를 함께 기술했다. 저자 김미르·장윤석, 지도교수 안남혁이며 영문 저자명은 사용자 지시에 따라 나중에 입력한다. 학과 게시판에서 지정한 졸업논문 두 편의 A4·국영문 제목·전체 폭 초록·2단 본문·전체 폭 비교 그림 배치를 따른다. [참고 양식 출처](format-references.json)에 확인한 원문을 기록했다. 서명과 학번이 포함된 참고 PDF는 로컬 reference-pdfs 폴더에 보관한다.

- [초기 얼굴 지표 재계산](initial-portrait-verification.json)
- [누적 요청과 현재 조건의 이미지 비교](../experiments/prompt-state-image-v1/RESULTS.md)
- [한 번 추출 방식의 새 요청 검증](../experiments/single-extraction-validation-v1/RESULTS.md)
- [실행 대상 검사의 새 요청 검증](../experiments/instruction-eligibility-validation-v1/RESULTS.md)
- [복원 표현 개선의 두 모델 검증](../experiments/operation-scope-validation-v1/RESULTS.md)
- [복원 표현 개발 자료 재계산](../experiments/operation-scope-v2/RESULTS.md)
- [실행 대상 검사 개발 자료 재계산](../experiments/instruction-eligibility-v1/RESULTS.md)
- [앞선 구성요소 검증과 연구 색인](../RESEARCH_INDEX.md)
- [본문 수치 대조 기록](evidence.json)
- [문서 렌더링 검수 기록](render-verification.json)
- [실행 코드 연결 검사](implementation-verification.json)
- [그림 원본 연결 기록](figures/figure-provenance.json)
- [온라인 Google Slides](../artifacts/README.md)

번들 Python으로 `paper/audit.py`와 `scripts/check_consistency.py`를 실행하면 수치·출처·산출물 해시를 검사한다. `paper/build_inha.py`로 문서를 만들고 `paper/render_inha.py --runtime-root <번들 dependencies 경로> --renderer <문서 스킬의 render_docx.py 경로> --output-dir .codex-build/paper-render`로 렌더링한다. 전체 페이지를 확인한 뒤 PDF와 검수 해시를 갱신한다. `layout.json`은 표 제목과 주요어를 관리한다.
