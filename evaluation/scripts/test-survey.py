"""Local API integration checks. Synthetic responses never go to production."""
import json,uuid,urllib.request,urllib.error,http.cookiejar,os
from pathlib import Path
base='http://localhost:8766'
jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def request(path,body=None,origin=base):
 data=json.dumps(body).encode() if body is not None else None
 req=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json','Origin':origin})
 try:
  with client.open(req) as r:return r.status,r.read().decode(),r.headers
 except urllib.error.HTTPError as e:return e.code,e.read().decode(),e.headers
assert request('/api/admin/responses')[0]==401
assert request('/api/admin/responses?format=csv')[0]==401
assert request('/api/submit',{},'https://untrusted.example')[0]==403
assert request('/api/submit',{})[0]==400
assert request('/api/admin/login',{'password':'wrong'})[0]==401
c=json.loads(Path('app/current-review/data.json').read_text());ids=[x['id'] for x in c]
timestamp='2026-09-07T00:00:00.000Z'
sid=str(uuid.uuid4());payload={'schema':'public-final-human-v2','id':sid,'age':'20대','startedAt':timestamp,'order':ids,'answers':{f'{x}-{k}':{'value':'unknown','updatedAt':timestamp} for k in ['face','preservation'] for x in ids}}
code,body,_=request('/api/submit',payload);assert code==200,(code,body)
assert request('/api/submit',payload)[0]==200
payload['age']='30대';assert request('/api/submit',payload)[0]==409
payload['id']=str(uuid.uuid4());payload['order'][0]=ids[1];assert request('/api/submit',payload)[0]==400
secret=Path('.dev.vars').read_text().split('=',1)[1].strip().strip('"')
code,body,headers=request('/api/admin/login',{'password':secret});assert code==200,(code,body)
assert 'HttpOnly' in headers.get('Set-Cookie','')
code,body,_=request('/api/admin/responses');assert code==200,(code,body)
assert sum(r['id']==sid for r in json.loads(body)['rows'])==1
code,body,_=request('/api/admin/responses?format=csv');assert code==200
assert body.count(sid)==32
assert 'unknown' in body and 'SHA256' in body
assert request('/api/admin/logout',{})[0]==200
assert request('/api/admin/responses')[0]==401
Path('.wrangler/test-submission-id').write_text(sid)
print('PASS: validation, cross-origin rejection, persistence, retry deduplication, conflict handling, admin login, protected CSV (32 rows), logout. Local synthetic data only.')
