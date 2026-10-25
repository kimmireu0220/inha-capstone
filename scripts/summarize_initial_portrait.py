"""Recheck six historical ten-stage series and matched original-based endpoints."""
import hashlib,importlib.util,json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'experiments/nonhuman-followup-v1/extension-metrics/results.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 spec=importlib.util.spec_from_file_location('initial_metrics',ROOT/'experiments/nonhuman-followup-v1/metrics/analyze.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 data=json.loads(SOURCE.read_text());network=m.lpips.LPIPS(net='alex',version='0.1',verbose=False).cpu().eval();rows=[];error=0.;checked={};cache={}
 def sample(key):
  if key in cache:return cache[key]
  row=data['rows'][key];p=Path(row['paths'][0]);ref=Path(row['reference']);assert sha(p)==row['sha256'];assert sha(ref)==row['reference_sha256'];checked[str(p.relative_to(ROOT))]=sha(p);checked[str(ref.relative_to(ROOT))]=sha(ref)
  actual=m.measure(m.image(p),m.image(ref),row['roi'],network,False)
  nonlocal error
  for mode in ['fixed','1','3','6']:
   for metric in m.FACE_KEYS:error=max(error,abs(actual['face'][mode][metric]-row['face'][mode][metric]))
  assert error<1e-6
  result={'path':str(p.relative_to(ROOT)),'sha256':sha(p),'face':actual['face']};cache[key]=result;return result
 people=['P01','P02','P03','P04','P05','P06']
 for person in people:
  a,b=sample(data['summary'][person]['final_id']),sample(data['summary'][person+'-end-only']['final_id'])
  rows.append(dict(person=person,sequential=a,original_based=b))
 series=[]
 for person in people:
  for stage in range(1,11):
   matches=[x for x in data['trajectories'] if x['branch']==person and x['stage']==stage];assert len(matches)==1
   series.append(dict(person=person,stage=stage,**sample(matches[0]['id'])))
 modes={}
 for mode in ['fixed','1','3','6']:
  modes[mode]={key:sum((r['sequential']['face'][mode][key]>r['original_based']['face'][mode][key]) if key!='ssim' else (r['sequential']['face'][mode][key]<r['original_based']['face'][mode][key]) for r in rows) for key in m.FACE_KEYS}
 stages={str(n):{key:statistics.mean(r['face']['3'][key] for r in series if r['stage']==n) for key in m.FACE_KEYS} for n in range(1,11)}
 result={'historical_reanalysis':True,'new_image_calls':0,'people':6,'stages_per_person':10,'paired_endpoints':6,'sequential_outputs':60,'total_measured_outputs':len(cache),'source_sha256':{str(SOURCE.relative_to(ROOT)):sha(SOURCE),'experiments/nonhuman-followup-v1/metrics/analyze.py':sha(ROOT/'experiments/nonhuman-followup-v1/metrics/analyze.py')},'verifier_sha256':sha(Path(__file__)),'checked_images':checked,'max_metric_replay_error':error,'original_based_favorable_pairs':modes,'stage_registered_means':stages,'sequential_rows':series,'rows':rows}
 (ROOT/'paper/initial-portrait-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pairs':6,'outputs':len(cache),'max_error':error,'favorable':modes,'stage_means':stages}))
if __name__=='__main__':main()
