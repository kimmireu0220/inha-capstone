"""Loopback-only image editor. File-backed state, one GPU job at a time."""
import base64,copy,io,json,os,secrets,subprocess,threading,time,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from PIL import Image,ImageOps,UnidentifiedImageError
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent; DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
PORT=int(os.environ.get('STUDIO_PORT','8770'));TOKEN=secrets.token_urlsafe(32)
LOCK=threading.RLock();GPU=threading.Lock();JOBS={}
DEFAULT={'shirt_color':'original','background':'original','pin':'original'}
Image.MAX_IMAGE_PIXELS=24000000

def uid():return uuid.uuid4().hex

def save(p,d):
 tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2));tmp.replace(p)

def folder(pid):
 if not isinstance(pid,str) or len(pid)!=32 or any(c not in '0123456789abcdef' for c in pid):raise ValueError('작업을 찾을 수 없습니다.')
 return DATA/pid

def read(pid):return json.loads((folder(pid)/'project.json').read_text())

def valid_state(s):
 if not isinstance(s,dict) or set(s)!=set(DEFAULT) or any(not isinstance(v,str) or not v.strip() or len(v)>120 or '\n' in v for v in s.values()):raise ValueError('설정을 확인해주세요. 세 항목 모두 짧은 값이 필요합니다.')
 return {k:v.strip() for k,v in s.items()}

def prompt_for(s):
 parts=[]
 if s['shirt_color']=='original':parts.append('Keep the original shirt unchanged.')
 else:parts.append('Set the existing shirt color to '+s['shirt_color']+'; preserve its shape and fabric.')
 if s['background']=='original':parts.append('Keep the original background unchanged.')
 else:parts.append('Set the background to '+s['background']+'.')
 if s['pin']=='original':parts.append('Keep the original accessories unchanged.')
 elif s['pin']=='none':parts.append('There must be no pin on the shirt.')
 else:parts.append('Add exactly one small '+s['pin']+' circular pin on the viewer-right chest.')
 return 'Edit only the supplied original image. Preserve face, facial features, expression, gaze, natural skin texture, hair, pose, framing and lighting on the person. Do not beautify or smooth the face. No text, logos or watermarks. Apply these complete current requirements; preserve everything else:\n'+'\n'.join('- '+x for x in parts)

def create_project(raw,name):
 with Image.open(io.BytesIO(raw)) as im:
  if im.format not in ('PNG','JPEG','WEBP'):raise ValueError('PNG, JPG, WebP 이미지를 사용해주세요.')
  im=ImageOps.exif_transpose(im).convert('RGB'); im.load()
  if min(im.size)<128:raise ValueError('가로와 세로가 128픽셀 이상인 이미지를 사용해주세요.')
  original=im.copy(); scale=min(512/im.width,768/im.height,1); w=max(128,int(im.width*scale)//16*16);h=max(128,int(im.height*scale)//16*16)
  im=im.resize((w,h),Image.Resampling.LANCZOS)
 pid=uid();p=folder(pid);p.mkdir();original.save(p/'original.png');im.save(p/'reference.png')
 d={'id':pid,'name':name[:80],'created':time.time(),'revision':0,'state':dict(DEFAULT),'current_version':None,'versions':[],'messages':[],'size':[w,h],'active_job':None}
 save(p/'project.json',d);return d

def change(pid,revision,fn):
 with LOCK:
  d=read(pid)
  if d['revision']!=revision:raise ValueError('설정이 변경됐습니다. 새로고침 후 다시 시도해주세요.')
  if d['active_job']:raise ValueError('현재 작업이 끝난 뒤 변경할 수 있습니다.')
  fn(d);d['revision']+=1;save(folder(pid)/'project.json',d);return d

def start_job(pid,revision,kind,request=''):
 if not GPU.acquire(blocking=False):raise ValueError('다른 작업을 처리 중입니다. 완료 후 다시 시도해주세요.')
 try:
  with LOCK:
   d=read(pid)
   if d['revision']!=revision or d['active_job']:raise ValueError('설정이 변경됐거나 작업 중입니다. 새로고침해주세요.')
   jid=uid();job={'id':jid,'project':pid,'kind':kind,'status':'running','started':time.time(),'message':'요청을 해석하고 있어요.' if kind=='chat' else '원본에서 새 이미지를 만들고 있어요.'}
   JOBS[jid]=job;d['active_job']=jid;d['revision']+=1;save(folder(pid)/'project.json',d)
  threading.Thread(target=worker,args=(job,copy.deepcopy(d),request),daemon=True).start();return job
 except Exception:GPU.release();raise

def worker(job,d,request):
 p=folder(d['id']);jp=p/job['id'];jp.mkdir();result=None
 try:
  if job['kind']=='chat':
   proc=subprocess.run([str(REPO/'.venv-local-prompt/bin/python'),str(ROOT/'state_model.py')],input=json.dumps({'state':d['state'],'request':request},ensure_ascii=False),text=True,capture_output=True,timeout=120)
   (jp/'model.log').write_text(proc.stdout+'\n'+proc.stderr)
   if proc.returncode:raise ValueError('요청 해석에 실패했습니다. 다시 시도하거나 현재 설정을 직접 수정해주세요.')
   raw=proc.stdout.strip();a=raw.find('{');b=raw.rfind('}');parsed=json.loads(raw[a:b+1])
   if parsed.get('clarification'):
    with LOCK:
     latest=read(d['id']);latest['active_job']=None;latest['revision']+=1
     latest['messages'].append({'request':request,'state':latest['state'],'reply':str(parsed['clarification'])[:200],'applied':False,'created':time.time()})
     save(p/'project.json',latest);job.update(status='needs_input',message=str(parsed['clarification'])[:200])
    return
   result=valid_state(parsed['state'])
  else:
   prompt=prompt_for(d['state']);(jp/'prompt.txt').write_text(prompt);seed=secrets.randbelow(2147483647)
   cmd=[str(REPO/'.venv-local-image/bin/mflux-generate-flux2-edit'),'--model','Runpod/FLUX.2-klein-4B-mflux-4bit','--base-model','flux2-klein-4b','--quantize','4','--low-ram','--image-paths',str(p/'reference.png'),'--prompt-file',str(jp/'prompt.txt'),'--width',str(d['size'][0]),'--height',str(d['size'][1]),'--steps','4','--seed',str(seed),'--metadata','--output',str(jp/'output.png')]
   with (jp/'model.log').open('w') as f:proc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=900)
   if proc.returncode or not (jp/'output.png').exists():raise ValueError('이미지를 만들지 못했습니다. 기존 이미지와 설정은 보존됐습니다.')
   with Image.open(jp/'output.png') as im:im.verify()
   result={'id':job['id'],'parent':d['current_version'],'state':d['state'],'image':job['id']+'/output.png','seed':seed,'prompt':prompt,'created':time.time(),'seconds':time.time()-job['started']}
  with LOCK:
   latest=read(d['id'])
   if job['kind']=='chat':
    latest['state']=result;latest['messages'].append({'request':request,'state':result,'reply':parsed.get('message','적용 완료'),'applied':True,'created':time.time()})
   else:latest['versions'].append(result);latest['current_version']=result['id']
   latest['active_job']=None;latest['revision']+=1;save(p/'project.json',latest)
   job.update(status='done',message=parsed.get('message','적용 완료') if job['kind']=='chat' else '새 이미지가 완성됐어요.')
 except Exception as e:
  with LOCK:
   latest=read(d['id']);latest['active_job']=None;latest['revision']+=1;save(p/'project.json',latest)
   job.update(status='error',message=str(e)[:240] if isinstance(e,ValueError) else '처리 중 오류가 발생했습니다. 기존 작업은 보존됐습니다.')
 finally:
  job['seconds']=time.time()-job['started'];save(jp/'job.json',job);GPU.release()

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,code,d):
  data=json.dumps(d,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def safe_host(self):return self.headers.get('Host') in (f'127.0.0.1:{PORT}',f'localhost:{PORT}')
 def do_GET(self):
  if not self.safe_host():return self.reply(403,{'error':'로컬 접속만 허용됩니다.'})
  path=self.path.split('?')[0]
  try:
   if path=='/api/bootstrap':
    with LOCK:projects=[read(p.name) for p in DATA.iterdir() if p.is_dir() and (p/'project.json').exists()]
    return self.reply(200,{'token':TOKEN,'projects':sorted(projects,key=lambda d:d['created'],reverse=True),'jobs':JOBS})
   if path.startswith('/media/'):
    rel=Path(path.removeprefix('/media/'));p=(DATA/rel).resolve()
    if not p.is_relative_to(DATA.resolve()) or p.suffix!='.png':return self.reply(404,{'error':'없음'})
   elif path=='/':p=ROOT/'dist/index.html'
   elif path in ['/app.js','/style.css']:p=ROOT/'dist'/path[1:]
   else:return self.reply(404,{'error':'없음'})
   data=p.read_bytes();self.send_response(200);self.send_header('Content-Type','image/png' if p.suffix=='.png' else 'text/javascript' if p.suffix=='.js' else 'text/css' if p.suffix=='.css' else 'text/html; charset=utf-8');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
  except (ValueError,FileNotFoundError):self.reply(404,{'error':'작업을 찾을 수 없습니다.'})
 def do_POST(self):
  if not self.safe_host() or self.headers.get('X-Studio-Token')!=TOKEN:return self.reply(403,{'error':'페이지를 새로고침해주세요.'})
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<22000000:raise ValueError('이미지는 15MB 이하로 업로드해주세요.')
   b=json.loads(self.rfile.read(length));path=self.path
   if path=='/api/create':
    raw=(REPO/'experiments/trigger-validation-v1/P04/reference.png').read_bytes() if b.get('sample') else base64.b64decode(b['image'],validate=True)
    return self.reply(200,create_project(raw,'연구 샘플 P04' if b.get('sample') else str(b.get('name','새 작업'))))
   pid=b['project'];rev=b['revision']
   if path=='/api/state':
    s=valid_state(b['state']);return self.reply(200,change(pid,rev,lambda d:d.update(state=s)))
   if path=='/api/restore':
    def restore(d):
     v=next((v for v in d['versions'] if v['id']==b['version']),None)
     if v is None:raise ValueError('버전을 찾을 수 없습니다.')
     d.update(state=copy.deepcopy(v['state']),current_version=v['id'])
    return self.reply(200,change(pid,rev,restore))
   if path=='/api/chat':
    request=b.get('request','').strip()
    if not request or len(request)>1000:raise ValueError('요청을 1~1000자로 입력해주세요.')
    return self.reply(202,start_job(pid,rev,'chat',request))
   if path=='/api/generate':return self.reply(202,start_job(pid,rev,'image'))
   self.reply(404,{'error':'없는 요청입니다.'})
  except (ValueError,KeyError,UnidentifiedImageError,FileNotFoundError) as e:self.reply(400,{'error':str(e)[:240]})
  except Exception:self.reply(500,{'error':'작업을 처리하지 못했습니다.'})

if __name__=='__main__':
 # Interrupted jobs must never leave the persistent project locked.
 for p in DATA.glob('*/project.json'):
  d=json.loads(p.read_text())
  if d.get('active_job'):d.update(active_job=None,revision=d['revision']+1);save(p,d)
 print(f'Local studio: http://localhost:{PORT}',flush=True)
 ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
