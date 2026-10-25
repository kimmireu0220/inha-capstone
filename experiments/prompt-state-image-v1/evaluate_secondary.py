"""Post-hoc whole-packet 7B check; primary ratings remain unchanged."""
import importlib.metadata,json,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent;REPO=R.parents[1];sys.path.insert(0,str(R.parent/'action-image-v1'))
from evaluate import packet,parse,save,sha
from goals import prompt
MODEL='mlx-community/Qwen2.5-VL-7B-Instruct-4bit';REVISION='fdcc572e8b05ba9daeaf71be8c9e4267c826ff9b'
def main():
 data=packet(R);primary=json.loads((R/'ai-ratings.json').read_text());assert set(primary['ratings'])==set(data['items'])
 inputs=dict(posthoc=True,model=MODEL,revision=REVISION,temperature=0,max_tokens=400,evaluation_plan_sha256=sha(R/'evaluation-plan.json'),source_sha256={n:sha(R/n) for n in ['evaluate_secondary.py','EVALUATOR_CHECK.md','ai-ratings.json']},helper_sha256={n:sha(R.parent/'action-image-v1'/n) for n in ['evaluate.py','goals.py']})
 frozen=R/'secondary-frozen.json'
 if frozen.exists():assert json.loads(frozen.read_text())==inputs
 else:save(frozen,inputs)
 from huggingface_hub import snapshot_download
 from mlx_vlm import load,generate
 from mlx_vlm.prompt_utils import apply_chat_template
 from mlx_vlm.utils import load_config
 from PIL import Image
 path=snapshot_download(MODEL,revision=REVISION,local_files_only=True);model,processor=load(path);config=load_config(path)
 output=R/'ai-ratings-7b.json';result=json.loads(output.read_text()) if output.exists() else dict(inputs=inputs,ratings={},versions={n:importlib.metadata.version(n) for n in ['mlx-vlm','mlx','transformers']});assert result['inputs']==inputs
 for key,item in sorted(data['items'].items()):
  if key in result['ratings']:continue
  formatted=apply_chat_template(processor,config,prompt(item['goals']),num_images=1)
  with Image.open(item['image']) as source:im=source.convert('RGB')
  started=time.monotonic();response=generate(model,processor,formatted,[im],max_tokens=400,temperature=0,verbose=False);raw=response.text if hasattr(response,'text') else str(response);scores,error=parse(raw)
  result['ratings'][key]=dict(scores=scores,raw=raw,parse_error=error,seconds=time.monotonic()-started);save(output,result);print('SECONDARY',len(result['ratings']),'/',len(data['items']),scores,flush=True)
if __name__=='__main__':main()
