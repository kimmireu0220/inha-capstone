"""Fixed independent phrasing cases, exercised through the running API."""
import json,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE={'shirt_color':'navy','background':'ocean','pin':'silver'}
cases=[
('color','Change the shirt to white.',{'shirt_color':'white'}),
('synonym','Make only the top white.',{'shirt_color':'white'}),
('short','Black shirt.',{'shirt_color':'black'}),
('background','Change only the background to a library.',{'background':'library'}),
('pin_add','Add one gold circular pin.',{'pin':'gold'}),
('pin_remove','Remove the pin.',{'pin':'none'}),
('pin_paraphrase','Erase the pin attached to the chest.',{'pin':'none'}),
('keep','Keep the shirt and background unchanged and remove only the pin.',{'pin':'none'}),
('negative','Do not remove the pin. Keep it as it is.',{}),
('correction','Make the shirt white, not red.',{'shirt_color':'white'}),
('multiple','Change the shirt to white and the pin to gold. Keep the background.',{'shirt_color':'white','pin':'gold'}),
('reset','Restore the shirt color to the original image.',{'shirt_color':'original'}),
('ambiguous','Make it like before.',None),
('unsupported','Make the hair longer.',None)]
(ROOT/'english-cases.json').write_text(json.dumps([{'id':i,'request':r,'initial':BASE,'expected':None if patch is None else {**BASE,**patch}} for i,r,patch in cases],ensure_ascii=False,indent=2)+'\n')
def get():return json.load(urllib.request.urlopen('http://localhost:8770/api/bootstrap'))
token=get()['token']
def post(path,body):return json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:8770'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Studio-Token':token})))
p=post('/api/create',{'sample':True});results=[]
for i,request,patch in cases:
 p=post('/api/state',{'project':p['id'],'revision':p['revision'],'state':BASE})
 j=post('/api/chat',{'project':p['id'],'revision':p['revision'],'request':request})
 for _ in range(150):
  b=get();job=b['jobs'][j['id']]
  if job['status']!='running':break
  time.sleep(1)
 p=next(x for x in b['projects'] if x['id']==p['id'])
 expected=None if patch is None else {**BASE,**patch}
 passed=(job['status']=='error' and p['state']==BASE) if expected is None else job['status']=='done' and p['state']==expected
 row={'id':i,'request':request,'expected':expected,'actual':p['state'],'status':job['status'],'message':job['message'],'passed':passed};results.append(row)
 (ROOT/'english-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(row,ensure_ascii=False),flush=True)
print('PASS',sum(x['passed'] for x in results),'/',len(results),flush=True)
