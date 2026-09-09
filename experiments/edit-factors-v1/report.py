"""Descriptive 2x2 contrasts; no inference from pseudo-replicated images."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
ARMS=['gray_original','navy_original','gray_cable','navy_cable']
METRICS=[('face','mae'),('face','ssim'),('face','lpips'),('skin','mae'),('skin','ssim'),('skin','highpass_mae')]
HEAD=['얼굴 MAE','얼굴 SSIM','얼굴 LPIPS','피부 MAE','피부 SSIM','피부 고주파 MAE']
CONTRASTS={'color_at_original':[-1,1,0,0], 'color_at_cable':[0,0,-1,1],
           'material_at_gray':[-1,0,1,0], 'material_at_navy':[0,-1,0,1],
           'interaction':[1,-1,-1,1]}

def table(h,rows):
    return '\n'.join(['| '+' | '.join(h)+' |','| '+' | '.join(['---']*len(h))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    r=json.loads((ROOT/'results.json').read_text());assert r['complete']
    c=json.loads((ROOT/'color-results.json').read_text());assert c['checks_passed']
    v=json.loads((ROOT/'verification.json').read_text());assert v['passed']
    def data(p,a,s,k,mode='fixed'):
        return r['summary'][p+':final:'+a]['metrics']['original'][s][mode][k]
    def summaries(mode):
        return table(['인물','조건',*HEAD],[[p,a,*[f"{data(p,a,s,k,mode)['mean']:.6f} [{data(p,a,s,k,mode)['min']:.6f}, {data(p,a,s,k,mode)['max']:.6f}]" for s,k in METRICS]] for p in ('P04','P05','P06') for a in ARMS])
    contrasts={}
    for p in ('P04','P05','P06'):
        contrasts[p]={}
        for name,w in CONTRASTS.items():
            modes={}
            for mode in ('fixed','1','3','6'):
                vals={}
                for s,k in METRICS:
                    mean=float(np.dot(w,[data(p,a,s,k,mode)['mean'] for a in ARMS]))
                    blocks=[]
                    for rep in (1,2):
                        block=[next(x for x in r['rows'] if x['person']==p and x['order']==a and x['repeat']==rep)['original'][s][mode][k] for a in ARMS]
                        blocks.append(float(np.dot(w,block)))
                    assert abs(mean-np.mean(blocks))<1e-12
                    vals[s+'/'+k]={'mean_difference':mean,'block_differences':blocks}
                color_mean=float(np.dot(w,[c['summary'][p+':final:'+a]['original'][mode]['residual_mae'] for a in ARMS]))
                vals['skin/color_residual_mae']={'mean_difference':color_mean}
                modes[mode]=vals
            contrasts[p][name]=modes
    (ROOT/'contrasts.json').write_text(json.dumps({'coefficients_in_arm_order':CONTRASTS,'arm_order':ARMS,'results':contrasts,'source_sha256':hashlib.sha256((ROOT/'results.json').read_bytes()).hexdigest(),'block_average_check_passed':True,'inference':'descriptive_only; blocks are not seed-matched pairs'},indent=2)+'\n')
    ct=table(['인물','대비',*HEAD],[[p,n,*[f"{contrasts[p][n]['fixed'][s+'/'+k]['mean_difference']:+.6f}" for s,k in METRICS]] for p in contrasts for n in CONTRASTS])
    indiv=table(['출력',*HEAD],[[x['id'],*[f"{x['original'][s]['fixed'][k]:.6f}" for s,k in METRICS]] for x in r['rows']])
    color=table(['인물','조건','피부 원시 MAE','평균색 제거 잔차 MAE','MSE 평균색 항 비율'],[[p,a,*[f"{c['summary'][p+':final:'+a]['original']['fixed'][k]:.6f}" for k in ('raw_mae','residual_mae')],f"{100*c['summary'][p+':final:'+a]['original']['fixed']['bias_mse_fraction']:.1f}%"] for p in ('P04','P05','P06') for a in ARMS])
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'edit-factors-v1'})
    fig,axes=plt.subplots(2,3,figsize=(12,7.4))
    for ax,(s,k) in zip(axes.flat,METRICS):
        for p,col,dx in [('P04','#3275b9',-.15),('P05','#ad6233',0),('P06','#47906e',.15)]:
            for i,a in enumerate(ARMS):
                d=data(p,a,s,k);x=i+dx
                ax.plot([x,x],[d['min'],d['max']],color=col,alpha=.65)
                ax.scatter([x-.025,x+.025],d['values'],color=col,s=22,label=p if i==0 else None)
        ax.set_xticks(range(4),['Keep both','Color only','Material only','Color + material'],rotation=22)
        ax.set_title(s+' '+k);ax.grid(axis='y',alpha=.15)
    axes[0,0].legend(fontsize=9)
    fig.suptitle('Clothing color x material: distance from original\nThree portraits; two original-based outputs per cell')
    fig.text(.5,.015,'Fixed ROIs. Dots are outputs; bars are observed ranges. These are image distances, not human degradation scores.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.05,1,.92])
    for ext in ('png','pdf','svg'):fig.savefig(ROOT/f'factor-comparison.{ext}',dpi=180)
    plt.close(fig)
    text=f'''# 의상 색 × 재질 비교 — 24회 새 생성

2026-09-09. 기존 P04/P05/P06에서 색 유지/남색 × 재질 유지/케이블 니트의 네 조건을 두 번씩 새로 생성했다. **24/24 저장, 재시도 0, 픽셀 기준 서로 다른 출력 24장**이다.

요청 내용을 더 많이 바꾼다고 얼굴 차이가 항상 커지지는 않았다. P05에서는 색 변경에 따른 얼굴 LPIPS 증가가 보였으나 P06의 평균은 색·재질을 바꾼 조건이 변경 없는 조건보다 낮기도 했다. 재질 단독 변화의 얼굴·피부 지표 방향도 인물과 지표에 따라 달랐다. 따라서 이 네 조건을 보편적인 열화 강도 순서로 사용할 수 없다. 두 반복만으로 효과가 없다고 확정할 수도 없다.

## 사전 계획과 실행

[계획](PROTOCOL.md) · [모든 프롬프트·입력·영역](plan.json). 24개 모두 같은 인물의 원본부터 1회 생성했으므로 생성 횟수는 같다. gray_original은 변경 없는 요청, navy_original은 색만 남색, gray_cable은 재질만 케이블 니트, navy_cable은 두 가지 변경이다. 배경과 얼굴·신체·옷 외곽은 유지하도록 요청했다. 실제 케이블 두께·색조·접힘까지 통제한 물리적 강도 실험은 아니다.

첫 출력은 모두 보존했다. P06-gray_original-r1에서는 원본에 없던 수평 흰 줄무늬가 생겼다. P06-gray_original-r2에는 그 줄무늬가 없다. 변경 없는 프롬프트도 전체 이미지 보존을 보장하지 않는 실행 사례이며, 해당 출력을 제외하거나 재시도하지 않았다. 케이블 요청은 가시적으로 반영됐지만 목·소매·밑단의 짜임과 두께가 달라졌다. 이러한 생성 담당자의 비블라인드 관찰은 독립 평가 점수나 성공률이 아니다.

## 고정 영역 결과

평균 [최소, 최대], 각 셀 두 출력. 낮은 MAE/LPIPS/고주파 MAE와 높은 SSIM은 원본에 가까움을 뜻한다. 얼굴 사각형에는 머리·배경도 포함된다. 범위는 신뢰구간이 아니다.

{summaries('fixed')}

![색·재질별 자동 지표](factor-comparison.png)

[PDF](factor-comparison.pdf) · [SVG](factor-comparison.svg)

## 사전 정의한 대비

color_at_original=기존 재질에서 남색−회색 유지, color_at_cable=니트에서 같은 색 대비. material_at_gray=기존 색에서 니트−기존 재질, material_at_navy=남색에서 같은 재질 대비. interaction=(니트의 색 대비)−(기존 재질의 색 대비). 아래는 지표 원래 방향의 차이다. SSIM의 음수는 원본과 덜 비슷함을 뜻한다.

{ct}

두 반복 블록의 대비도 [contrasts.json](contrasts.json)에 보존했고, 그 평균이 셀 평균의 대비와 일치하는지 검사했다. 블록 번호가 같은 것은 생성 seed를 맞춘 짝이 아니다. 이 수치를 유의한 상호작용이나 인과적인 피부 열화 효과로 부르지 않는다.

## 평균색 제거 잔차

{color}

영역별 RGB 평균 차이를 제거한 잔차도 계산했다. MSE 항등식과 동일 입력·상수 오프셋 대조 검사를 통과했다. MSE 비율은 수학적 분해이며 조명 기여율이나 열화 비율이 아니다. MAE는 가산 분해되지 않는다. [원시 색 진단](color-results.json).

## NCC sigma3 보조 결과

{summaries('3')}

sigma1/6은 [CSV](metrics.csv)에 모두 있다. NCC 검색 경계 도달은 0이며 정렬로 제거할 수 없는 색·형태 차이는 남는다.

## 개별 출력 전체

{indiv}

## 사후 공간 진단

줄무늬 사례를 확인한 뒤 셔츠 내부와 좌우 배경 띠의 MAE·SSIM·평균색 제거 잔차를 24개 모두에서 추가 계산했다. [사후 계획](POSTHOC_SPATIAL.md) · [결과](SPATIAL_RESULTS.md). 편집 조건의 셔츠 차이는 의도한 변화도 포함하므로 낮을수록 성공이라는 지표가 아니다.

## 검증과 재현

입력·출력·호출 기록 해시, 최초 호출, 크기1024×1536, 3인물×4조건×2반복 완전성을 검사했다. 동일 조건 두 반복의 프롬프트가 같다. 원본/직전 입력은 동일하지만 일관된 데이터 형식을 위해 둘 다 저장했다. 이를 독립 관측 두 개로 세지 않는다. 고정 얼굴 MAE/SSIM 48쌍 재계산, CSV 960행 및 집계 검증을 통과했다. [검증 기록](verification.json) · [환경·파일 해시](manifest.json).

```sh
.venv-metrics/bin/python experiments/edit-factors-v1/analyze.py
.venv-metrics/bin/python experiments/edit-factors-v1/verify.py
.venv-metrics/bin/python experiments/edit-factors-v1/color_diagnostic.py
.venv-metrics/bin/python experiments/edit-factors-v1/report.py
```

사람의 자연스러움·정체성·편집 성공과 자동 지표의 일치는 이번 자료로 답할 수 없다. 기존 생성 인물 세 명과 노출되지 않은 모델 버전에 한정된 탐색 결과다. 유의성 검정·학습 임계값·지각적 강도 정답을 만들지 않았다.
'''
    (ROOT/'RESULTS.md').write_text(text)
    print(ROOT/'RESULTS.md')

if __name__=='__main__':main()
