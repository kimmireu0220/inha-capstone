"""Post-hoc measurement of clothing and background; no image editing."""
import json
from pathlib import Path
import numpy as np
from analyze import ROOT,M,local,save
from color_diagnostic import decompose

REGIONS={'shirt_interior':[320,600,700,1000], 'background_left':[40,100,100,1100], 'background_right':[924,100,984,1100]}

def main():
    plan=json.loads((ROOT/'plan.json').read_text())
    primary=json.loads((ROOT/'results.json').read_text());assert primary['complete']
    rows=[]
    for job in plan['jobs']:
        ref=M.image(local(plan['people'][job['person']]['reference']));out=M.image(local(job['output']))
        assert M.sha(local(job['output']))==json.loads(local(job['output']).with_suffix('.call.json').read_text())['output_sha256']
        measures={}
        for name,roi in REGIONS.items():
            a=M.crop(out,roi);b=M.crop(ref,roi)
            d=decompose(a,b)
            measures[name]={'mae':d['raw_mae'],'ssim':M.ssim(a,b),'residual_mae':d['residual_mae']}
        measures['background_two_strips_mean']={k:float(np.mean([measures[n][k] for n in ('background_left','background_right')])) for k in ('mae','ssim','residual_mae')}
        rows.append({k:job[k] for k in ('id','person','order','repeat')}|{'metrics':measures})
    groups={}
    for person in ('P04','P05','P06'):
        for arm in ('gray_original','navy_original','gray_cable','navy_cable'):
            chosen=[r for r in rows if r['person']==person and r['order']==arm];assert len(chosen)==2
            groups[person+':'+arm]={region:{k:{'values':[r['metrics'][region][k] for r in chosen],'mean':float(np.mean([r['metrics'][region][k] for r in chosen]))} for k in ('mae','ssim','residual_mae')} for region in measures}
    save(ROOT/'spatial-results.json',{'status':'post_hoc','regions':REGIONS,'rows':rows,'summary':groups,'protocol_sha256':M.sha(ROOT/'POSTHOC_SPATIAL.md'),'source_results_sha256':M.sha(ROOT/'results.json'),'analysis_sha256':M.sha(Path(__file__))})
    text='# 셔츠·배경 사후 공간 진단\n\n[계획과 한계](POSTHOC_SPATIAL.md). 24개 최초 출력을 전부 포함했다. 아래 각 셀은 두 관측값이다. 편집 조건의 셔츠 MAE는 요청된 변화도 포함하므로 열화 순위가 아니다.\n\n| 인물/조건 | 셔츠 MAE 두 값 | 배경 두 띠 평균 MAE 두 값 |\n| --- | --- | --- |\n'
    for name,g in groups.items():
        text+='| '+name+' | '+', '.join(f'{v:.6f}' for v in g['shirt_interior']['mae']['values'])+' | '+', '.join(f'{v:.6f}' for v in g['background_two_strips_mean']['mae']['values'])+' |\n'
    text+='\nSSIM·평균색 제거 잔차와 좌우 배경 별도 값은 [원시 결과](spatial-results.json)에 있다. 가시적 줄무늬 사례의 위치를 이 수치만으로 판정하지 않았다.\n\n재현: `.venv-metrics/bin/python experiments/edit-factors-v1/spatial_diagnostic.py`\n'
    (ROOT/'SPATIAL_RESULTS.md').write_text(text)
    print(text)

if __name__=='__main__':main()
