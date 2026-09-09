# 무료 공개 모델 로컬 실행 확인

이 문서는 두 모델을 각각 시험한 당시 기록이다. 이후 [로컬 편집기](../../local-studio/README.md)로 연결했고 [일괄/순차 비교](../local-policy-v1/RESULTS.md)를 추가했다.

2026-09-09. M1 iMac, 통합 메모리16GiB에서 유료 API 없이 이미지 편집과 한국어 요구사항 갱신을 각각 실제 실행했다. 전체 플랫폼이나 자동 연결 파이프라인을 구현한 것은 아니다.

| 항목 | 실제 관측 |
| --- | --- |
| 이미지 모델 | FLUX.2 Klein 4B, Runpod 4bit 양자화, MFLUX 0.19.1 |
| 입력 | 기존 생성 인물 P04 원본 |
| 출력 | 512×768, 4단계, seed42, 최초 결과1장 |
| 생성 루프 | 173.25초 (모델 메타데이터; 전체 요청 시간 아님) |
| 최초 프로세스 전체 | 278.88초 (약91초 모델 다운로드 및 로딩/전후처리 포함) |
| MLX 최대 메모리 | 약6.15GB; 프로세스 전체 메모리와 별개 |
| 프로세스 peak footprint | 약6.74GB |
| 언어 모델 | Qwen3 4B, MLX 4bit |
| 수정 지시문 결과 | 한국어 연속 요청3개 모두 기대 상태와 정확히 일치 |
| 텍스트 생성 시간 | 각2.90~3.01초, 캐시된 모델 로딩1.48초 별도 |
| 텍스트 MLX 최대 메모리 | 약2.71GB |

이미지 관찰: 남색 셔츠, 옅은 파란 배경, 보는 사람 기준 오른쪽 은색 원형 핀이 확인된다. 옷의 주름·질감과 얼굴 세부/명암에도 변화가 보인다. 독립 사람 평가나 얼굴 보존 성공 판정은 하지 않았다. 출력 해상도가 기존 실험보다 작으므로 기존 지표와 직접 비교하지 않았다. 첫 출력은 재시도나 선택 없이 보존했다.

언어 모델 관찰: 초기 영어 지시문에서 Qwen3 0.6B와4B 모두 세 문항의 스키마/내용 검사에 실패했다. 초기 코드와 원문 결과를 보존했다. 한국어 지시문, 명시적 값 표기, 다른 요청의 예시1개를 추가한 뒤4B가 셔츠 색 변경 → 배경/핀 추가 → 셔츠 색 재변경/핀 삭제/배경 유지의3문항을 통과했다. 본 결과를 보고 프롬프트를 조정한 개발용 확인이며 외부 검증 정확도3/3이 아니다. 형식 검사 실패 시 상태를 갱신하지 않는다. 뜻이 잘못된 유효 JSON은 별도 검사가 필요하다.

이번 이미지의 프롬프트는 고정한 연구 프롬프트를 사용했다. 언어 모델이 생성한 상태를 자동으로 이미지 생성에 연결해 시험한 결과는 아니다. 두 모델은 순차 실행했다. 모델 사용료는 발생하지 않았으며 장비/전력 비용은 별도다.

결론: 이 장비에서 로컬 시제품 개발은 가능하다. 이미지1장 계산에 약3분이므로 현재 설정을 다중 사용자 실시간 서비스 성능으로 간주할 수 없다. Qwen 이미지 모델은 실행하지 않았으며 작은 FLUX 모델로 대체했다. 기존 연구에서 관찰한 보존 이득이 이 모델에도 성립하는지는 별도 비교가 필요하다.

재실행:

```sh
experiments/local-open-model-v1/run-image.sh
.venv-local-prompt/bin/python experiments/local-open-model-v1/prompt_smoke.py --model mlx-community/Qwen3-4B-4bit --output prompt-4b-revised-results.json
```

환경: requirements-lock.txt / prompt-requirements-lock.txt. 입력·출력 해시와 모델 revision: manifest.json. 모델 가중치는 사용자 Hugging Face 캐시에 있고 Git에 포함하지 않는다. 원본/실험 환경은 변경하지 않았다.

[생성 이미지](output.png) · [최종 텍스트 결과](prompt-4b-revised-results.json) · [이미지 메타데이터](output.metadata.json)

공식/배포 문서:
- https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
- https://github.com/mflux-community/mflux/blob/main/src/mflux/models/flux2/README.md
- https://huggingface.co/Runpod/FLUX.2-klein-4B-mflux-4bit
- https://huggingface.co/mlx-community/Qwen3-4B-4bit
