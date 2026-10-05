# 동작·값 분리의 선행 연구와 본 실험의 범위

2026-10-06에 확인한 SOM-DST는 상태 동작 예측과 선택한 항목의 값 생성을 분리한다. 따라서 이 분리 원리 자체를 본 연구의 새로운 알고리즘으로 주장하지 않는다.

- Sungdong Kim et al., Efficient Dialogue State Tracking by Selectively Overwriting Memory, ACL 2020, pp. 567–582. https://aclanthology.org/2020.acl-main.53/

현재 후보는 학습된 SOM-DST 모델의 재현이 아니라 고정 소형 언어 모델의 두 호출로 구현한 이미지 편집용 적용이다. 원본 복원(reset), 현재 상태 유지(keep), 삭제(remove), 새 값(set)을 구분하고 원본 참조 이미지로 최종 상태를 렌더링한다.

유용한 기여가 되려면 기존의 값 직접 추출·재검토 및 간단한 코드 대조보다 고정된 새 대화에서 정확해야 하며, 이미지 단계의 요청 반영까지 개선되어야 한다. 항목별 거부와 동작 분리를 제거한 대조, 호출·시간·실패 비용도 분리해야 한다. 선행 원리의 이름만 바꾸거나 개발 대화의 점수를 새 방법의 일반화 근거로 내세우지 않는다.

## 직접 관련된 얼굴 편집 선행 연구

ChatEdit는 대화 이력에서 현재 요청을 추적하고 직전 출력 대신 최초 이미지를 편집하는 프레임워크를 이미 제안했다. 따라서 원본 재사용과 대화 추적의 결합 또한 최초 제안이라고 주장할 수 없다. 현재 후보가 검증된다면 제한된 실행 예산에서 취소·유지·원본 복원의 실행 오류를 줄이는 구체적 구현과 검증된 효과에 기여 범위를 한정해야 한다.

- Xing Cui et al., ChatEdit: Towards Multi-turn Interactive Facial Image Editing via Dialogue, EMNLP 2023, pp. 14567–14583. https://aclanthology.org/2023.emnlp-main.899/

2026년의 IMAGAgent와 AnchorEdit도 관련 후보 문헌으로 확인했다. 현재는 초록·메타데이터를 확인한 수준이며 정밀 비교나 우월성 주장의 근거로 쓰기 전에 전체 방법·평가 조건을 읽어야 한다.

- IMAGAgent: Orchestrating Multi-Turn Image Editing via Constraint-Aware Planning and Reflection. https://arxiv.org/abs/2603.29602
- AnchorEdit: Maintaining Temporal Consistency in Multi-turn Image Editing via Causal Memory. https://arxiv.org/abs/2606.11751
