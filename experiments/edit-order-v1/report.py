"""Generate all-order tables and a scientific dot plot from recorded measurements."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
ORDERS = ['batch', 'SBP', 'SPB', 'BSP', 'BPS', 'PSB', 'PBS']


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---']*len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def main():
    r = json.loads((ROOT/'results.json').read_text()); assert r['complete']
    c = json.loads((ROOT/'color-results.json').read_text())
    v = json.loads((ROOT/'verification.json').read_text()); assert v['passed']
    summary = r['summary']
    metrics = [('face', 'mae'), ('face', 'ssim'), ('face', 'lpips'), ('skin', 'mae'), ('skin', 'ssim'), ('skin', 'highpass_mae')]

    def values(group, mode='fixed'):
        return [summary[group]['metrics']['original'][scope][mode][k] for scope, k in metrics]

    def show(value):
        return f"{value['mean']:.6f} [{value['min']:.6f}, {value['max']:.6f}]"

    header = ['조건', '얼굴 MAE ↓', '얼굴 SSIM ↑', '얼굴 LPIPS ↓', '피부 MAE ↓', '피부 SSIM ↑', '피부 고주파 MAE ↓']
    finals = table(header, [[order, *map(show, values('final:'+order))] for order in ORDERS])
    aligned = table(header, [[order, *map(show, values('final:'+order, '3'))] for order in ORDERS])
    first = table(header, [[edit+' 단독 (4회)', *map(show, values('stage:1:added:'+edit))] for edit in 'SBP'])
    pairs = table(header, [[p, *map(show, values('two_step:'+p))] for p in ['SB','BS','SP','PS','BP','PB']])
    individual = table(['순서', '반복', *header[1:]], [[row['order'], row['repeat'],
                        *[f"{row['original'][scope]['fixed'][k]:.6f}" for scope,k in metrics]]
                       for order in ORDERS for row in r['rows'] if row['order']==order and row['stage']==(1 if order=='batch' else 3)])
    ranks = []
    for scope,k in metrics:
        ranks.append([scope+'/'+k, *[' → '.join(sorted(ORDERS[1:], key=lambda order:
                       (1 if k!='ssim' else -1)*summary['final:'+order]['metrics']['original'][scope]['fixed'][k]['values'][rep])) for rep in (0,1)]])
    rank_table = table(['지표 (원본에 가까운 순)', '반복 1', '반복 2'], ranks)
    color_rows=[]
    for edit in 'SBP':
        value=c['summary']['stage:1:added:'+edit]['original']['fixed']
        color_rows.append([edit, *[f"{value[k]:.6f}" for k in ['raw_mae','bias_abs_mean','residual_mae']],f"{100*value['bias_mse_fraction']:.1f}%"])
    color_table=table(['단독 편집', '피부 원시 MAE', '평균색 오프셋 절댓값', '평균색 제거 잔차 MAE', 'MSE 중 평균색 항 비율'],color_rows)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'edit-order-v1'})
    fig,axes=plt.subplots(2,3,figsize=(12,7.3))
    titles=['Face MAE (lower)','Face SSIM (higher)','Face LPIPS (lower)','Interior skin MAE (lower)','Interior skin SSIM (higher)','Interior high-pass MAE (lower)']
    for ax,(scope,k),title in zip(axes.flat,metrics,titles):
        for x,order in enumerate(ORDERS):
            data=summary['final:'+order]['metrics']['original'][scope]['fixed'][k]
            color='#3275b9' if order=='batch' else '#a26435'
            ax.plot([x,x],[data['min'],data['max']],color=color,alpha=.5)
            ax.scatter([x-.06,x+.06],data['values'],color=color,s=26,alpha=.8)
            ax.scatter([x],[data['mean']],color=color,s=35,marker='_')
        ax.set_xticks(range(7),ORDERS,rotation=35);ax.set_title(title);ax.grid(axis='y',alpha=.15)
    fig.suptitle('Editing order: final distance from original\nOne portrait; two paths per condition; fixed ROIs',fontsize=15)
    fig.text(.5,.015,'S = navy shirt; B = pale-blue background; P = silver pin. Dots = individual outputs; bars = observed range, not confidence intervals.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.04,1,.9])
    for ext in ('png','pdf','svg'):fig.savefig(ROOT/f'final-comparison.{ext}',dpi=180)
    plt.close(fig)
    text=f'''# 편집 순서 6종 비교 — 38회 새 생성 결과

2026-09-09. 사람 평가 없이 P04 한 인물에서 6순열×2반복×3단계와 일괄 편집 2회를 실행했다. **38/38 성공, 재시도 0, 픽셀 기준 서로 다른 출력 38장**이다. 기존 14회 실험과 별도 날짜·설계의 자료이며 합산하지 않는다.

## 관측된 결과와 해석

일괄 편집의 두 최종 출력은 모든 순차 출력보다 고정 얼굴 ROI의 LPIPS·MAE가 낮고 SSIM이 높았다. 하지만 여섯 순차 순서 사이의 우열은 지표와 반복에 따라 달라져 **현재 자료로 최적 편집 순서를 정할 수 없다.** 피부 내부 지표는 개별 반복의 범위가 겹치므로 얼굴 사각형의 결과를 그대로 피부의 확정 우열로 바꾸지 않는다.

첫 단계 단독 편집에서는 배경 변경의 차이가 컸다. 사후 평균색 분리에서는 그 피부 MSE의 상당 부분이 영역별 평균색 항에 해당했다. 따라서 배경 변경 후의 큰 MAE를 곧 질감 열화로 부르면 안 된다. 평균색을 제거한 잔차도 남지만 그것 역시 열화 정답은 아니다.

## 설계

[사전 고정 계획](PROTOCOL.md) · [38개 프롬프트와 입력 계획](plan.json). S=셔츠 남색, B=배경 옅은 파랑, P=보는 사람 기준 오른쪽 가슴의 은색 원형 핀. 모든 경로의 최종 프롬프트가 같고, 중간 프롬프트도 완료된 요구를 S/B/P 정규 순서로 나열했다. 각 반복 블록의 경로 순서는 사전 난수로 섞었다. 실제 생성 seed·내부 모델 버전은 노출되지 않았다.

원본은 기존 P04, 크기는 모두 1024×1536. 기존 얼굴 ROI [352,88,672,448]와 기존 이마·양 볼 영역을 사용했다. 모든 경로는 원본부터 새로 생성했고 첫 단계가 같아도 결과를 공유하지 않았다. 단계와 인물·경로를 구분하며 38장을 독립 인물 38명처럼 세지 않는다.

내장 `image_gen.imagegen`의 첫 출력만 보존했다. 생성 담당자는 최종 14장에 셔츠·배경·핀 요청이 가시적으로 반영된 것을 점검했다. 핀 위치·크기·배경 색조의 미세 차이가 있어 요구 구현이 픽셀 수준에서 동일하지는 않다. 이는 비블라인드 실행 점검이며 사람 평가나 독립 AI 점수가 아니다.

## 최종 고정 ROI 결과

평균 [최소, 최대]. 범위는 두 관측값이며 신뢰구간이 아니다. MAE·LPIPS·고주파 MAE는 낮을수록, SSIM은 높을수록 원본에 가깝다.

{finals}

![순서별 최종 관측값](final-comparison.png)

[PDF](final-comparison.pdf) · [SVG](final-comparison.svg)

## 반복별 최종값과 순위 안정성

{individual}

{rank_table}

순위표는 효과 크기·불확실성을 대신하지 않는다. 같은 마지막 편집을 가진 BSP/SBP, BPS/PBS, PSB/SPB도 위 모든 값에 포함했다. 한 지표에서의 순위를 최적 순서로 선택하지 않는다.

## 같은 원본에서 시작한 단독 편집

첫 단계의 S·B·P는 각각 네 번 호출됐다. 후속 단계가 서로 다른 경로에서 나온 첫 출력이지만 모두 같은 원본과 같은 해당 단독 프롬프트를 사용했다.

{first}

## 같은 요구 집합을 가진 두 단계 비교

SB와 BS, SP와 PS, BP와 PB는 생성 횟수와 완료 요구 집합이 같다. 다만 중간 출력·실현된 색조·질감까지 동일하지는 않다. 둘씩 비교할 때에도 두 관측 범위와 지표 차이를 함께 봐야 한다.

{pairs}

전체 단계×추가 편집 셀은 각 4관측이며 [results.json](results.json)의 `summary`에 원본 및 직전 입력 기준으로 모두 보존했다. 이전에 완료된 요구 집합이 달라 이 셀 평균을 순수 편집 종류의 인과효과라고 부르지 않는다.

## NCC sigma3 보조 결과

{aligned}

sigma1/6도 모두 [CSV](metrics.csv)에 보존했다. 검색 경계에 도달한 경우는 원본·직전 기준 모두 0이다. NCC 보정은 정수 이동만 다루며 색·밝기·변형을 제거하지 않는다.

## 사후 진단: 피부 평균색과 잔차

[추가 계획](POSTHOC_COLOR.md)은 첫 단계 수치를 본 뒤 작성했다. d=출력−원본, b=영역별 RGB 평균(d), e=d−b로 나눴다. MSE=평균색 MSE+잔차 MSE 항등식을 모든 영역에서 검사했다. MAE는 이처럼 가산 분해되지 않으므로 열의 MAE 값을 더하거나 뺀 비율로 해석하지 않는다.

{color_table}

비율은 각 단독 편집 그룹의 평균 bias-MSE/평균 raw-MSE다. 수학적 성분 분리이며 조명이나 피부 열화의 인과적 기여율이 아니다. 영역별 평균색 제거는 실제 변화를 흡수할 수 있다. 이 분석을 위해 수정된 이미지 파일을 생성하지 않았다.

모든 38개 출력·두 기준·네 좌표 설정의 [추가 진단 원시 결과](color-results.json)를 보존했다.

## 검증과 재현

38개 입력 연결·SHA256·크기·첫 호출을 확인했다. 전체 최종 프롬프트가 동일하고 단계×추가 편집 셀이 균형을 이루는지 검사했다. 원본/직전 76쌍의 고정 MAE·SSIM을 별도 경로로 재계산하고 CSV 1520행과 모든 그룹 평균을 대조했다. LPIPS 전체 가중치 해시는 기존 분석과 같다. [검증 결과](verification.json) · [환경과 파일 해시](manifest.json).

```sh
.venv-metrics/bin/python experiments/edit-order-v1/analyze.py
.venv-metrics/bin/python experiments/edit-order-v1/verify.py
.venv-metrics/bin/python experiments/edit-order-v1/color_diagnostic.py
.venv-metrics/bin/python experiments/edit-order-v1/report.py
```

저장된 출력의 분석만 수행하며 생성 API를 호출하지 않는다. `--partial`은 중간 점검용이고 최종 결과는 38개 완전성을 요구한다. 소스·입력·가중치 해시가 같을 때만 측정 캐시를 재사용한다.

## 다음 판단

현재 가장 일관된 관측은 순차 순서의 최적화보다 일괄/반복 방식의 차이다. 한 인물만으로 일반화할 수 없어 같은 요구를 다른 기존 인물에 적용하는 재현 실험이 필요하다. 동시에 배경 변화가 피부 평균색에 반영되는 현상을 확인했으므로 편집 강도를 바꿀 때 색 변화와 형태·재질 변화를 별도로 정의해야 한다. 사람의 자연스러움·동일성·선호는 여전히 측정하지 않았다.
'''
    (ROOT/'RESULTS.md').write_text(text)
    print(ROOT/'RESULTS.md')


if __name__ == '__main__':
    main()
