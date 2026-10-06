# 논문 원고

[논문 PDF](manuscript.inha.pdf) · [논문 Word](manuscript.inha.docx) · [한국어 원본](manuscript.ko.md) · [국문·영문 통합본](manuscript.inha.md)

제목은 「반복 인물 이미지 편집을 위한 유지 및 삭제 지시의 상태 갱신 제약」이다. 최신 S·T 검증과 P·S 이미지 분석, 전체 입력의 사후 7B 평가를 반영했다. 6쪽의 표 5개·비교 그림 2개와 참고문헌을 검수했다.

명시적 유지·삭제 검사로 S 정확 턴은 27/32→29/32, T는 28/32→29/32였다. S에서는 유지와 삭제를 결합해야 각각의 단독 구성요소보다 높았다. 다만 개발자가 구성한 제한 문형 검사이고 개선은 소수 대화에 집중됐다. 이미지 점수의 판단 불가와 설명 모순 때문에 전반적인 이미지 품질 개선을 주장하지 않는다.

저자 김미르·장윤석, 지도교수 안남혁. 영문 저자명은 확인되지 않아 생략했다. 학교 공식 빈 양식을 확보하지 못했으므로 Word/PDF는 사례 배치를 참고한 A4 단일 단 검토 원고다. 제출 전 학과 양식 및 영문 저자명을 확인해야 한다.

- [S 구성요소 비교](../experiments/request-contract-v3/RESULTS.md)
- [T 추가 검증](../experiments/isolated-contract-v1/RESULTS.md)
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
