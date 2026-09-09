"""Fixed independent phrasing cases, exercised through the running API."""
import json,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE={'shirt_color':'navy','background':'ocean','pin':'silver'}
cases=[
('color','셔츠를 흰색으로 바꿔줘.',{'shirt_color':'white'}),
('synonym','상의 색만 하얗게 해줘.',{'shirt_color':'white'}),
('short','셔츠는 검정으로.',{'shirt_color':'black'}),
('background','배경만 도서관으로 바꿔줘.',{'background':'library'}),
('pin_add','금색 원형 핀 하나 달아줘.',{'pin':'gold'}),
('pin_remove','핀은 없애줘.',{'pin':'none'}),
('pin_paraphrase','가슴에 달린 핀을 지워줘.',{'pin':'none'}),
('keep','셔츠랑 배경은 그대로 두고 핀만 빼줘.',{'pin':'none'}),
('negative','핀은 빼지 말고 그대로 둬.',{}),
('correction','셔츠는 빨간색 말고 흰색으로 해줘.',{'shirt_color':'white'}),
('multiple','셔츠는 흰색으로, 핀은 금색으로 바꿔줘. 배경은 유지해.',{'shirt_color':'white','pin':'gold'}),
('reset','셔츠 색을 원본대로 돌려줘.',{'shirt_color':'original'}),
('ambiguous','아까처럼 해줘.',None),
('unsupported','머리를 길게 바꿔줘.',None)]
(ROOT/'phrasing-cases.json').write_text(json.dumps([{'id':i,'request':r,'initial':BASE,'expected':None if patch is None else {**BASE,**patch}} for i,r,patch in cases],ensure_ascii=False,indent=2)+'\n')
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
 (ROOT/'phrasing-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print(json.dumps(row,ensure_ascii=False),flush=True)
print('PASS',sum(x['passed'] for x in results),'/',len(results),flush=True)
