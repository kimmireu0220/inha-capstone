# 요청 해석 수정 후 확인

전체 상태를 모델이 다시 쓰는 대신 field/op/value 동작을 만들고 코드가 원래 상태에 적용한다. op는 set/reset/keep이며 reset은 원본 참조를 뜻하는 original을 저장한다. 알 수 없는 원본 색을 추측하지 않는다. 명확한 기본 색·배경·핀 표현은 도메인 해석기로 처리하고, 그 밖의 표현은 로컬 모델의 구조화된 동작으로 해석한다. 모델이 지정한 대상과 요청의 대상, 근거 문자열, 동작 형식을 확인하고 해결되지 않으면 전체 요청을 보류한다. 일부분만 적용하지 않는다.

수정된 실제 서버 API에서 이전 한국어14개·영어14개와 추가7개를 확인했다:35/35 통과. 모호한 요청과 미지원 요청은 needs_input을 반환하고 설정을 유지하며, 요청과 질문을 화면 이력에 저장하는지 함께 검사했다. 이는 알려진 사례에 대한 회귀/개발 검증이며 일반 자유 대화 정확도35/35를 뜻하지 않는다. 기본35개는 명시적 도메인 해석 경로다.

추가로 도메인 사전에 없는 'Change the background to a snowy mountain landscape.'를 실제 Qwen3 4B에 전달했다. background만 snowy mountain landscape로 갱신하고 셔츠/핀은 유지했으며 evidence를 요청 원문에서 확인했다. 결과: model-fallback-result.json. 모든 자유 표현의 의미를 자동으로 보증하는 검증기는 아니다.

기존 결과/실패는 보존: phrasing-results.json, english-results.json. 최신 결과: recheck-results.json. 재실행: `.venv-metrics/bin/python local-studio/checks/recheck.py` (서버 필요, 새 로컬 샘플 작업 생성, 이미지 생성 없음).
