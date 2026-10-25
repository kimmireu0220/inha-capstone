"""Freeze complete history/state comparison before generating any images."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'local-studio'))
from request_state import render_prompt,PRESERVE

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 paths=['experiments/single-extraction-validation-v1/benchmark.json','experiments/single-extraction-validation-v1/results-qwen3.json','local-studio/request_state.py','experiments/prompt-state-image-v1/PROTOCOL.md','experiments/prompt-state-image-v1/prepare.py']
 paths += [f'experiments/state-tracking-v2/references/{p}.png' for p in ['R01','R02']]
 inputs={p:sha(REPO/p) for p in paths}
 bench=json.loads((REPO/paths[0]).read_text())['histories']; methods=json.loads((REPO/paths[1]).read_text())['methods']
 def lookup(method,h,n):return next(r for r in methods[method]['rows'] if r['dialogue']==h and r['turn']==n)
 lengths=[]; conditions=[]
 for hi,(h,requests) in enumerate(bench.items()):
  for n in range(1,len(requests)+1):
   raw=('Edit only the supplied photograph. Apply the following requests in chronological order to obtain the final current appearance. Later direct instructions override earlier ones. References to the source or original mean the supplied photograph.\n'+ '\n'.join(f'Request {i+1}: '+r['request'] for i,r in enumerate(requests[:n]))+'\n'+PRESERVE)
   texts={'full_history':raw,'unchecked_state':render_prompt(lookup('json_first_only',h,n)['observed']),'checked_state':render_prompt(lookup('single_extraction_checked',h,n)['observed'])}
   lengths.append(dict(history=h,request_index=n,prompts=texts))
   if n!=len(requests):continue
   for pi,person in enumerate(['R01','R02']):
    modes=list(texts); shift=(hi+pi)%3; modes=modes[shift:]+modes[:shift]
    for mode in modes:
     prompt=texts[mode]; key=hashlib.sha256((inputs[f'experiments/state-tracking-v2/references/{person}.png']+'\n'+prompt).encode()).hexdigest()[:16]
     conditions.append(dict(id=f'{person}-{h}-{mode}',job='img-'+key,person=person,history=h,turn=n,mode=mode,prompt=prompt,expected_state=lookup('single_extraction_checked',h,n)['expected']))
 prepared=dict(planned_backend='builtin',condition_count=len(conditions),inputs=inputs,conditions=conditions,lengths=lengths)
 path=ROOT/'prepared.json'
 if path.exists():assert json.loads(path.read_text())==prepared,'Frozen inputs changed'
 else:save(path,prepared)
 print('Frozen',len(conditions),'conditions;',len({r['job'] for r in conditions}),'unique image jobs')
if __name__=='__main__':main()
