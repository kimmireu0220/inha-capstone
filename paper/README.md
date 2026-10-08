# 논문 원고

[논문 PDF](manuscript.inha.pdf) · [논문 Word](manuscript.inha.docx) · [한국어 원본](manuscript.ko.md) · [국문·영문 통합본](manuscript.inha.md)

제목은 「반복 인물 이미지 편집을 위한 유지 및 삭제 지시의 상태 갱신 제약」이다. S·T 검증과 P·S 이미지 분석, 사후 7B 평가에 포즈·표정 확장 C와 짧은 동작 대조를 추가했다. 6쪽의 표 6개·비교 그림 2개와 참고문헌을 검수했다. 최종 페이지 검수 기록은 `render-verification.json`에 저장한다.

유지·삭제 규칙을 함께 적용했을 때 정확한 턴은 S에서 27/32→29/32, T에서 28/32→29/32였다. S에서는 각 규칙을 단독으로 적용한 경우보다 두 규칙을 결합한 경우가 더 높았다. 연구용 합성 대화로 검사했으며 개선은 S3와 T7에서 나타났다. 이미지 평가는 판단 불가와 설명·점수 불일치가 있어 전반적인 품질 향상 여부를 판단하기 어렵다.

저자 김미르·장윤석, 지도교수 안남혁. 사용자 지시에 따라 영문 저자명은 나중에 추가한다. 사용자가 지정한 학과 게시판의 안남혁 지도교수 논문 2편을 형식 기준으로 삼아 A4·국영문 제목·전체 폭 초록·2단 본문·전체 폭 비교 그림 배치를 적용했다. [참고 양식 출처](format-references.json)에 원문 주소와 확인한 페이지를 기록했다. 참고 PDF는 서명과 학번이 있어 로컬 `reference-pdfs/`에만 보관하고 Git에서 제외한다. 서명·저작권 양도서와 타 논문의 본문은 복사하지 않았다.

- [S 구성요소 비교](../experiments/request-contract-v3/RESULTS.md)
- [T 추가 검증](../experiments/isolated-contract-v1/RESULTS.md)
- [C 포즈·표정 확장과 삭제·복원 대조](../experiments/compound-edit-v1/RESULTS.md)
- [S 이미지 해석](../experiments/contract-image-v3/INTERPRETATION.md)
- [7B 사후 평가 해석](../experiments/contract-image-review-v1/INTERPRETATION.md)
- [P 이미지 해석](../experiments/keep-image-v1/INTERPRETATION.md)
- [개발 실패와 앞선 연구 색인](../RESEARCH_INDEX.md)
- [본문 수치 대조 기록](evidence.json)
- [문서 렌더링 검증 기록](render-verification.json)
- [그림의 원본 출력 연결 기록](figures/figure-provenance.json)

`python paper/audit.py`로 본문을 검산하고 번들 Python으로 `python paper/build_inha.py`를 실행한다. `layout.json`은 표 제목과 키워드를 관리한다. 별도 초안은 `--source-dir <초안 폴더> --output-dir <산출 폴더>`로 검토한다. 그림은 `paper/make_contract_figure.py`로 재생성한다.

`python paper/render_inha.py --runtime-root <번들 dependencies 경로> --renderer <문서 스킬의 render_docx.py 경로> --output-dir .codex-build/paper-render`로 렌더링한다. 이 보조 스크립트는 한글 글꼴 경로를 Fontconfig에 명시한다. 전체 페이지를 눈으로 확인한 뒤 PDF와 검증 해시를 갱신한다.

앞선 비교 중심 원고는 Git 이력에 남아 있다. [온라인 발표 자료](../artifacts/README.md)는 최신 방법 논문과 일치하는 10장이며 수치·이미지 출처·발표자 노트와 전체 배치를 검수했다.
