import json
from pathlib import Path
R=Path(__file__).resolve().parent;d=json.loads((R/'results.json').read_text())
lines=[]
for x in d['rows']:
 if x['arm']=='batch' or x['stage']==3:
  v=x['metrics'];lines.append(f"| {x['seed']} | {x['arm']} | {v['mae']:.6f} | {v['ssim']:.6f} | {v['lpips']:.6f} |")
times=[]
for seed,v in d['path_seconds'].items():times.append(f"| {seed} | {v['batch']:.1f} | {v['sequential']:.1f} | {v['sequential']/v['batch']:.2f} |")
means=d['means'];drop=(1-means['batch']['lpips']/means['sequential']['lpips'])*100
(R/'RESULTS.md').write_text(f'''# FLUX.2 Klein 4B 일괄·순차 비교

2026-09-09. 같은 생성 인물 P04, 같은512×768 원본, 시드42/314에서 일괄1회와 셔츠→배경→핀 순차3회를 비교했다. 새 출력 8개를 생성했다. 모든 호출에서 최신 요구 전체를 전달했다. 순차 최종과 일괄 프롬프트는 정확히 같다. 양쪽 모두 원본을 같은 방식으로 축소한 뒤 시작했다.

## 고정 얼굴 영역의 원본 차이

MAE·LPIPS는 낮을수록, SSIM은 높을수록 원본에 가깝다.

| 시드 | 방법 | MAE ↓ | SSIM ↑ | LPIPS ↓ |
| --- | --- | --- | --- | --- |
{chr(10).join(lines)}

일괄 평균: MAE {means['batch']['mae']:.6f}, SSIM {means['batch']['ssim']:.6f}, LPIPS {means['batch']['lpips']:.6f}. 순차 평균: MAE {means['sequential']['mae']:.6f}, SSIM {means['sequential']['ssim']:.6f}, LPIPS {means['sequential']['lpips']:.6f}.

일괄의 평균 얼굴 LPIPS는 순차 대비 {drop:.1f}% 낮다.

## 전체 편집 실행 시간

모델 다운로드는 캐시되어 있다. 각 호출은 별도 프로세스이므로 아래 시간은 모델 로딩과 전후처리를 포함한다. 순차는3회 합계, 일괄은1회다.

| 시드 | 일괄 초 | 순차 전체 초 | 순차/일괄 |
| --- | --- | --- | --- |
{chr(10).join(times)}

## 최종 이미지의 실행자 관찰

네 최종 결과 모두 남색 셔츠·옅은 파란 배경·보는 사람 기준 오른쪽의 은색 원형 핀이 보였다. 두 시드의 순차 결과에서는 일괄보다 이마·볼의 질감/잔선 대비와 얼굴·목의 명암 변화가 더 눈에 띄었다. 일괄 결과에도 원본 얼굴과 옷의 세부 차이가 남았다. 이 내용은 비블라인드 실행자 관찰이다. [관찰 기록](visual-observations.json).

두 시드 모두 MAE·SSIM·LPIPS가 일괄에 유리했다.

## 범위와 재현

M1·16GiB, MFLUX0.19.1, Runpod FLUX.2 Klein4B 4bit, four steps, low-RAM. 한 인물·두 시드의 예비 비교다. 두 방식은 생성 횟수가 달라 난수 경로도 달라질 수 있다. 원본 ROI를 절반 크기 [176,44,336,224]로 고정해 자동 지표를 계산했다.

입출력 해시, 최종 프롬프트 일치,8개 고유 출력, 원본 대조 MAE0/SSIM1/LPIPS0을 검증했다. 원문 호출·중간 결과는 generated에 보존했다. [검증](verification.json), [전체 지표](results.json), [사전 계획](PROTOCOL.md).

재현: `.venv-metrics/bin/python experiments/local-policy-v1/analyze.py` 다음 `report.py`. 생성은 `run.py`로 분리되며 성공한 기존 호출은 다시 생성하지 않는다. `prepare.py`는 최초 계획 작성용이므로 완료한 실험에서 재실행하지 않는다.

[시드42 비교](comparison-42.png) · [시드314 비교](comparison-314.png)
''')
