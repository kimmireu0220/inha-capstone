# 논문 원고 — 2026-09-13

[인하대 사례 형식 PDF](manuscript.inha.pdf) · [Word](manuscript.inha.docx) · [원고](manuscript.ko.md)

저자 김미르·장윤석, 지도교수 안남혁. 외부 제출 전 초안이다. 사람 평가 자료와 그에 근거한 결론을 제거하고 자동 지표·AI 평가·웹 편집기 테스트 결과로 구성했다. 웹 편집기 기능 검사는 사용자 대상 사용성 연구가 아니다.

- [본문 수치 검산](evidence.json)
- [피부 영역 사후 분석](../experiments/local-policy-robustness-v1/RESULTS.md)
- [사이트 요청 회귀 검증](../local-studio/checks/RECHECK.md)
- [인하대 형식 근거](INHA_FORMAT.md)

`build.py`, `build_inha.py`로 Word를 생성하고 문서 렌더러로 PDF와 페이지 이미지를 검토한다. `audit.py`는 수치 전사와 근거 파일을 검산한다. 소수 합성 인물·시드의 탐색적 연구로서 일반화 성능이나 지각적 품질의 확증 결과가 아니다.

문체 원칙: 연구 대상·방법·결과를 직접 서술한다. 반복적인 부정·방어 문구를 피하고, 해석에 필요한 한계는 논의 절에 간결하게 정리한다. 실험 수치와 평가 범위는 정확히 유지한다.
