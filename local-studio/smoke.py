"""Real API integration smoke test; explicitly runs local models."""
import json,time,urllib.request
from pathlib import Path
BASE='http://localhost:8770'
def get():return json.load(urllib.request.urlopen(BASE+'/api/bootstrap'))
token=get()['token']
def post(path,body):
 req=urllib.request.Request(BASE+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Studio-Token':token});return json.load(urllib.request.urlopen(req))
def poll(job):
 for _ in range(450):
  b=get();j=b['jobs'][job['id']]
  if j['status']!='running':
   assert j['status']=='done',j
   return next(p for p in b['projects'] if p['id']==job['project'])
  time.sleep(2)
 raise TimeoutError('job timeout')
p=post('/api/create',{'sample':True});print('CREATED',p['id'],flush=True)
j=post('/api/chat',{'project':p['id'],'revision':p['revision'],'request':'셔츠를 남색으로 바꾸고 배경은 옅은 파란색으로 해줘. 은색 핀 하나 추가해줘.'});p=poll(j);print('CHAT',p['state'],flush=True)
assert p['state']=={'shirt_color':'navy','background':'pale blue','pin':'silver'},p['state']
j=post('/api/generate',{'project':p['id'],'revision':p['revision']});p=poll(j);print('GENERATED',p['current_version'],flush=True)
v=p['versions'][0];assert v['state']==p['state'] and v['parent'] is None
req=urllib.request.urlopen(BASE+'/media/'+p['id']+'/'+v['image']);assert req.status==200 and req.read(8)==b'\x89PNG\r\n\x1a\n'
p=post('/api/state',{'project':p['id'],'revision':p['revision'],'state':{'shirt_color':'white','background':'ocean','pin':'none'}})
p=post('/api/restore',{'project':p['id'],'revision':p['revision'],'version':v['id']});assert p['state']==v['state'] and p['current_version']==v['id']
try:post('/api/state',{'project':p['id'],'revision':0,'state':p['state']});raise AssertionError('stale accepted')
except urllib.error.HTTPError as e:assert e.code==400
result={'passed':True,'project':p['id'],'version':v['id'],'state':p['state'],'generation_seconds':v['seconds'],'checks':['real Korean chat','real original-based generation','PNG retrieval','manual state save','restore image and state','stale revision rejection']}
Path(__file__).with_name('data').joinpath('smoke-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False),flush=True)
