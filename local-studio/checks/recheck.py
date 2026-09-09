import json,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def get():return json.load(urllib.request.urlopen('http://localhost:8770/api/bootstrap'))
token=get()['token']
def post(path,body):return json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:8770'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Studio-Token':token})))
p=post('/api/create',{'sample':True});cases=[]
for lang in ['phrasing','english']:
 for r in json.loads((ROOT/(lang+'-cases.json')).read_text()):cases.append({**r,'language':lang})
base={'shirt_color':'navy','background':'ocean','pin':'silver'}
for req,patch in [('Green shirt.',{'shirt_color':'green'}),('배경을 정원으로.',{'background':'garden'}),('Restore the background to original.',{'background':'original'}),('Do not delete the pin.',{}),('배경은 그대로 두고 셔츠는 회색으로.',{'shirt_color':'gray'}),('핀은 원본대로.',{'pin':'original'}),('그거 취소해줘.',None)]:
 cases.append({'id':'additional','request':req,'initial':base,'expected':None if patch is None else {**base,**patch},'language':'additional'})
results=[]
for r in cases:
 p=post('/api/state',{'project':p['id'],'revision':p['revision'],'state':r['initial']})
 j=post('/api/chat',{'project':p['id'],'revision':p['revision'],'request':r['request']})
 for _ in range(600):
  b=get();job=b['jobs'][j['id']]
  if job['status']!='running':break
  time.sleep(.2)
 p=next(x for x in b['projects'] if x['id']==p['id'])
 passed=(job['status']=='needs_input' and p['state']==r['initial'] and p['messages'][-1]['applied'] is False) if r['expected'] is None else job['status']=='done' and p['state']==r['expected']
 results.append({**r,'actual':p['state'],'status':job['status'],'passed':passed});print(r['request'],passed,flush=True)
(ROOT/'recheck-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print('PASS',sum(x['passed'] for x in results),'/',len(results),flush=True)
assert all(x['passed'] for x in results)
