import json,hashlib,importlib.util
from pathlib import Path
import numpy as np,torch,lpips
from scipy.ndimage import gaussian_filter
from skimage.color import rgb2gray
from PIL import Image
R=Path(__file__).resolve().parent;repo=R.parents[1];source=repo/'experiments/local-policy-v1'
spec=importlib.util.spec_from_file_location('metric',repo/'experiments/nonhuman-followup-v1/metrics/analyze.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M);M.RADIUS=32
roi=[176,44,336,224];regions={k:[x//2 for x in v] for k,v in M.REGIONS.items()};modes={'fixed':None,'0.5':.5,'1.5':1.5,'3':3}
def load(p):return np.asarray(Image.open(p).convert('RGB'),dtype=np.float32)/255
def save(n,d):(R/n).write_text(json.dumps(d,indent=2)+'\n')
def skin(a,b,shift):
 ag=rgb2gray(a);bg=rgb2gray(b);ah=ag-gaussian_filter(ag,1);bh=bg-gaussian_filter(bg,1);per={}
 for k,r in regions.items():
  x=M.crop(b,r).astype(np.float64);y=M.crop(a,r,shift).astype(np.float64);diff=y-x;offset=diff.mean(axis=(0,1));res=diff-offset
  mse=float((diff**2).mean());color=float((offset**2).mean());resmse=float((res**2).mean());assert abs(mse-color-resmse)<1e-12
  per[k]={'mae':float(abs(diff).mean()),'ssim':M.ssim(x,y),'highpass_mae':float(abs(M.crop(ah,r,shift)-M.crop(bh,r)).mean()),'residual_mae':float(abs(res).mean()),'mse':mse,'mean_color_mse':color,'residual_mse':resmse,'pixels':x.shape[0]*x.shape[1],'valid':(x.shape[0]-6)*(x.shape[1]-6)}
 keys=['mae','ssim','highpass_mae','residual_mae','mse','mean_color_mse','residual_mse'];avg={k:float(np.average([v[k] for v in per.values()],weights=[v['valid' if k=='ssim' else 'pixels'] for v in per.values()])) for k in keys}
 return {'average':avg,'regions':per}
ref=load(source/'reference.png');torch.set_num_threads(2);net=lpips.LPIPS(net='alex',version='0.1',verbose=False).cpu().eval();old=json.loads((source/'results.json').read_text());rows=[]
for row in old['rows']:
 p=source/row['output'];assert M.sha(p)==row['output_sha256'];a=load(p);measure={}
 for name,sigma in modes.items():
  loc={'dx':0,'dy':0,'boundary':False} if sigma is None else M.locate(a,ref,roi,sigma)
  shift=(loc['dx'],loc['dy']);measure[name]={'location':loc,'face':M.face(M.crop(ref,roi),M.crop(a,roi,shift),net),'skin':skin(a,ref,shift)}
 for k,v in row['metrics'].items():assert abs(measure['fixed']['face'][k]-v)<1e-7
 rows.append({'id':row['id'],'arm':row['arm'],'seed':row['seed'],'stage':row['stage'],'output_sha256':row['output_sha256'],'modes':measure})
final=[r for r in rows if r['arm']=='batch' or r['stage']==3]
summary={name:{arm:{'face':{k:float(np.mean([r['modes'][name]['face'][k] for r in final if r['arm']==arm])) for k in ['mae','ssim','lpips']},'skin':{k:float(np.mean([r['modes'][name]['skin']['average'][k] for r in final if r['arm']==arm])) for k in ['mae','ssim','highpass_mae','residual_mae']}} for arm in ['batch','sequential']} for name in modes}
for sigma in [.5,1.5,3]:
 loc=M.locate(np.roll(ref,(2,3),(0,1)),ref,roi,sigma);assert (loc['dx'],loc['dy'])==(3,2),loc
ident=M.face(M.crop(ref,roi),M.crop(ref,roi),net);assert ident['mae']==0 and ident['ssim']==1 and abs(ident['lpips'])<1e-7
iskin=skin(ref,ref,(0,0));assert iskin['average']['mae']==0 and iskin['average']['ssim']==1
save('results.json',{'posthoc':True,'rows':rows,'summary':summary,'skin_regions':regions})
save('verification.json',{'passed':True,'saved_images':8,'final_images':4,'fixed_face_reproduced':True,'known_translation_recovered':True,'mse_decomposition_verified':True,'search_boundary_hits':sum(m['location']['boundary'] for r in rows for m in r['modes'].values()),'protocol_sha256':M.sha(R/'PROTOCOL.md'),'analysis_sha256':M.sha(Path(__file__)),'source_results_sha256':M.sha(source/'results.json'),'reference_sha256':M.sha(source/'reference.png')})
print(json.dumps(summary,indent=2))
