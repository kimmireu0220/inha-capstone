# 유지 보호 규칙의 적용 범위

2026-10-06. P 결과를 확인한 뒤 v1 코드를 읽고 만든 사후 진단이다. 고정 검증이나 실제 사용자 표현의 빈도 추정이 아니다. `audit_boundaries.py`의 15문항 중 보호 항목이 의도와 맞는 경우는 9개였다. 원문과 결과는 `boundary-audit.json`에 있다.

오류 6개는 `keep`·`leave`라는 동사만으로 이전 값을 보호하면 안 되는 경우다. `Keep the necklace off`와 `Leave the pin out of the image`는 제거 상태를 요구한다. `Keep the jacket green`은 이전 값이 아니라 특정 색을 요구할 수 있다. `Keep the pin hidden`은 가시성 변경이다. `Keep the shirt but make it blue`와 `Keep the necklace unchanged? No, remove it`는 뒤의 대명사 지시가 앞의 유지를 덮어쓴다. 현재 규칙은 이 차이를 해석하지 못한다.

따라서 P의 30→32/32를 범용 자연어 안전성으로 해석하지 않는다. 고정된 P 방법·점수와 이미 시작한 이미지 실험의 프롬프트는 수정하지 않는다. 이 진단의 실패도 연구 기록에 남긴다. 실사용 적용 전에는 명확한 불변 지시만 보호하고 애매한 문장에서는 개입하지 않는 범위 축소가 필요하다. 범위를 좁힌 새 구현의 효과는 기존 검증을 소급 수정하지 않고 별도로 검증해야 한다.
