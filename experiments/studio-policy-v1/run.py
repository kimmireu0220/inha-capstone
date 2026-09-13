"""Run the website's actual HTTP generation paths, retaining every successful call."""
import hashlib,json,shutil,time,urllib.request
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[1];BASE='http://localhost:8770'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(R/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def get():return json.load(urllib.request.urlopen(BASE+'/api/bootstrap',timeout=30))
def post(path,body):
 token=get()['token']
 return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Studio-Token':token}),timeout=30))
def project(pid):return next(p for p in get()['projects'] if p['id']==pid)
def poll(j):
 deadline=time.monotonic()+1000
 while time.monotonic()<deadline:
  b=get();job=b['jobs'][j['id']]
  if job['status']!='running':
   assert job['status']=='done',job
   return project(j['project'])
  time.sleep(2)
 raise TimeoutError(j['id'])
requests=['셔츠를 남색으로 바꿔줘.','배경을 옅은 파란색으로 바꿔줘.','은색 핀 하나 추가해줘.']
states=[{'shirt_color':'navy','background':'original','pin':'original'}, {'shirt_color':'navy','background':'pale blue','pin':'original'}, {'shirt_color':'navy','background':'pale blue','pin':'silver'}]
plan={'protocol_sha256':sha(R/'PROTOCOL.md'),'server_sha256':sha(REPO/'local-studio/server.py'),'source_sha256':sha(REPO/'experiments/trigger-validation-v1/P04/reference.png'),'seeds':[42,314],'requests':requests,'states':states,'roi':[176,44,336,224]}
if (R/'plan.json').exists():assert json.loads((R/'plan.json').read_text())==plan
else:save('plan.json',plan)
ledger=json.loads((R/'calls.json').read_text()) if (R/'calls.json').exists() else {'projects':{},'calls':[]}
for seed,modes in [(42,['sequential','regenerate']),(314,['regenerate','sequential'])]:
 pid=ledger['projects'].get(str(seed))
 if not pid:
  p=post('/api/create',{'sample':True,'name':f'모드 비교 · 시드 {seed}'})
  pid=p['id'];ledger['projects'][str(seed)]=pid;save('calls.json',ledger)
  shutil.copyfile(REPO/'local-studio/data'/pid/'reference.png',R/f'reference-{seed}.png')
 for mode in modes:
  expected=3 if mode=='sequential' else 1
  done=[c for c in ledger['calls'] if c['seed']==seed and c['mode']==mode]
  if len(done)==expected:continue
  assert not done,'Partial path retained; inspect before resuming rather than repeating successes.'
  p=project(pid);assert p['active_job'] is None
  p=post('/api/restore',{'project':pid,'revision':p['revision'],'version':None})
  p=post('/api/generation-settings',{'project':pid,'revision':p['revision'],'mode':mode,'seed':seed})
  for stage,(request,state) in enumerate(zip(requests,states),1):
   p=poll(post('/api/chat',{'project':pid,'revision':p['revision'],'request':request}));assert p['state']==state,p['state']
   if mode=='regenerate' and stage<3:continue
   print('START',seed,mode,stage,flush=True)
   j=post('/api/generate',{'project':pid,'revision':p['revision']})
   save('running.json',{'seed':seed,'mode':mode,'stage':stage,'job':j})
   p=poll(j);v=next(v for v in p['versions'] if v['id']==p['current_version'])
   assert v['mode']==mode and v['seed']==seed and v['state']==state
   source=REPO/'local-studio/data'/pid/v['id'];target=R/'generated'/f'{mode}-{seed}-s{stage}';target.mkdir(parents=True,exist_ok=True)
   for f in source.iterdir():
    if f.is_file():shutil.copyfile(f,target/f.name)
   record={'seed':seed,'mode':mode,'stage':stage,'project':pid,'version':v,'artifact_dir':str(target.relative_to(R))}
   ledger['calls'].append(record);save('calls.json',ledger)
   print('DONE',seed,mode,stage,round(v['seconds'],2),flush=True)
save('running.json',{'status':'complete','outputs':len(ledger['calls'])})
print('COMPLETE',len(ledger['calls']),flush=True)
