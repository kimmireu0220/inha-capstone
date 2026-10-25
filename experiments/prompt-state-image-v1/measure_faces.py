"""Measure recognition and aligned appearance independently of target scores."""
import hashlib,importlib.metadata,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sys.path.insert(0,str(ROOT.parent/'action-image-v1'))
from evaluate import packet,sha,save

def main():
 import cv2,numpy as np,torch,lpips
 from insightface.app import FaceAnalysis
 from insightface.utils.face_align import norm_crop
 spec=importlib.util.spec_from_file_location('metric_formulas',ROOT.parent/'nonhuman-followup-v1/metrics/analyze.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 packet(ROOT)
 prepared=json.loads((ROOT/'prepared.json').read_text());ledger=json.loads((ROOT/'calls.json').read_text())
 app=FaceAnalysis(name='buffalo_l',root=str(Path.home()/'.insightface'),allowed_modules=['detection','recognition'],providers=['CPUExecutionProvider']);app.prepare(ctx_id=-1,det_thresh=0.5,det_size=(640,640))
 network=lpips.LPIPS(net='alex',version='0.1',verbose=False).cpu().eval()
 def read(path):
  im=cv2.imread(str(path));assert im is not None
  found=app.get(im)
  if len(found)!=1:return len(found),None,None
  f=found[0];crop=norm_crop(im,landmark=f.kps,image_size=112)
  return 1,f.normed_embedding.astype(np.float64),cv2.cvtColor(crop,cv2.COLOR_BGR2RGB).astype(np.float32)/255
 refs={p:read(REPO/'experiments/state-tracking-v2/references'/f'{p}.png') for p in ['R01','R02']};assert all(x[0]==1 for x in refs.values())
 jobs={}
 for call in ledger['calls']:
  path=ROOT/call['folder']/'output.png';n,vec,crop=read(path);_,rv,rc=refs[call['person']]
  jobs[call['job']]={'face_count':n,'identity_similarity':None if n!=1 else float(np.dot(vec,rv)),'aligned_112':None if n!=1 else m.face(rc,crop,network),'output_sha256':sha(path)}
  print('MEASURED',call['job'],n,flush=True)
 rows=[{k:r[k] for k in ['id','person','history','turn','mode','job']}|jobs[r['job']] for r in prepared['conditions']]
 weights=hashlib.sha256()
 for name,t in network.state_dict().items():weights.update(name.encode());weights.update(t.detach().cpu().numpy().tobytes())
 result=dict(metric='buffalo_l cosine and landmark-aligned 112px RGB MAE/SSIM/LPIPS-Alex-v0.1',prepared_sha256=sha(ROOT/'prepared.json'),ledger_sha256=sha(ROOT/'calls.json'),script_sha256=sha(Path(__file__)),formula_sha256=sha(ROOT.parent/'nonhuman-followup-v1/metrics/analyze.py'),model_sha256={p.name:sha(p) for p in sorted((Path.home()/'.insightface/models/buffalo_l').glob('*.onnx'))},lpips_state_dict_sha256=weights.hexdigest(),versions={n:importlib.metadata.version(n) for n in ['insightface','onnxruntime','numpy','torch','lpips','scikit-image']},rows=rows)
 save(ROOT/'face-results.json',result)
if __name__=='__main__':main()
