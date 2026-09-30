# 논문 원고

[최종 PDF](manuscript.inha.pdf) · [편집 가능한 Word](manuscript.inha.docx) · [한국어 원본](manuscript.ko.md) · [국문·영문 초록 포함 Markdown](manuscript.inha.md)

저자 김미르·장윤석, 지도교수 안남혁. 영문 저자명은 확인되지 않아 원고에서 생략했다. 학교의 공식 빈 양식은 확보하지 못했으므로 현재 Word/PDF는 검토용 A4 단일 단 원고다. 제출 전 학과 양식 및 영문 저자명을 확인해야 한다.

논문은 두 비교를 분리해 보고한다. 합성 인물 6명·최종 18쌍의 순차 편집/원본 기반 재생성, 실제 인물 6명·편집 이력 3종·2시드·세 프롬프트 방법의 최종 요구 종합 108장이다. 실제 인물 2명의 정책 비교는 별도 예비 결과다. 두 실험의 수치를 합산하지 않는다.

- [합성 인물 입력 정책 원자료](../experiments/studio-multiperson-v1/RESULTS.md)
- [실제 인물 최종 요구 종합 원자료](../experiments/prompt-synthesis-expanded-v1/RESULTS.md)
- [실제 인물 정책 예비 비교](../experiments/real-people-v1/RESULTS.md)
- [본문 수치 대조 기록](evidence.json)
- [문서 렌더링 검증 기록](render-verification.json)

재생성: 번들 Python으로 `python paper/audit.py`와 `python paper/build_inha.py`를 실행하고, 번들 `render_docx.py`로 Word를 PDF와 페이지 이미지로 렌더링한다. 한글 글꼴이 렌더러의 임시 HOME에서 검색되는지 확인해야 한다. 전체 페이지를 눈으로 확인한 뒤 PDF를 교체한다. 원본 이미지와 생성 기록은 독립 검증을 위해 실험 폴더에 보존한다.
