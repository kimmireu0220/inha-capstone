# 논문 원고

[인하대 형식 PDF](manuscript.inha.pdf) · [Word](manuscript.inha.docx) · [원고](manuscript.ko.md)

저자 김미르·장윤석, 지도교수 안남혁. 순차 이미지 편집과 원본 기반 재생성의 얼굴 보존을 비교하고 웹 편집기에 적용한다.

본문은 자동 지표, AI 평가, 웹 편집기의 순차 생성·일괄 재생성 비교를 다룬다. 실험별 세부 기록은 저장소에 있다.

- [본문 수치 검산](evidence.json)
- [사이트 6인물·18쌍 입력 정책 비교](../experiments/studio-multiperson-v1/RESULTS.md)
- [사이트 P04 예비 비교](../experiments/studio-policy-v1/RESULTS.md)
- [인하대 형식 근거](INHA_FORMAT.md)

`build.py`, `build_inha.py`로 Word를 생성하고 PDF를 렌더링해 확인한다. `audit.py`는 본문 수치와 근거 파일을 검산한다. 인하대 형식은 6쪽, 읽기용 PDF는 9쪽이다.

번들 LibreOffice 렌더러는 `FONTCONFIG_FILE`을 해당 번들의 `LibreOfficeDev.app/Contents/Resources/fontconfig/fonts.conf`로 지정한다. 한글 누락 여부를 페이지 이미지에서 확인한다. 이번 두 PDF는 번들 LibreOffice로 렌더링했다.
