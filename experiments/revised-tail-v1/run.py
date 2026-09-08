"""Schedule revised tails; built-in image generation is performed separately."""
import importlib.util
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent
def read(p): return json.loads(Path(p).read_text())
def save(p, x): Path(p).write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec = importlib.util.spec_from_file_location('old_metrics', EXP/'policy-pilot-v1/run.py')
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)
metrics.cachefile = ROOT/'metric-cache.json'
metrics.cache = read(metrics.cachefile) if metrics.cachefile.exists() else {}

prefix = read(EXP/'trigger-validation-v1/P04/step-8.call.json')['prompt'].split('\nNew edit:')[0]
rebase_prefix = read(EXP/'trigger-validation-v1/rebase-template.json')['prefix']
base_state = read(EXP/'trigger-validation-v1/P04/step-8.call.json')['state']
steps = []
for stage in (9,10):
    state = dict(base_state)
    state['clothes'] = 'A charcoal grey blazer over a burgundy crewneck shirt.'
    change = 'Change only the crewneck shirt color from ivory to burgundy. Keep the charcoal grey blazer, blue pin, necklace, earrings and background unchanged.'
    if stage == 10:
        state['background'] = 'A quiet library with wooden bookshelves; original lighting on the person remains unchanged.'
        change = 'Replace only the office background with a quiet library with wooden bookshelves. Keep the person and lighting on the person unchanged.'
    prompt = prefix+'\nNew edit:\n'+change+'\nComplete current requirements after this edit (supersede earlier versions):\n'+'\n'.join('- '+v for v in state.values())
    assert 'pocket' not in prompt.lower()
    steps.append(dict(stage=stage,state=state,prompt=prompt))
save(ROOT/'prompts.json',steps)

source_dirs = [('P01',EXP/'ten-stage-v1',[340,120,660,480]),('P02',EXP/'ten-stage-p02-v1',[352,160,672,520]),('P03-r1',EXP/'ten-stage-p03-v1/run-1',[352,64,672,424]),('P03-r2',EXP/'ten-stage-p03-v1/run-2',[352,64,672,424])]
cfg=read(EXP/'trigger-validation-v1/config.json')
source_dirs += [(p,EXP/'trigger-validation-v1'/p,cfg['roi_xyxy'][p]) for p in ('P04','P05','P06')]
branches=[]
for name,folder,roi in source_dirs:
    ref=read(folder/'step-1.call.json')['input']
    branches.append(dict(name=name,policy='sequential',reference=ref,roi=roi,initial=str(folder/'step-8.png'),prefix_files=[str(folder/f'step-{i}.png') for i in range(1,9)]))
old=read(EXP/'policy-pilot-v1/progress.json')
for policy in ('fixed3','triggered'):
    rows=old['policies'][policy][:8]
    branches.append(dict(name='P04-'+policy,policy=policy,reference=str(EXP/'trigger-validation-v1/P04/reference.png'),roi=cfg['roi_xyxy']['P04'],initial=rows[-1]['final']['path'],prefix_files=[r['final']['path'] for r in rows],prefix_rebases=[r['stage'] for r in rows if r['rebased']]))
snapshot=[dict(b,reference_sha256=sha(b['reference']),prefix_sha256=[sha(p) for p in b['prefix_files']]) for b in branches]
if (ROOT/'inputs.json').exists(): assert read(ROOT/'inputs.json')==snapshot
else: save(ROOT/'inputs.json',snapshot)
(ROOT/'generated').mkdir(exist_ok=True)
pending={}
def lookup(b,step,kind,inp,prompt):
    key=hashlib.sha256((sha(inp)+'\n'+prompt).encode()).hexdigest()
    output=ROOT/'generated'/f'{key}.png'
    record=output.with_suffix('.call.json')
    if record.exists():
        r=read(record)
        assert r['prompt']==prompt and r['input_sha256']==sha(inp)
        assert sha(output)==r['output_sha256']
        return str(output)
    assert not output.exists(), 'Unrecorded output: do not regenerate'
    job=dict(id=key,stage=step['stage'],kind=kind,input=inp,input_sha256=sha(inp),output=str(output),prompt=prompt,state=step['state'],branches=[])
    pending.setdefault(key,job)['branches'].append(b['name'])
    return None

results=[]
for b in branches:
    metrics.REF=Path(b['reference']); metrics.ROI=b['roi']
    previous=b['initial']; rows=[]
    for step in steps:
        raw=lookup(b,step,'edit',previous,step['prompt'])
        if raw is None: break
        before=metrics.metric(raw)
        intervene=(b['policy']=='fixed3' and step['stage']%3==0) or (b['policy']=='triggered' and before['lpips']>=.0555075)
        final=raw
        if intervene:
            final=lookup(b,step,'rebase',b['reference'],rebase_prefix+'\n'.join('- '+v for v in step['state'].values()))
            if final is None: break
        after=metrics.metric(final)
        rows.append(dict(stage=step['stage'],input=previous,raw=raw,final=final,before=before,after=after,rebased=intervene,state=step['state']))
        previous=final
    results.append(dict(**b,rows=rows))
save(ROOT/'pending.json',list(pending.values()))
save(ROOT/'progress.json',dict(complete=all(len(b['rows'])==2 for b in results),human_evaluation='not_collected',independent_agent_evaluation='not_collected',branches=results,new_calls=len(list((ROOT/'generated').glob('*.call.json')))))
print(json.dumps(dict(completed=[(b['name'],len(b['rows'])) for b in results],pending=len(pending)),ensure_ascii=False))
