# 논문 원고

[논문 PDF](manuscript.inha.pdf) · [논문 Word](manuscript.inha.docx) · [한국어 원본](manuscript.ko.md) · [국문·영문 통합본](manuscript.inha.md)

완료된 U1–U4의 96장 비교와 추가 48개 조건의 두 AI 평가·얼굴 측정을 반영했다. 추가 대조는 목표 127/288·142/288, ArcFace 0.846995, 고유 RGB 이미지 36종이다. 국문·영문 통합본과 Word/PDF를 재생성했고 7쪽 전체의 한글, 표, 그림, 결론과 참고문헌을 시각 확인했다. 문서 검증 기록에는 최종 산출물 해시를 남겼다.

저자 김미르·장윤석, 지도교수 안남혁. 영문 저자명은 확인되지 않아 원고에서 생략했다. 학교의 공식 빈 양식은 확보하지 못했으므로 현재 Word/PDF는 검토용 A4 단일 단 원고다. 제출 전 학과 양식 및 영문 저자명을 확인해야 한다.

기초 비교는 합성 인물 6명·최종 18쌍의 순차 편집/원본 기반 재생성과 실제 인물 6명·편집 이력 3종·2시드·세 프롬프트 방법의 최종 요구 종합 108장이다. 실제 인물 2명의 정책 비교는 별도 예비 결과다. 서로 다른 실험의 수치를 합산하지 않는다.

후속 비교는 같은 실제 인물 6명에 새 대화 4종·두 시드·두 방법을 적용한 96장이다. 자동 상태 갱신의 1차 AI 목표 충족과 얼굴 유사도는 자연어 종합보다 높지만 대화별 실패와 평가자 의존성이 있다. 전체 대화에서 구조화된 상태를 추출하는 추가 대조는 같은 대화의 후속 진단이다.

- [합성 인물 입력 정책 원자료](../experiments/studio-multiperson-v1/RESULTS.md)
- [실제 인물 최종 요구 종합 원자료](../experiments/prompt-synthesis-expanded-v1/RESULTS.md)
- [자동 상태 갱신의 완료된 집계](../experiments/state-tracking-v2/summary.json)
- [추가 대조의 사전 명세](../experiments/state-format-control-v1/PROTOCOL.md)
- [실제 인물 정책 예비 비교](../experiments/real-people-v1/RESULTS.md)
- [본문 수치 대조 기록](evidence.json)
- [문서 렌더링 검증 기록](render-verification.json)

재생성: 번들 Python으로 `python paper/audit.py`와 `python paper/build_inha.py`를 실행한다. 초안 검토는 `build_inha.py --output-dir .codex-build/paper-draft`로 최종 산출물을 덮어쓰지 않고 할 수 있다.

`python paper/render_inha.py --runtime-root <의존성 로더가 반환한 dependencies 경로> --renderer <문서 스킬의 render_docx.py 경로> --output-dir .codex-build/paper-render`로 번들 렌더러를 실행한다. 이 보조 스크립트는 설치된 사용자·시스템 글꼴을 Fontconfig에 명시해 임시 렌더링 환경에서 한글이 사라지는 문제를 방지한다. 글꼴 경로가 다른 환경에서는 `--font-dir`를 지정한다. 전체 페이지의 한글과 표·그림 배치를 눈으로 확인한 뒤 PDF를 교체한다. 원본 이미지와 생성 기록은 독립 검증을 위해 실험 폴더에 보존한다.
