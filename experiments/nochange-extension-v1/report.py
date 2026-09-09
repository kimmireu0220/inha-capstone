"""Join explicitly reused stages 1-3 with new continuation stages 4-6."""
import copy
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
METRICS=[('face','mae'),('face','ssim'),('face','lpips'),('skin','mae'),('skin','ssim'),('skin','highpass_mae')]

def table(h,rows):
    return '\n'.join(['| '+' | '.join(h)+' |','| '+' | '.join(['---']*len(h))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    current=json.loads((ROOT/'results.json').read_text());assert current['complete']
    v=json.loads((ROOT/'verification.json').read_text());assert v['passed']
    prior=ROOT.parent/'edit-decomposition-v1'
    old=json.loads((prior/'results.json').read_text())
    skin={r['id']:r for r in json.loads((prior/'skin-results.json').read_text())['rows']}
    rows=[]
    for r in old['rows']:
        if r['arm']=='no_change':
            r=copy.deepcopy(r);r['original']['skin']=skin[r['id']]['skin'];r['source']='reused_stages_1_to_3';rows.append(r)
    for r in current['rows']:
        r=copy.deepcopy(r);r['source']='new_stages_4_to_6';rows.append(r)
    rows.sort(key=lambda r:(r['repeat'],r['stage']))
    assert len(rows)==12 and {(r['repeat'],r['stage']) for r in rows}=={(rep,s) for rep in (1,2) for s in range(1,7)}
    summary=[]
    for stage in range(1,7):
        chosen=[r for r in rows if r['stage']==stage]
        d={'stage':stage,'n_paths':2,'original':{s:{k:float(np.mean([r['original'][s]['fixed'][k] for r in chosen])) for scope,k in METRICS if scope==s} for s in ('face','skin')},'previous_face':{k:float(np.mean([r['previous']['face']['fixed'][k] for r in chosen])) for k in ('mae','ssim','lpips')}}
        summary.append(d)
    checks={str(rep):{k:bool(np.all(np.diff([r['original']['face']['fixed'][k] for r in rows if r['repeat']==rep])*(1 if k!='ssim' else -1)>0)) for k in ('mae','ssim','lpips')} for rep in (1,2)}
    (ROOT/'trajectory.json').write_text(json.dumps({'rows':rows,'summary':summary,'strict_original_distance_monotonicity':checks,'reused_outputs':6,'new_outputs':6,'independent_paths':2,'note':'Previously observed 3-stage paths were continued; not two new independent 6-stage paths.'},indent=2)+'\n')
    individual=table(['반복','단계','원본 MAE','원본 SSIM','원본 LPIPS','직전 LPIPS','피부 MAE','피부 SSIM','피부 고주파 MAE'],[[r['repeat'],r['stage'],*[f"{r['original']['face']['fixed'][k]:.6f}" for k in ('mae','ssim','lpips')],f"{r['previous']['face']['fixed']['lpips']:.6f}",*[f"{r['original']['skin']['fixed'][k]:.6f}" for k in ('mae','ssim','highpass_mae')]] for r in rows])
    means=table(['단계','원본 얼굴 LPIPS 평균','직전 얼굴 LPIPS 평균','원본 피부 MAE 평균'],[[r['stage'],f"{r['original']['face']['lpips']:.6f}",f"{r['previous_face']['lpips']:.6f}",f"{r['original']['skin']['mae']:.6f}"] for r in summary])
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'nochange-extension-v1'})
    fig,axes=plt.subplots(1,3,figsize=(12,4.3))
    specs=[('original','face','lpips'),('previous','face','lpips'),('original','skin','highpass_mae')]
    for ax,(basis,scope,k) in zip(axes,specs):
        for rep,col in [(1,'#3275b9'),(2,'#ad6233')]:
            selected=[r for r in rows if r['repeat']==rep]
            ax.plot(range(1,7),[r[basis][scope]['fixed'][k] for r in selected],marker='o',label=f'Path {rep}',color=col)
        ax.axvline(3.5,ls='--',color='gray',alpha=.6);ax.set_xticks(range(1,7));ax.set_xlabel('Generation step');ax.set_title(basis+' / '+scope+' '+k);ax.grid(alpha=.15)
    axes[0].legend()
    fig.suptitle('No-change regeneration: continuation from step 3 to step 6')
    fig.text(.5,.02,'Left of dashed line: reused observations. Right: new continuation. One portrait; two dependent trajectories.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.9])
    for ext in ('png','pdf','svg'):fig.savefig(ROOT/f'trajectory.{ext}',dpi=180)
    plt.close(fig)
    text=f'''# 변경 없는 재생성 — 3→6단계 연장

2026-09-09. 기존 P04 두 경로를 그대로 6단계까지 연장했다. **새 호출6/6 저장, 재시도0**. 아래12개 단계 관측 중 앞6장은 [이전 연구](../edit-decomposition-v1/RESULTS.md)의 재사용이고 뒤6장만 새 결과다. 독립 경로는 여전히2개다.

## 설계

[새 호출 전에 고정한 계획](PROTOCOL.md) · [프롬프트·입력 연결](plan.json). 모든 단계에서 같은 '아무 변경 없이 충실하게 재현' 프롬프트를 사용하고 직전 출력을 입력했다. 1~3단계 증가를 본 뒤 연장을 결정했으므로 사후 선택된 후속 관찰이다. 6단계에서 중단하는 상한을 새 출력 전에 정했다. 좋은 결과를 골라 교체하지 않았다.

## 원본 거리와 직전 거리

{means}

![반복 생성 궤적](trajectory.png)

[PDF](trajectory.pdf) · [SVG](trajectory.svg)

직전 입력과의 거리가 작아지는 것과 원본으로 돌아가는 것은 다르다. 단계별 차이를 단순히 더해서 원본 LPIPS를 계산할 수도 없다. 반복 간 차이와 전체 궤적을 함께 해석해야 하며, 여섯 단계만으로 장기 포화·수렴을 주장하지 않는다.

## 모든 관측값

{individual}

[trajectory.json](trajectory.json)에 기존 단계의 출처와 전체 지표를 연결했다. 새 단계의 원본/직전 얼굴·피부 지표 및 고정/NCCsigma1/3/6은 [results.json](results.json)과 [CSV](metrics.csv)에 있다. 기존1~3단계의 피부 분석은 원본 기준만 있으므로 직전 피부 값을 새로 지어 채우지 않았다. 원본 얼굴 거리의 엄격한 단계별 단조성 검사는 {json.dumps(checks,ensure_ascii=False)} 이다. SSIM은 감소 방향으로 검사했다.

## 검증

새6장의 크기·입력 연결·시간 순서·원본/이전 결과 해시를 확인했다. 원본/직전 고정 MAE/SSIM12쌍 별도 재계산, CSV240행, 모든 집계값을 대조했다. LPIPS 가중치는 기존과 같다. [검증](verification.json) · [환경·해시](manifest.json) · [새6장의 평균색/잔차 진단](color-results.json).

```sh
.venv-metrics/bin/python experiments/nochange-extension-v1/analyze.py
.venv-metrics/bin/python experiments/nochange-extension-v1/verify.py
.venv-metrics/bin/python experiments/nochange-extension-v1/color_diagnostic.py
.venv-metrics/bin/python experiments/nochange-extension-v1/report.py
```

저장된 출력을 읽는 분석이며 생성하지 않는다. 관측값은 원본과의 수치적 차이로서 사람의 피부 열화·자연스러움·동일성 정답이 아니다. 기존 경로를 연장한 한 인물 결과이므로 인물 일반화나 모델 일반화를 주장하지 않는다.
'''
    (ROOT/'RESULTS.md').write_text(text)
    print(json.dumps({'summary':summary,'monotonicity':checks},indent=2))

if __name__=='__main__':main()
