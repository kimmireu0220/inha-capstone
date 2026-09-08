# 익명 최종 이미지의 요구 반영 관찰

허용 자료는 이 폴더의 INSTRUCTIONS.md, items.json, PNG뿐이다. 프로젝트의 다른 폴더, 해독표, 방법·단계 정보, 지표, 다른 평가자의 답안은 읽지 않는다. 각 후보와 연결된 원본을 view_image로 직접 확인한다. 같은 원본은 한 번 확인하고 재사용할 수 있다. 작은 장신구가 불확실하면 원본 해상도에서 다시 확인하며 보이지 않는 내용을 추측하지 않는다.

각 조건을 독립적으로 0 미충족 / 1 일부 충족 / 2 충족 / null 판단 어려움으로 평가한다. 조건별 한국어 근거를 짧게 붙인다.

| 키 | 요구 |
|---|---|
| earrings | 양쪽 귀에 작은 은색 링 귀걸이 |
| necklace | 가는 은색 목걸이, 작은 은색 물방울 모양 펜던트 하나 |
| pin | 인물 왼쪽 가슴, 즉 이미지를 보는 사람 기준 오른쪽 가슴에 코발트 파란색 원형 핀 정확히 하나 |
| blazer | 차콜 회색 재킷 |
| shirt | 버건디색 라운드넥 셔츠 |
| background | 나무 책장이 있는 조용한 도서관 배경. 실제 소음은 판단하지 않으며 차분한 도서관 장면으로 평가 |
| no_text | 글자·로고·워터마크 없음. 책등의 판독 가능한 글자도 포함. 불명확한 선이나 모양을 글자로 추측하지 않음 |
| lighting | 원본의 인물 조명 유지. 주광 방향·그림자 분포·전체 밝기/색조를 비교. 픽셀 동일성을 요구하지 않고 배경 밝기 자체의 차이는 제외 |

얼굴에 인위적 무늬가 있다는 이유만으로 옷·장신구·배경 조건을 낮추지 않는다. 조건이 맞다는 이유만으로 전체가 자연스럽다고 평가하지 않는다. 별도 overall_artificiality는 시각적 부자연스러움 0 없음 / 1 약함 / 2 뚜렷함 / 3 심함 / null 판단 어려움과 근거를 기록한다. 원본의 자연 주름은 인위적 열화가 아니다. 이미지 간 동일인 여부를 판별하지 않는다.

응답 JSON 형식:

```json
{
  "reviewer": "배정된 이름",
  "human": false,
  "type": "AI_assistant_visual_observation",
  "blinded_to": ["method", "stage", "metrics", "other_ratings"],
  "items": [{
    "id": "items.json의 ID",
    "criteria": {
      "earrings": {"score": 2, "reason": "관찰 근거"},
      "necklace": {"score": null, "reason": "관찰 근거"},
      "pin": {"score": 2, "reason": "관찰 근거"},
      "blazer": {"score": 2, "reason": "관찰 근거"},
      "shirt": {"score": 2, "reason": "관찰 근거"},
      "background": {"score": 2, "reason": "관찰 근거"},
      "no_text": {"score": 2, "reason": "관찰 근거"},
      "lighting": {"score": 1, "reason": "관찰 근거"}
    },
    "overall_artificiality": {"severity": 1, "reason": "관찰 근거"},
    "confidence": "high/medium/low"
  }],
  "viewed_files": ["실제로 확인한 PNG 목록"]
}
```

예시의 숫자는 형식 설명용으로 복사할 답이 아니다. 모든 후보를 독립적으로 평가하고 결과 파일은 배정받은 경로에만 apply_patch로 작성한다. 다른 평가자와 의논하거나 합의 답안을 만들지 않는다.
