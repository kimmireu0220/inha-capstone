import json,hashlib,importlib.util
from pathlib import Path
import numpy as np
import torch,lpips
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent;repo=R.parents[1]
spec=importlib.util.spec_from_file_location('frozen',repo/'experiments/nonhuman-followup-v1/metrics/analyze.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
def image(p):
 with Image.open(p) as im:
  assert im.size==(512,768)
  return np.asarray(im.convert('RGB'),dtype=np.float32)/255
def save(n,d):(R/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
plan=json.loads((R/'plan.json').read_text()); assert M.sha(R/'PROTOCOL.md')==plan['protocol_sha256']; assert M.sha(R/'reference.png')==plan['reference_sha256']
torch.set_num_threads(2);net=lpips.LPIPS(net='alex',version='0.1',verbose=False).cpu().eval();ref=image(R/'reference.png');roi=[176,44,336,224]
control=M.face(M.crop(ref,roi),M.crop(ref,roi),net);assert control['mae']==0 and control['ssim']==1 and abs(control['lpips'])<1e-7
rows=[]
for j in plan['jobs']:
 p=R/j['output'];log=json.loads(p.with_suffix('.call.json').read_text());assert log['exit_code']==0 and M.sha(p)==log['output_sha256'] and M.sha(R/j['input'])==log['input_sha256'];assert M.sha(R/j['prompt_file'])==j['prompt_sha256']
 assert Image.open(p).size==(512,768)
 a=image(p);v=M.face(M.crop(ref,roi),M.crop(a,roi),net)
 assert np.isclose(v['mae'],np.abs(ref[44:224,176:336]-a[44:224,176:336]).mean(),atol=1e-8)
 rows.append({**j,'metrics':v,'call_seconds':log['seconds'],'output_sha256':log['output_sha256']})
assert len(rows)==8 and len({x['output_sha256'] for x in rows})==8
final=[x for x in rows if x['arm']=='batch' or x['stage']==3]
for seed in [42,314]:
 a=next(x for x in final if x['seed']==seed and x['arm']=='batch');b=next(x for x in final if x['seed']==seed and x['arm']=='sequential');assert a['prompt_sha256']==b['prompt_sha256']
means={arm:{k:float(np.mean([x['metrics'][k] for x in final if x['arm']==arm])) for k in ['mae','ssim','lpips']} for arm in ['batch','sequential']}
paths={str(seed):{arm:sum(x['call_seconds'] for x in rows if x['seed']==seed and x['arm']==arm) for arm in ['batch','sequential']} for seed in [42,314]}
save('results.json',{'rows':rows,'means':means,'path_seconds':paths,'control':control})
state=hashlib.sha256()
for name,value in sorted(net.state_dict().items()):state.update(name.encode());state.update(str(tuple(value.shape)).encode());state.update(value.cpu().numpy().tobytes())
save('verification.json',{'passed':True,'unique_outputs':8,'input_output_hashes_verified':True,'final_prompts_equal':True,'roi':roi,'reference_control':control,'lpips_state_dict_sha256':state.hexdigest(),'analysis_sha256':M.sha(Path(__file__)),'plan_sha256':M.sha(R/'plan.json')})
# Scientific contact sheets: direct pixel paste, no generated/retouched content.
for seed in [42,314]:
 imgs=[('REFERENCE',R/'reference.png')]+[(x['arm'],R/x['output']) for x in final if x['seed']==seed]
 imgs=sorted(imgs,key=lambda z:['REFERENCE','batch','sequential'].index(z[0]))
 sheet=Image.new('RGB',(1536,800),'white');draw=ImageDraw.Draw(sheet)
 for i,(label,p) in enumerate(imgs):draw.text((i*512+8,8),label,fill='black');sheet.paste(Image.open(p).convert('RGB'),(i*512,32))
 sheet.save(R/f'comparison-{seed}.png')
print(json.dumps({'means':means,'paths':paths},indent=2))
