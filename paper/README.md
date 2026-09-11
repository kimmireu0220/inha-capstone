# 논문 원고 — 2026-09-11

현재 자료로 작성한 한국어 탐색적 실험 논문이다.

**최신 편집본: [인하대 사례 형식 PDF](manuscript.inha.pdf) · [Word](manuscript.inha.docx)**. 사용자 제공 안남혁 교수 지도 논문 5편의 형식을 적용했다. 저자는 김미르·장윤석, 지도교수는 안남혁으로 반영했다. 두 저자의 영문명만 미확인 빈칸이다. [형식 근거](INHA_FORMAT.md). 외부 제출이나 학술지 게재는 하지 않았다.

- [원고 Markdown](manuscript.ko.md)
- [편집 가능한 Word](manuscript.ko.docx)
- [읽기용 PDF](manuscript.ko.pdf)
- [본문 수치·근거 연결과 해시](evidence.json)
- [추가 사후 분석](../experiments/local-policy-robustness-v1/RESULTS.md)

새 실험은 저장된 FLUX8개에 대한 피부 ROI·위치 보정 분석이다. 사람 평가나 추가 이미지를 만들어 표본을 늘리지 않았다. 피부 원시 MAE가 반대 방향인 결과를 본문에 포함했다. 단일 평가자, 결과 노출, 공유 출력, 적은 인물·시드, 원래 생성기의 버전 불확실성을 명시했다.

## 제출 전 필요한 사항

저자·소속·교신저자, 목표 학회/학술지 형식, 지원 내역 및 실제 적용되는 연구 윤리·동의·자료 공개 사항은 확인 후 넣어야 한다. 현재 확인되지 않은 승인 사실이나 저자 정보를 만들어 넣지 않았다. 확증적 주장을 하려면 새로운 독립 인물과 사전 고정한 조건, 결과에 노출되지 않은 복수 사람 평가가 필요하다. 추가 반복만으로 기존 한 명 평가의 독립성 문제를 해결할 수 없다.

## 재생성

`make_figure.py`는 Matplotlib 환경, `build.py`는 python-docx 환경에서 실행한다. `audit.py`는 표6 전체와 로컬 최종 표, 핵심 후속 수치 및 AI 건수를 원자료와 대조하고 소스 해시를 기록한다. 모든 문장의 과학적 타당성을 자동 검증하는 스크립트는 아니다.

DOCX 렌더링은 documents 스킬의 bundled LibreOffice로 수행했다. 렌더러에 Noto Sans CJK KR 정적 글꼴이 필요하다(공식 notofonts/noto-cjk 저장소의 Sans/OTF/Korean/NotoSansCJKkr-Regular.otf). 이번 환경은 paper/qa/fonts의 글꼴 디렉터리를 지정하는 별도 Fontconfig 설정을 FONTCONFIG_FILE로 전달했다. 글꼴 바이너리는 저장소에 포함하지 않는다. PDF에는 한글 글꼴을 포함한다. QA 이미지는 로컬 검수용이다.

## 최종 검수

2026-09-11: bundled LibreOffice 렌더링의 10쪽 전체에서 한글 표시, 표·그림·참고문헌 배치를 확인했다. 표6의 40개 수치, 로컬 최종4행, 후속 핵심 수치와 AI 일치 건수 대조를 통과했다.
