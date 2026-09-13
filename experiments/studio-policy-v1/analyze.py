"""Analyze all eight website outputs with the previously specified face metrics."""
import hashlib,importlib.util,json
from pathlib import Path
import numpy as np
import torch,lpips
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent;REPO=R.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(R/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def image(p):
 with Image.open(p) as im:
  assert im.size==(512,768)
  return np.asarray(im.convert('RGB'),dtype=np.float32)/255
plan=json.loads((R/'plan.json').read_text());ledger=json.loads((R/'calls.json').read_text())
assert sha(R/'PROTOCOL.md')==plan['protocol_sha256']
assert sha(REPO/'local-studio/server.py')==plan['server_sha256']
assert len(ledger['calls'])==8
assert sha(R/'reference-42.png')==sha(R/'reference-314.png')
spec=importlib.util.spec_from_file_location('frozen',REPO/'experiments/nonhuman-followup-v1/metrics/analyze.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
torch.set_num_threads(2);net=lpips.LPIPS(net='alex',version='0.1',verbose=False).cpu().eval()
roi=plan['roi'];ref=image(R/'reference-42.png');control=M.face(M.crop(ref,roi),M.crop(ref,roi),net)
assert control['mae']==0 and control['ssim']==1 and abs(control['lpips'])<1e-7
rows=[]
for c in ledger['calls']:
 v=c['version'];folder=R/c['artifact_dir'];im=folder/'output.png';inp=folder/'input.png';prompt=folder/'prompt.txt'
 assert sha(im)==v['output_sha256'] and sha(inp)==v['input_sha256']
 assert prompt.read_text()==v['prompt']
 assert v['state']==plan['states'][c['stage']-1]
 if c['mode']=='sequential' and c['stage']>1:
  prior=next(x for x in ledger['calls'] if x['seed']==c['seed'] and x['mode']==c['mode'] and x['stage']==c['stage']-1)
  assert v['input_version']==prior['version']['id'] and v['input_sha256']==prior['version']['output_sha256']
 else:assert v['input_version'] is None and v['input_sha256']==sha(R/f"reference-{c['seed']}.png")
 rows.append({'seed':c['seed'],'mode':c['mode'],'stage':c['stage'],'project':c['project'],'version':v['id'],'artifact_dir':c['artifact_dir'],'seconds':v['seconds'],'metrics':M.face(M.crop(ref,roi),M.crop(image(im),roi),net),'input_sha256':v['input_sha256'],'output_sha256':v['output_sha256'],'prompt_sha256':sha(prompt)})
assert len({r['output_sha256'] for r in rows})==8
final=[r for r in rows if r['stage']==3]
for seed in plan['seeds']:
 pair=[r for r in final if r['seed']==seed]
 assert len(pair)==2 and pair[0]['prompt_sha256']==pair[1]['prompt_sha256']
means={mode:{k:float(np.mean([r['metrics'][k] for r in final if r['mode']==mode])) for k in ['mae','ssim','lpips']} for mode in ['regenerate','sequential']}
path_seconds={str(seed):{mode:sum(r['seconds'] for r in rows if r['mode']==mode and r['seed']==seed) for mode in means} for seed in plan['seeds']}
save('results.json',{'rows':rows,'final':final,'means':means,'path_seconds':path_seconds,'roi':roi,'control':control})
save('verification.json',{'passed':True,'outputs':8,'final_outputs':4,'input_lineage_verified':True,'final_prompts_equal':True,'final_states_equal':True,'protocol_sha256':sha(R/'PROTOCOL.md'),'analysis_sha256':sha(Path(__file__)),'server_sha256':plan['server_sha256'],'reference_control':control,'source':'website HTTP endpoints used by the UI'})
for seed in plan['seeds']:
 a=next(r for r in final if r['seed']==seed and r['mode']=='regenerate');b=next(r for r in final if r['seed']==seed and r['mode']=='sequential')
 sheet=Image.new('RGB',(1536,802),'white');draw=ImageDraw.Draw(sheet)
 for i,(label,p) in enumerate([('ORIGINAL',R/f'reference-{seed}.png'),('REGENERATE',R/a['artifact_dir']/'output.png'),('SEQUENTIAL',R/b['artifact_dir']/'output.png')]):
  draw.text((i*512+8,9),label,fill='black');sheet.paste(Image.open(p).convert('RGB'),(i*512,34))
 sheet.save(R/f'comparison-{seed}.png')
lines=['# 사이트 생성 경로의 두 모드 비교','','2026-09-14. 같은 원본 P04·시드 42/314·최종 요구를 사용해 사이트의 순차 생성 3회와 일괄 재생성 1회를 비교했다. 총 8개 새 출력이다.','','## 고정 얼굴 영역 지표','','ROI [176,44,336,224]. MAE·LPIPS는 낮을수록, SSIM은 높을수록 원본에 가깝다.','','| 시드 | 모드 | MAE ↓ | SSIM ↑ | LPIPS ↓ |','| --- | --- | ---: | ---: | ---: |']
for r in final:
 m=r['metrics'];lines.append(f"| {r['seed']} | {r['mode']} | {m['mae']:.6f} | {m['ssim']:.6f} | {m['lpips']:.6f} |")
for mode,m in means.items():lines.append(f"| 평균 | {mode} | {m['mae']:.6f} | {m['ssim']:.6f} | {m['lpips']:.6f} |")
lines+=['','## 경로 전체 시간','','| 시드 | 일괄 1회(초) | 순차 3회 합계(초) |','| --- | ---: | ---: |']
for seed,v in path_seconds.items():lines.append(f"| {seed} | {v['regenerate']:.2f} | {v['sequential']:.2f} |")
lines+=['','## 입력 검증','','일괄 입력은 최초 원본, 순차 2·3단계 입력은 직전 출력과 해시가 일치했다. 최종 프롬프트와 상태가 방법 간 같고, 8개 출력이 모두 고유함을 확인했다. 원본 대조 MAE=0, SSIM=1, LPIPS≈0을 확인했다.','','## 범위','','한 합성 인물과 두 시드의 사이트 생성 경로 비교다. 2026-09-09 CLI 비교와 별도 결과로 관리한다. 생성 기록은 API 경로에서 수집하고 모드 선택·시드 저장·결과 비교 화면은 브라우저에서 검수한다. 시간은 모델 로딩과 저장을 포함한 생성 요청 처리 시간이다.','','[시드 42 이미지](comparison-42.png) · [시드 314 이미지](comparison-314.png) · [전체 수치](results.json) · [검증](verification.json) · [계획](PROTOCOL.md)']
(R/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'means':means,'path_seconds':path_seconds},indent=2))
