"""Read-only production checks: public access, images, protected admin export."""
import json,sys,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
base=sys.argv[1].rstrip('/')
jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def req(path,body=None):
 data=json.dumps(body).encode() if body is not None else None
 r=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json','Origin':base,'User-Agent':'Mozilla/5.0'})
 try:
  with client.open(r) as response:return response.status,response.read(),response.headers
 except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
assert req('/survey')[0]==200
assert req('/admin')[0]==200
assert req('/api/admin/responses')[0]==401
assert req('/api/admin/responses?format=csv')[0]==401
assert req('/api/submit',{})[0]==400
c=json.loads(Path('app/current-review/data.json').read_text())
for image in [c[0]['referenceCrop'],c[0]['candidateCrop'],c[-1]['candidate']]:
 code,body,h=req(image);assert code==200 and h.get('Content-Type','').startswith('image/'),(image,code)
secret=Path('.dev.vars').read_text().split('=',1)[1].strip().strip('"')
code,body,h=req('/api/admin/login',{'password':secret});assert code==200,(code,body)
assert 'Secure' in h.get('Set-Cookie','') and 'HttpOnly' in h.get('Set-Cookie','')
code,body,_=req('/api/admin/responses');assert code==200,(code,body)
print('Saved responses:',json.loads(body)['total'])
assert req('/api/admin/responses?format=csv')[0]==200
assert req('/api/admin/logout',{})[0]==200
assert req('/api/admin/responses')[0]==401
print('PASS: public survey, representative images, server validation, admin authentication, secure cookie, D1 read, CSV, logout. No synthetic production responses created.')
