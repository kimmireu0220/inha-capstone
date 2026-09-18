# 논문 원고

[인하대 형식 PDF](manuscript.inha.pdf) · [Word](manuscript.inha.docx) · [원고](manuscript.ko.md)

저자 김미르·장윤석, 지도교수 안남혁. 순차 이미지 편집과 원본 기반 재생성의 얼굴 보존을 비교하고 웹 편집기에 적용한다.

본문은 자동 지표, AI 평가, 웹 편집기의 두 생성 방식 비교를 중심으로 구성한다. 작업 날짜, UI 변경 이력, 기능 검사 통과 건수와 단발 실행 시간은 본문에서 제외한다. 비교 방향이 다른 사례와 표본 범위는 유지한다. 전체 실험·개발 기록은 저장소에 보존한다.

- [본문 수치 검산](evidence.json)
- [사이트 입력 정책 비교](../experiments/studio-policy-v1/RESULTS.md)
- [인하대 형식 근거](INHA_FORMAT.md)

`build.py`, `build_inha.py`로 Word를 생성하고 PDF를 렌더링해 확인한다. `audit.py`는 본문 수치와 근거 파일을 검산한다. 인하대 형식은 6쪽, 읽기용 PDF는 7쪽이다.

번들 LibreOffice 렌더러는 `FONTCONFIG_FILE`을 해당 번들의 `LibreOfficeDev.app/Contents/Resources/fontconfig/fonts.conf`로 지정한다. 한글 누락 여부를 페이지 이미지에서 확인한다. 이번 읽기용 PDF는 번들 런타임 제거로 Microsoft Word의 로컬 PDF 내보내기를 사용했다.
