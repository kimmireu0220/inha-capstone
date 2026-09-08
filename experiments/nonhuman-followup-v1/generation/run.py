"""Schedule first-trigger-only, end-only, always-original controls; no image API."""
import hashlib,json,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXP=ROOT.parent.parent
def read(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('base_metrics',EXP/'policy-pilot-v1/run.py')
mm=importlib.util.module_from_spec(spec);spec.loader.exec_module(mm)
mm.cachefile=ROOT/'metric-cache.json';mm.cache=read(mm.cachefile) if mm.cachefile.exists() else {}
prefix=read(EXP/'trigger-validation-v1/rebase-template.json')['prefix']
steps=read(EXP/'trigger-validation-v1/calls.json')
steps=[s for s in steps if s['person']=='P04' and s['stage']<=8]+read(EXP/'revised-tail-v1/prompts.json')
assert [s['stage'] for s in steps]==list(range(1,11))
current=read(EXP/'revised-tail-v1/progress.json')['branches']
cfg={b['name']:b for b in current}
catalog={}
files=list((EXP/'policy-pilot-v1/generated').glob('*.call.json'))+list((EXP/'revised-tail-v1/generated').glob('*.call.json'))+list((EXP/'trigger-validation-v1').glob('P*/rebase.call.json'))+list((ROOT/'generated').glob('*.call.json'))
for p in files:
    r=read(p)
    if 'pocket' in r['prompt'].lower():continue
    key=hashlib.sha256((sha(r['input'])+'\n'+r['prompt']).encode()).hexdigest()
    catalog.setdefault(key,r)
(ROOT/'generated').mkdir(exist_ok=True)
pending={}
failures={r['id']:r for r in [read(p) for p in (ROOT/'failures').glob('*.json')]}
blocked={}
def lookup(b,stage,kind,inp,prompt):
    assert 'pocket' not in prompt.lower()
    key=hashlib.sha256((sha(inp)+'\n'+prompt).encode()).hexdigest()
    if key in catalog:return catalog[key]['output']
    if key in failures:
        blocked[b]=dict(stage=stage,failure_id=key,reason='generation_failed_no_retry')
        return None
    output=str(ROOT/'generated'/f'{key}.png')
    assert not Path(output).exists(), 'Unrecorded output; do not regenerate'
    pending.setdefault(key,dict(id=key,stage=stage,kind=kind,input=inp,input_sha256=sha(inp),prompt=prompt,state=steps[stage-1]['state'],output=output,branches=[]))['branches'].append(b)
    return None
def metric(b,p):
    mm.REF=Path(cfg[b]['reference']);mm.ROI=cfg[b]['roi'];return mm.metric(p)
results=[]
for person,alarm in [('P04',3),('P05',2),('P06',2)]:
    base=cfg[person];prefix_files=base['prefix_files'][:alarm-1]
    initial=read(EXP/'trigger-validation-v1'/person/'rebase.call.json')
    assert initial['stage']==alarm and initial['prompt']==prefix+'\n'.join('- '+v for v in steps[alarm-1]['state'].values())
    rows=[dict(stage=i+1,output=p,metrics=metric(person,p),rebased=False) for i,p in enumerate(prefix_files)]
    previous=initial['output'];rows.append(dict(stage=alarm,output=previous,metrics=metric(person,previous),rebased=True))
    for step in steps[alarm:]:
        output=lookup(person+'-once-triggered',step['stage'],'edit',previous,step['prompt'])
        if output is None:break
        rows.append(dict(stage=step['stage'],input=previous,output=output,metrics=metric(person,output),rebased=False))
        previous=output
    results.append(dict(name=person+'-once-triggered',person=person,policy='once-triggered',alarm_stage=alarm,reference=base['reference'],roi=base['roi'],rows=rows,logical_calls=11))
for person in ['P01','P02','P03-r1','P03-r2','P04','P05','P06']:
    base=cfg[person];out=lookup(person+'-end-only',10,'rebase',base['reference'],prefix+'\n'.join('- '+v for v in steps[-1]['state'].values()))
    rows=[] if out is None else [dict(stage=10,output=out,metrics=metric(person,out),rebased=True)]
    results.append(dict(name=person+'-end-only',person=person,policy='end-only',reference=base['reference'],roi=base['roi'],rows=rows,logical_calls=11,single_shot_calls=1))
rows=[]
for step in steps:
    out=lookup('P04-always-original',step['stage'],'rebase',cfg['P04']['reference'],prefix+'\n'.join('- '+v for v in step['state'].values()))
    if out is not None:rows.append(dict(stage=step['stage'],output=out,metrics=metric('P04',out),rebased=True))
results.append(dict(name='P04-always-original',person='P04',policy='always-original',reference=cfg['P04']['reference'],roi=cfg['P04']['roi'],rows=rows,logical_calls=10))
assert len(list((ROOT/'generated').glob('*.call.json')))<=27
complete=all(len(r['rows'])==(1 if r['policy']=='end-only' else 10) for r in results)
for r in results:
    if r['name'] in blocked:
        r['stopped']=blocked[r['name']]
        r['planned_logical_calls']=r.pop('logical_calls')
        r['observed_successful_calls']=len(r['rows'])+1
        r['observed_attempted_calls']=len(r['rows'])+2
save(ROOT/'pending.json',list(pending.values()))
save(ROOT/'progress.json',dict(complete=complete,full_design_complete=complete,collection_complete=not pending,terminal_failures=blocked,branches=results,new_calls=len(list((ROOT/'generated').glob('*.call.json'))),new_failed_calls=len(failures),human_evaluation='not_collected'))
print(json.dumps(dict(complete=complete,collection_complete=not pending,pending=len(pending),failures=blocked,new_calls=len(list((ROOT/'generated').glob('*.call.json'))),branches=[(b['name'],len(b['rows'])) for b in results]),ensure_ascii=False))
