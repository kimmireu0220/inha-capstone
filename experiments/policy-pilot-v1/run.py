"""Incremental policy scheduler; never generates images or reads human answers."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import lpips
from skimage.metrics import structural_similarity

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'trigger-validation-v1'
REF = SOURCE / 'P04/reference.png'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v): p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n')
def read(p): return json.loads(p.read_text())
def now(): return datetime.now(timezone.utc).isoformat()
STEPS = [x for x in read(SOURCE/'calls.json') if x['person']=='P04']
assert len(STEPS)==10
PREFIX = read(SOURCE/'rebase-template.json')['prefix']
CONFIG = read(SOURCE/'config.json')
ROI = CONFIG['roi_xyxy']['P04']
cachefile = ROOT/'metric-cache.json'
cache = read(cachefile) if cachefile.exists() else {}
network = None
def metric(path):
    global network
    key = sha(path)
    if key in cache: return cache[key]
    image = Image.open(path).convert('RGB')
    assert image.size == (1024,1536)
    a = np.asarray(Image.open(REF).convert('RGB').crop(ROI),dtype=np.float32)/255
    b = np.asarray(image.crop(ROI),dtype=np.float32)/255
    if network is None:
        torch.set_num_threads(2)
        torch.manual_seed(0)
        torch.use_deterministic_algorithms(True)
        network = lpips.LPIPS(net='alex',version='0.1',verbose=False).cpu().eval()
    def tensor(x): return torch.from_numpy(x.transpose(2,0,1).copy()).unsqueeze(0)*2-1
    with torch.no_grad():
        values = dict(mae=float(np.mean(np.abs(a-b))),ssim=float(structural_similarity(a,b,channel_axis=2,data_range=1.,win_size=7,gaussian_weights=False,use_sample_covariance=True)),lpips=float(network(tensor(a),tensor(b)).item()))
    cache[key] = values
    save(cachefile,cache)
    return values

def catalog():
    out = {}
    records = [SOURCE/'P04'/f'step-{i}.call.json' for i in range(1,11)] + [SOURCE/'P04/rebase.call.json'] + sorted((ROOT/'generated').glob('*.call.json'))
    for p in records:
        r = read(p)
        if not Path(r['output']).exists(): continue
        key = hashlib.sha256((sha(r['input'])+'\n'+r['prompt']).encode()).hexdigest()
        out.setdefault(key,dict(path=r['output'],record=str(p)))
    return out

def main():
    (ROOT/'generated').mkdir(exist_ok=True)
    cat = catalog()
    pending = {}
    policies = {}
    def lookup(stage,kind,input_path,prompt,policy):
        key = hashlib.sha256((sha(input_path)+'\n'+prompt).encode()).hexdigest()
        if key in cat: return cat[key]
        pending.setdefault(key,dict(id=key,stage=stage,kind=kind,input=str(input_path),input_sha256=sha(input_path),prompt=prompt,state=STEPS[stage-1]['state'],output=str(ROOT/'generated'/f'{key}.png'),policies=[]))['policies'].append(policy)
        return None
    for policy in ['sequential','fixed3','triggered']:
        previous = str(REF)
        rows = []
        for step in STEPS:
            stage = step['stage']
            raw = lookup(stage,'edit',previous,step['prompt'],policy)
            if raw is None: break
            before = metric(raw['path'])
            intervene = (policy=='fixed3' and stage%3==0) or (policy=='triggered' and before['lpips']>=.0555075)
            final = raw
            if intervene:
                prompt = PREFIX + '\n'.join('- '+v for v in step['state'].values())
                decision = ROOT/f'{policy}-stage-{stage}-decision.json'
                value = dict(policy=policy,stage=stage,input=previous,raw=raw,metrics=before,rebase=True,threshold=.0555075,recorded_at=now())
                if not decision.exists(): save(decision,value)
                else:
                    old=read(decision)
                    assert old['raw']==raw and old['metrics']==before
                final = lookup(stage,'rebase',REF,prompt,policy)
                if final is None: break
            after = metric(final['path'])
            rows.append(dict(stage=stage,state=step['state'],input=previous,raw=raw,final=final,rebased=intervene,before=before,after=after,alarm_after=after['lpips']>=.0555075))
            previous = final['path']
        policies[policy] = rows
    summary = {}
    for policy,rows in policies.items():
        values = [r['after']['lpips'] for r in rows]
        summary[policy] = dict(completed_stages=len(rows),rebase_stages=[r['stage'] for r in rows if r['rebased']],logical_calls_completed=len(rows)+sum(r['rebased'] for r in rows),mean_lpips=float(np.mean(values)) if values else None,max_lpips=max(values) if values else None,final_lpips=values[-1] if values else None,alarm_stages=sum(r['alarm_after'] for r in rows))
    result = dict(complete=all(len(v)==10 for v in policies.values()),human_evaluation='not_collected',independent_agent_evaluation='not_collected',summary=summary,policies=policies,new_calls=len(list((ROOT/'generated').glob('*.call.json'))))
    save(ROOT/'progress.json',result)
    save(ROOT/'pending.json',list(pending.values()))
    print(json.dumps(dict(complete=result['complete'],summary=summary,pending=list(pending.values())),ensure_ascii=False))

if __name__=='__main__': main()
