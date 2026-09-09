"""Render descriptive tables from saved results without regenerating images."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAMES = {'batch': '한 번에 편집', 'sequential': '세 번 나눠 편집', 'no_change': '무변경 3회 재생성'}
ARMS = tuple(NAMES)
KEYS = ('mae', 'ssim', 'lpips')


def main():
    result = json.loads((ROOT / 'results.json').read_text())
    skin = json.loads((ROOT / 'skin-results.json').read_text())
    final = result['final']

    def table(headers, rows):
        return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                          '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                         ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows])

    def interval(v):
        return f"{v['mean']:.6f} [{v['min']:.6f}, {v['max']:.6f}]"

    primary = table(['조건', 'MAE ↓', 'SSIM ↑', 'LPIPS ↓'],
                    [[NAMES[a], *[interval(final[a]['by_mode']['fixed'][k]) for k in KEYS]] for a in ARMS])
    repeat_rows = [r for r in result['rows'] if r['stage'] == (1 if r['arm'] == 'batch' else 3)]
    repeats = table(['조건', '반복', 'MAE', 'SSIM', 'LPIPS'],
                    [[NAMES[r['arm']], r['repeat'], *[f"{r['original']['face']['fixed'][k]:.6f}" for k in KEYS]]
                     for r in sorted(repeat_rows, key=lambda r: (ARMS.index(r['arm']), r['repeat']))])
    aligned = table(['조건', 'MAE ↓', 'SSIM ↑', 'LPIPS ↓'],
                    [[NAMES[a], *[interval(final[a]['by_mode']['3'][k]) for k in KEYS]] for a in ARMS])
    trajectories = []
    for a in ARMS:
        for stage in range(1, (1 if a == 'batch' else 3) + 1):
            rows = [r for r in result['rows'] if r['arm'] == a and r['stage'] == stage]
            trajectories.append([NAMES[a], stage, *[f"{sum(r[b]['face']['fixed'][k] for r in rows)/2:.6f}"
                                                    for b in ('original', 'previous') for k in KEYS]])
    stages = table(['조건', '단계', '원본 MAE', '원본 SSIM', '원본 LPIPS', '직전 MAE', '직전 SSIM', '직전 LPIPS'], trajectories)
    skin_table = table(['조건', '피부 MAE ↓', '피부 SSIM ↑', '피부 고주파 MAE ↓'],
                       [[NAMES[a], *[interval(skin['final'][a]['fixed'][k]) for k in ('mae', 'ssim', 'highpass_mae')]] for a in ARMS])
    reduction = 100 * (1 - final['batch']['by_mode']['fixed']['lpips']['mean'] / final['sequential']['by_mode']['fixed']['lpips']['mean'])
    content = f'''# 편집 분할·무변경 재생성 비교 결과

2026-09-08. **새 이미지 생성 14회와 자동 지표 분석을 완료했다.** 생성 인물 P04 한 명에서 같은 최종 요구를 한 번에 적용한 2경로, 세 번에 나눠 적용한 2경로, 변경 없이 재생성만 반복한 2경로를 실행했다. 사람 평가와 독립 AI 평가는 수집하지 않았다.

이번 두 반복에서는 한 번에 편집한 쪽이 세 번 나눠 편집한 쪽보다 원본 얼굴 ROI에 가까웠다. 무변경 재생성도 원본과의 차이가 누적됐다. 이 결과는 **동일 인물의 편집 조건을 바꾸는 것 자체가 유용한 비교 축**임을 보여주는 예비 관측이며, 피부 열화의 정답이나 일반적인 우열을 확정하지 않는다.

## 실행 조건과 분석 단위

- [실행 전 고정 계획](PROTOCOL.md), [정확한 프롬프트·입력·출력](plan.json).
- batch: 남색 셔츠·옅은 파란 배경·보는 사람 기준 오른쪽 가슴의 작은 은색 원형 핀을 한 번에 적용. 1회 × 2경로.
- sequential: 셔츠 색 → 배경 색 → 핀 추가. 현재까지의 모든 요구를 매번 함께 제공하고, 직전 출력을 다음 입력으로 사용. 3회 × 2경로.
- no_change: 변경하지 말라는 요청으로 직전 출력을 재생성. 3회 × 2경로. 요구 충족의 비교군이 아닌 재생성 자체의 진단 대조군.
- 도구: 내장 `image_gen.imagegen`. 정확한 내부 모델 버전·생성 시드는 제공되지 않았다. 별도의 시드가 통제된 독립 표본이라고 부르지 않는다.
- 14/14 호출 성공, 재시도·최선 출력 선택 0회. 전부 1024×1536. 파일·디코딩 픽셀 기준 모두 14개의 서로 다른 출력이다.
- 표본은 인물 1명, 조건당 2경로다. 14단계 또는 피부 영역 3개를 독립 인물 표본처럼 세지 않는다. 반복 번호가 같아도 조건 간 공통 난수를 사용한 짝 실험은 아니다.
- 생성 담당자는 편집 조건의 최종 4장에서 요청한 셔츠 색·배경 색·핀의 존재를 확인했다. 이 비블라인드 실행 점검은 정량적 요구 충족 점수나 독립 평가가 아니다. 유지 요청 전체의 성공을 뜻하지 않는다.

## 주 분석: 원본 대비 고정 얼굴 ROI

기존 P04 ROI `[352,88,672,448]`와 RGB MAE·SSIM·LPIPS AlexNet v0.1 구현 및 가중치를 그대로 사용했다. MAE·LPIPS는 낮을수록, SSIM은 높을수록 원본에 가깝다. 값은 평균 [최솟값, 최댓값]이다. 범위는 2회 관측의 범위이며 신뢰구간이 아니다.

{primary}

두 반복 각각에서도 batch의 MAE·LPIPS가 더 낮고 SSIM이 더 높았다. batch의 평균 LPIPS는 sequential보다 {reduction:.1f}% 낮았다. **이를 “피부 열화가 {reduction:.1f}% 감소했다”로 해석하면 안 된다.** ROI는 피부만의 마스크가 아니며 머리·경계·배경 일부를 포함한다.

{repeats}

## 단계별 원본 거리와 직전 입력 거리

각 값은 조건 내 두 경로의 평균이다. 두 종류의 거리를 더하거나 빼서 순수 열화량으로 만들지 않는다.

{stages}

무변경 조건의 원본 대비 평균 LPIPS는 0.020250 → 0.041245 → 0.062738로 증가했다. 두 반복 각각에서 MAE·LPIPS가 증가하고 SSIM은 감소했다. 반면 직전 입력 대비 평균 LPIPS는 0.020250 → 0.017633 → 0.015616으로 작아졌다. **직전 이미지와 비슷해지는 것과 최초 원본을 유지하는 것은 다를 수 있다.**

순차 편집에서는 배경을 바꾼 2단계에서 원본 대비 MAE·LPIPS 차이가 가장 크게 늘었다. 3단계에서는 MAE가 조금 감소해도 LPIPS는 증가하고 SSIM은 감소했다. 따라서 모든 지표가 단계마다 같은 방향으로 움직인다고 주장하지 않는다. 편집 종류와 단계 위치가 고정돼 있으므로 이 결과만으로 배경 편집의 인과효과를 분리할 수 없다.

![원본 대비 지표 변화](trajectories.png)

[벡터 PDF](trajectories.pdf) · [SVG](trajectories.svg) · [모든 원본/직전 지표 CSV](metrics.csv)

## 이동 보정 민감도

기존 NCC 정수 이동 보정의 sigma3 보조 결과다. ±64픽셀 검색 경계에 닿은 경우는 없었고, sigma1/3/6 간 추정 이동 차이는 최대 1픽셀이었다. 이 보정은 회전·변형·밝기 변화의 교정이 아니다.

{aligned}

batch와 sequential의 평균 우열은 고정 ROI와 sigma1/3/6 모두에서 유지됐다. 정합은 NCC를 최적화하므로 모든 지표를 반드시 개선하지 않는다. sigma1/6의 모든 값도 [원시 결과](results.json)와 CSV에 보존했다.

## 결과 확인 후 추가한 피부 내부 진단

배경 변경이 얼굴 사각형 지표에 섞이는 문제를 점검하려고, 주 결과를 본 뒤 [추가 분석 계획](POSTHOC_SKIN.md)을 기록했다. 기존 이마·양 볼 영역 및 수식을 그대로 재사용했다. 사전 주 분석을 교체하지 않는다.

{skin_table}

피부 세 영역의 가중 평균에서도 batch는 sequential보다 MAE·고주파 MAE가 낮고 SSIM이 높았다. 이 평균 방향은 고정 및 sigma1/3/6 모두에서 유지됐다. 다만 얼굴 사각형 MAE에서는 no_change가 batch보다 낮은 반면, 피부 내부 MAE에서는 batch가 더 낮았다. **영역 선택에 따라 조건 순위가 바뀔 수 있으므로 사각형 지표를 피부 열화 점수로 동일시하지 않는다.**

[피부 전체 수치](skin-results.json) · [피부 영역별 CSV](skin-metrics.csv). 세 작은 영역의 변화만으로 얼굴 전체의 자연스러움이나 동일성을 판정하지 않는다.

## 검증과 재현

- 사전 계획 해시, 원본 해시, 14개 출력·호출 로그, 단계 입력 연결과 시간 순서, 출력 크기, 중복 여부를 검사했다.
- 원본과 원본을 비교한 제어에서 MAE=0, SSIM=1, LPIPS=0을 확인했다.
- 원본·직전 기준 28쌍의 MAE·SSIM을 별도 계산 경로로 재계산했다. 최대 오차는 MAE 2.50e-8 미만, SSIM 0이다.
- 주 분석 CSV 112행을 JSON과 대조했다. LPIPS 전체 state-dict와 선형 가중치 해시는 기존 분석과 같다.
- [검증 결과](verification.json), [실행 환경·소스 해시](manifest.json), [실행 로그](analysis.log), [호출별 원문과 출력](generated/).

저장소 루트에서 기존 `.venv-metrics` 환경으로 실행한다. 아래 명령은 저장된 이미지 분석만 수행하며 새 이미지를 생성하지 않는다.

```sh
.venv-metrics/bin/python experiments/edit-decomposition-v1/analyze.py
.venv-metrics/bin/python experiments/edit-decomposition-v1/skin_and_verify.py
.venv-metrics/bin/python experiments/edit-decomposition-v1/plot.py
.venv-metrics/bin/python experiments/edit-decomposition-v1/report.py
```

절대 경로는 당시 호출의 provenance로 보존했고, 분석 코드는 현 checkout의 같은 저장소 상대 경로를 해석한다. 생성 모델 버전과 시드가 노출되지 않아 생성 출력의 동일 재현은 보장할 수 없다.

## 이번 실험이 말할 수 있는 범위

동일 인물에서도 편집을 나누는 방식과 무변경 반복에 따라 자동 지표가 달랐다. 따라서 인물 수만 늘리는 것 외에 **재생성 횟수·편집 종류·순서**를 나누어 실험할 이유가 생겼다.

다만 한 명·두 반복의 기술 통계이며 p값·모집단 효과·검증된 임계값을 제시하지 않는다. 순차 조건은 호출 수와 중간 입력·요구 순서가 함께 바뀌었고 호출 순서도 무작위화하지 않았다. no_change를 빼서 순수 요구 복잡도의 효과를 추정하지 않는다. 얼굴 동일성·피부 자연스러움·사람 선호는 이번에 측정하지 않았다.

다음 자동 실험에서는 같은 편집 세 개의 순서를 바꾸어 종류와 단계 위치를 분리하고, 편집 강도와 반복 수를 늘리는 것이 적절하다. 이번 결과는 기존 6명·7경로의 종합 결과나 사람 평가에 합산하지 않은 별도 실험이다.
'''
    (ROOT / 'RESULTS.md').write_text(content)
    print(ROOT / 'RESULTS.md')


if __name__ == '__main__':
    main()
