"""Rebuild descriptive replication tables from saved measurements."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
METRICS = [('face','mae'),('face','ssim'),('face','lpips'),('skin','mae'),('skin','ssim'),('skin','highpass_mae')]
HEAD = ['얼굴 MAE ↓','얼굴 SSIM ↑','얼굴 LPIPS ↓','피부 MAE ↓','피부 SSIM ↑','피부 고주파 MAE ↓']

def table(head, rows):
    return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    r=json.loads((ROOT/'results.json').read_text());assert r['complete']
    c=json.loads((ROOT/'color-results.json').read_text());assert c['checks_passed']
    v=json.loads((ROOT/'verification.json').read_text());assert v['passed']
    groups=[p+':final:'+a for p in ('P05','P06') for a in ('batch','SBP')]
    def summary(mode):
        rows=[]
        for g in groups:
            vals=[r['summary'][g]['metrics']['original'][s][mode][k] for s,k in METRICS]
            rows.append([g,*[f"{x['mean']:.6f} [{x['min']:.6f}, {x['max']:.6f}]" for x in vals]])
        return table(['인물/조건',*HEAD],rows)
    finals=[x for x in r['rows'] if x['stage']==(1 if x['order']=='batch' else 3)]
    individual=table(['출력',*HEAD],[[x['id'],*[f"{x['original'][s]['fixed'][k]:.6f}" for s,k in METRICS]] for x in finals])
    colors=table(['인물/조건','피부 원시 MAE','평균색 제거 잔차 MAE','MSE 평균색 항 비율'],[[g,f"{c['summary'][g]['original']['fixed']['raw_mae']:.6f}",f"{c['summary'][g]['original']['fixed']['residual_mae']:.6f}",f"{100*c['summary'][g]['original']['fixed']['bias_mse_fraction']:.1f}%"] for g in groups])
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'edit-replication-v1'})
    fig,axes=plt.subplots(2,3,figsize=(11,7))
    for ax,(s,k) in zip(axes.flat,METRICS):
        for x,g in enumerate(groups):
            d=r['summary'][g]['metrics']['original'][s]['fixed'][k]
            col='#3275b9' if g.endswith('batch') else '#a26435'
            ax.plot([x,x],[d['min'],d['max']],color=col)
            ax.scatter([x-.05,x+.05],d['values'],color=col)
        ax.set_xticks(range(4),[g.replace(':final:', '\n') for g in groups]);ax.set_title(s+' '+k);ax.grid(axis='y',alpha=.15)
    fig.suptitle('Batch vs sequential replication: distance from original\nTwo additional portraits; two outputs per final condition')
    fig.text(.5,.015,'Fixed ROIs. Points are individual outputs; bars show observed ranges, not confidence intervals.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.04,1,.92])
    for ext in ('png','pdf','svg'):fig.savefig(ROOT/f'final-comparison.{ext}',dpi=180)
    plt.close(fig)
    text=f'''# 타 인물 일괄/순차 재현 — 16회 새 생성

2026-09-09. 기존 P05/P06 각각에서 일괄 1회와 S→B→P 순차 3회를 두 번 실행했다. **16/16 출력 저장, 재시도 0, 픽셀 기준 서로 다른 이미지 16장**이다.

두 인물 모두에서 일괄 편집 두 출력의 고정 얼굴 MAE·LPIPS가 순차 두 출력보다 낮고 SSIM은 높았다. 효과 크기는 인물마다 달랐다. 피부 지표 평균도 두 인물에서 일괄 편집이 원본에 더 가까웠지만, P06 피부 MAE의 개별 범위는 겹친다. 얼굴 사각형에는 배경·머리 등이 포함되므로 이 결과를 사람의 피부 열화 등급이나 동일성 보존 성공률로 바꾸지 않는다.

## 설계와 범위

[사전 계획](PROTOCOL.md) · [입력·프롬프트·고정 ROI](plan.json). 이전 P04 결과를 본 뒤 설계한 후속 연구이며 미관찰 인물 검증은 아니다. 두 기존 원본에서 각 경로를 새로 시작했다. S=셔츠 남색, B=옅은 파랑 배경, P=은색 핀. 순서는 최적 결과를 골라 정한 것이 아니라 첫 예비 실험의 SBP를 유지했다. 모든 최종 프롬프트는 같다. 생성 seed와 내부 모델 버전은 노출되지 않았다.

두 반복의 최초 출력을 전부 보존했다. 생성 담당자의 가시적 실행 점검에서는 최종 출력에 셔츠 색·배경·핀 요청이 반영됐으나 세부 색조·핀 크기까지 동일한 것은 아니다. 이는 비블라인드 점검이며 사람 평가 또는 독립 AI 등급이 아니다. 새 사람 평가·독립 AI 점수는 수집하지 않았다.

## 고정 ROI 결과

평균 [최소, 최대]. 범위는 두 출력의 관측 범위이며 신뢰구간이 아니다. 낮은 MAE·LPIPS·고주파 MAE, 높은 SSIM은 해당 영역이 원본에 가깝다는 뜻이다.

{summary('fixed')}

![인물별 최종 지표](final-comparison.png)

[PDF](final-comparison.pdf) · [SVG](final-comparison.svg)

## 최종 출력별 값

{individual}

## NCC sigma3 보조 결과

{summary('3')}

sigma1/6과 모든 중간 단계·직전 입력 대비 지표는 [CSV](metrics.csv)와 [원시 결과](results.json)에 있다. NCC는 정수 이동만 보정하며 색·형태·질감 차이를 제거하지 않는다.

## 사전 포함한 피부 평균색 진단

{colors}

피부 영역별 출력−원본 차이 d를 평균색 b와 잔차 e=d−b로 나눴다. MSE=평균색 MSE+잔차 MSE를 검사했다. 두 인물 모두 평균색 제거 잔차 MAE도 일괄 편집 평균이 더 낮았다. 이 비율은 수학적 성분이며 조명 또는 열화의 인과적 비율이 아니다. MAE 항은 가산 분해가 아니다. [전체 결과](color-results.json).

## 검증과 재현

16개 입력 연결·첫 호출·파일 해시·1024×1536 크기와 완전성을 검사했다. 고정 얼굴 MAE/SSIM 원본·직전 32쌍을 별도로 재계산하고 CSV 640행 및 모든 집계값을 대조했다. 기존 LPIPS 전체 가중치 해시와 일치한다. [검증 기록](verification.json) · [환경·파일 해시](manifest.json).

```sh
.venv-metrics/bin/python experiments/edit-replication-v1/analyze.py
.venv-metrics/bin/python experiments/edit-replication-v1/verify.py
.venv-metrics/bin/python experiments/edit-replication-v1/color_diagnostic.py
.venv-metrics/bin/python experiments/edit-replication-v1/report.py
```

저장된 결과만 분석하며 새 생성이나 사람 응답을 만들지 않는다. P04 순서 연구와 모집단 표본처럼 합쳐 유의성을 계산하지 않았다. 이번 재현은 제한된 세 인물에서의 방향 일치에 근거를 더하지만 일반화, 자연스러움, 사람과 지표의 정합성은 검증하지 못한다.
'''
    (ROOT/'RESULTS.md').write_text(text)
    print(ROOT/'RESULTS.md')

if __name__=='__main__':main()
