# 논문 원고

본문과 발표 자료의 실험명은 ‘유지·삭제 규칙 비교 실험’, ‘새 대화에서의 재검증 실험’, ‘포즈·표정을 포함한 복합 요청 실험’으로 통일했다. 실험 기록의 S·T·C는 각각 이 세 실험을 가리키는 내부 식별자다. 이미지 평가의 설명·점수 불일치는 관찰 결과로 기술했다.

[논문 PDF](manuscript.inha.pdf) · [논문 Word](manuscript.inha.docx) · [한국어 원본](manuscript.ko.md) · [국문·영문 통합본](manuscript.inha.md)

제목은 「반복 인물 이미지 편집을 위한 유지 및 삭제 지시의 상태 갱신 제약」이다. 기존 규칙·이미지 분석과 복합 요청 검사에 표현 변화 검사와 지시 구절 정규화 검증을 추가했다. 초기 프롬프트 통합에서 취소된 조건이 남았던 문제와 현재 방법의 연결을 서론에서 설명한다. 8쪽의 표 7개·비교 그림 2개와 참고문헌을 검수했다. 최종 페이지 검수 기록은 `render-verification.json`에 저장한다.

추가 검증은 코드 고정 후 새 대화 네 개·요청 16개로 수행했다. 전체 상태 일치율은 기준 9/16, 기존 유지·삭제 10/16, 구절 정규화 16/16이었다. 정규화와 항목별 적용을 결합한 결과도 16/16으로, 이 검증의 추가 효과는 정규화로 설명된다. 기존 목표의 표현 변화 32개와 그 개발 재계산은 별도로 보고했다.

유지·삭제 규칙을 함께 적용했을 때 전체 상태 일치율은 S에서 27/32→29/32, T에서 28/32→29/32였다. S에서는 각 규칙을 단독으로 적용한 경우보다 두 규칙을 결합한 경우가 더 높았다. 연구용 합성 대화로 검사했으며 개선은 S3와 T7에서 나타났다. 이미지 평가에서는 판단 불가와 설명·점수 불일치가 나타났다. 이미지 결과는 개별 편집 사례와 평가 모델의 판정 차이를 중심으로 분석했다.

저자 김미르·장윤석, 지도교수 안남혁. 사용자 지시에 따라 영문 저자명은 나중에 추가한다. 사용자가 지정한 학과 게시판의 안남혁 지도교수 논문 2편을 형식 기준으로 삼아 A4·국영문 제목·전체 폭 초록·2단 본문·전체 폭 비교 그림 배치를 적용했다. [참고 양식 출처](format-references.json)에 원문 주소와 확인한 페이지를 기록했다. 참고 PDF는 서명과 학번이 있어 로컬 `reference-pdfs/`에만 보관하고 Git에서 제외한다. 참고 논문에서는 지면 구성과 서식만 적용했다.

- [S 구성요소 비교](../experiments/request-contract-v3/RESULTS.md)
- [구절 정규화의 새 대화 검증](../experiments/clause-normalization-v1/RESULTS.md)
- [동일 목표의 표현 변화 검사](../experiments/paraphrase-contract-v1/RESULTS.md)
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
