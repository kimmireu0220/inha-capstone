import json,time,hashlib,subprocess
from pathlib import Path
from datetime import datetime,timezone
R=Path(__file__).resolve().parent; repo=R.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((R/'plan.json').read_text());assert sha(R/'PROTOCOL.md')==plan['protocol_sha256'];assert sha(R/'reference.png')==plan['reference_sha256']
for j in plan['jobs']:
 out=R/j['output'];record=out.with_suffix('.call.json')
 if record.exists():
  old=json.loads(record.read_text());assert old['exit_code']==0 and sha(out)==old['output_sha256'];continue
 assert not out.exists();assert sha(R/j['prompt_file'])==j['prompt_sha256']
 cmd=[str(repo/'.venv-local-image/bin/mflux-generate-flux2-edit'),'--model','Runpod/FLUX.2-klein-4B-mflux-4bit','--base-model','flux2-klein-4b','--quantize','4','--low-ram','--image-paths',str(R/j['input']),'--prompt-file',str(R/j['prompt_file']),'--width','512','--height','768','--steps','4','--seed',str(j['seed']),'--metadata','--output',str(out)]
 started=datetime.now(timezone.utc).isoformat();t=time.monotonic();ih=sha(R/j['input']);print('START',j['id'],flush=True)
 with out.with_suffix('.log').open('w') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=repo)
 data={**j,'command':cmd,'started':started,'seconds':time.monotonic()-t,'exit_code':p.returncode,'input_sha256':ih,'output_sha256':sha(out) if out.exists() else None}
 record.write_text(json.dumps(data,indent=2)+'\n');print('END',j['id'],data['seconds'],p.returncode,flush=True)
 if p.returncode or not out.exists():raise SystemExit('generation failed; retained log')
