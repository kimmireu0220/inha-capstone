"""Resumable experiment through the same HTTP API used by the studio UI."""
import base64,hashlib,json,shutil,time,urllib.request
from pathlib import Path
R=Path(__file__).resolve().parent; REPO=R.parents[1]; BASE='http://localhost:8770'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 p=R/n;t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def get():return json.load(urllib.request.urlopen(BASE+'/api/bootstrap',timeout=30))
def post(path,b):
 return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=json.dumps(b).encode(),headers={'Content-Type':'application/json','X-Studio-Token':get()['token']}),timeout=30))
def project(pid):return next(p for p in get()['projects'] if p['id']==pid)
def poll(j):
 for _ in range(1800):
  job=get()['jobs'][j['id']]
  if job['status']!='running':
   assert job['status']=='done',job
   return project(j['project'])
  time.sleep(2)
 raise TimeoutError(j['id'])
requests=['셔츠를 남색으로 바꿔줘.','배경을 옅은 파란색으로 바꿔줘.','은색 핀 하나 추가해줘.']
states=[dict(shirt_color='navy',background='original',pin='original'),dict(shirt_color='navy',background='pale blue',pin='original'),dict(shirt_color='navy',background='pale blue',pin='silver')]
rois=[[170,60,330,240],[176,80,336,260],[176,32,336,212],[176,44,336,224],[176,36,336,216],[176,44,336,224]]
people={f'P{i:02}':{'source':f'assets/people/P{i:02}.png' if i<=3 else f'experiments/trigger-validation-v1/P{i:02}/reference.png','roi':rois[i-1]} for i in range(1,7)}
for p in people.values():p['source_sha256']=sha(REPO/p['source'])
plan={'people':people,'seeds':[42,314,2026],'requests':requests,'states':states,'expected_outputs':72,'protocol_sha256':sha(R/'PROTOCOL.md'),'code_sha256':{p:sha(REPO/'local-studio'/p) for p in ['server.py','intent.py','state_model.py']}}
if (R/'plan.json').exists():assert json.loads((R/'plan.json').read_text())==plan
else:save('plan.json',plan)
ledger=json.loads((R/'calls.json').read_text()) if (R/'calls.json').exists() else {'projects':{},'calls':[]}
for pi,(person,info) in enumerate(people.items()):
 for si,seed in enumerate(plan['seeds']):
  for mode in (['sequential','regenerate'] if (pi+si)%2==0 else ['regenerate','sequential']):
   key=f'{person}-{seed}-{mode}';pid=ledger['projects'].get(key)
   if not pid:
    p=post('/api/create',{'image':base64.b64encode((REPO/info['source']).read_bytes()).decode(),'name':f'다인물 비교 · {person} · {seed} · {mode}'})
    pid=p['id'];ledger['projects'][key]=pid;save('calls.json',ledger)
    shutil.copyfile(REPO/'local-studio/data'/pid/'reference.png',R/f'reference-{person}.png')
   p=project(pid)
   if p['active_job']:p=poll(get()['jobs'][p['active_job']])
   if p.get('generation_mode')!=mode or p.get('generation_seed')!=seed:
    p=post('/api/generation-settings',{'project':pid,'revision':p['revision'],'mode':mode,'seed':seed})
   for stage,(request,state) in enumerate(zip(requests,states),1):
    if any(c['person']==person and c['seed']==seed and c['mode']==mode and c['stage']==stage for c in ledger['calls']):continue
    if mode=='regenerate' and stage<3 and p['state']==states[-1]:continue
    existing=next((v for v in p['versions'] if v['mode']==mode and v['seed']==seed and v['state']==state),None)
    if existing is None:
     if p['state']!=state:
      p=poll(post('/api/chat',{'project':pid,'revision':p['revision'],'request':request}));assert p['state']==state,p['state']
     if mode=='regenerate' and stage<3:continue
     print('START',person,seed,mode,stage,flush=True)
     j=post('/api/generate',{'project':pid,'revision':p['revision']});save('running.json',{'status':'running','person':person,'seed':seed,'mode':mode,'stage':stage,'completed':len(ledger['calls']),'job':j})
     p=poll(j);existing=next(v for v in p['versions'] if v['id']==p['current_version'])
    v=existing;assert v['mode']==mode and v['seed']==seed and v['state']==state
    source=REPO/'local-studio/data'/pid/v['id'];target=R/'generated'/f'{key}-s{stage}';target.mkdir(parents=True,exist_ok=True)
    for f in source.iterdir():
     if f.is_file():shutil.copyfile(f,target/f.name)
    ledger['calls'].append({'person':person,'seed':seed,'mode':mode,'stage':stage,'project':pid,'version':v,'artifact_dir':str(target.relative_to(R))});save('calls.json',ledger)
    print('DONE',len(ledger['calls']),'/72',person,seed,mode,stage,round(v['seconds'],2),flush=True)
save('running.json',{'status':'complete','outputs':len(ledger['calls'])})
