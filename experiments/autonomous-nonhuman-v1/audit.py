"""Audit the saved nonhuman campaign without generation or human-label access."""
import ast
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
STUDIES={'edit-order-v1':38,'edit-replication-v1':16,'edit-factors-v1':24,'nochange-extension-v1':6}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def local(p):return REPO/('experiments/'+p.split('/experiments/',1)[1])

def main():
    records={};pixels=defaultdict(list);skin_error={'mae':0.,'ssim':0.};skin_pairs=0
    for name,count in STUDIES.items():
        p=ROOT.parent/name;plan=json.loads((p/'plan.json').read_text());r=json.loads((p/'results.json').read_text());v=json.loads((p/'verification.json').read_text());m=json.loads((p/'manifest.json').read_text())
        assert r['complete'] and r['measured']==count and v['passed']
        assert v['results_sha256']==sha(p/'results.json') and v['manifest_sha256']==sha(p/'manifest.json')
        assert m['signature']['analysis_sha256']==sha(p/'analyze.py')
        assert plan['protocol_sha256']==sha(p/'PROTOCOL.md')
        assert len(plan['jobs'])==count and len({j['id'] for j in plan['jobs']})==count
        for f,d in m['files_sha256'].items():assert sha(REPO/f)==d
        starts=[];indexed={x['id']:x for x in r['rows']}
        for j in plan['jobs']:
            out=local(j['output']);log=json.loads(out.with_suffix('.call.json').read_text());starts.append(datetime.fromisoformat(log['started']).timestamp())
            assert log['attempt']==1 and log['status']=='success'
            assert log['input_sha256']==sha(local(j['input'])) and log['output_sha256']==sha(out)
            with Image.open(out) as im:
                assert im.size==(1024,1536);a=np.asarray(im.convert('RGB'),dtype=np.float32)/255
                pixels[hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()].append(name+'/'+j['id'])
            if 'people' in plan:
                person=plan['people'][j['person']]
            else:
                person=json.loads((ROOT.parent/'edit-factors-v1/plan.json').read_text())['people']['P04']
                assert person['reference_sha256']==plan['reference_sha256'] and person['roi']==plan['roi']
            # A separate array path checks each fixed skin ROI, then its weighting.
            for basis,path in [('original',person['reference']),('previous',j['input'])]:
                with Image.open(local(path)) as im:b=np.asarray(im.convert('RGB'),dtype=np.float32)/255
                sizes=[];valid=[];maes=[];ssims=[]
                for region,(x0,y0,x1,y1) in person['skin_regions'].items():
                    aa=a[y0:y1,x0:x1];bb=b[y0:y1,x0:x1]
                    mae=float(np.abs(aa.astype(np.float64)-bb).mean())
                    ssim=float(structural_similarity(aa,bb,channel_axis=2,data_range=1.,win_size=7,gaussian_weights=False,use_sample_covariance=True))
                    expected=indexed[j['id']][basis]['skin']['fixed']['regions'][region]
                    skin_error['mae']=max(skin_error['mae'],abs(mae-expected['mae']))
                    skin_error['ssim']=max(skin_error['ssim'],abs(ssim-expected['ssim']))
                    sizes.append((x1-x0)*(y1-y0));valid.append((x1-x0-6)*(y1-y0-6));maes.append(mae);ssims.append(ssim);skin_pairs+=1
                expected=indexed[j['id']][basis]['skin']['fixed']
                skin_error['mae']=max(skin_error['mae'],abs(float(np.average(maes,weights=sizes))-expected['mae']))
                skin_error['ssim']=max(skin_error['ssim'],abs(float(np.average(ssims,weights=valid))-expected['ssim']))
        assert max(skin_error.values())<1e-7
        protocol_before_generation=(p/'PROTOCOL.md').stat().st_mtime<=min(starts)
        assert protocol_before_generation
        records[name]={'outputs':count,'protocol_file_predates_first_call':protocol_before_generation,'results_sha256':sha(p/'results.json'),'verification_sha256':sha(p/'verification.json'),'lpips_state_dict_sha256':m['signature']['lpips_state_dict_sha256'],'fixed_skin_pairs_recomputed':count*2*3}
        for source in p.glob('*.py'):ast.parse(source.read_text())
    assert len({x['lpips_state_dict_sha256'] for x in records.values()})==1
    new_unique=len(pixels);assert new_unique==84
    p=ROOT.parent/'edit-decomposition-v1';plan=json.loads((p/'plan.json').read_text());assert json.loads((p/'verification.json').read_text())['passed']
    for j in plan['jobs']:
        with Image.open(local(j['output'])) as im:pixels[hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()].append('edit-decomposition-v1/'+j['id'])
    assert len(pixels)==98
    result={'passed':True,'studies':records,'new_outputs_this_campaign':84,'unique_pixels_this_campaign':new_unique,'including_prior_14_unique_outputs':len(pixels),'duplicate_pixel_groups':[v for v in pixels.values() if len(v)>1],'independent_skin_region_pairs':skin_pairs,'skin_max_absolute_error':skin_error,'human_or_independent_agent_labels_added':0,'note':'Protocol mtime is a local provenance check, not external preregistration.'}
    (ROOT/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
