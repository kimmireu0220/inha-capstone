"""Measure frozen complete prompts, including common preservation text."""
import hashlib,importlib.metadata,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 from huggingface_hub import snapshot_download
 from transformers import AutoTokenizer
 models=json.loads((REPO/'experiments/operation-scope-validation-v1/models.json').read_text());info=models['qwen3'];folder=Path(snapshot_download(info['model'],revision=info['revision'],local_files_only=True));tok=AutoTokenizer.from_pretrained(folder)
 data=json.loads((ROOT/'prepared.json').read_text());rows=[]
 for row in data['lengths']:
  sizes={mode:dict(characters=len(p),words=len(p.split()),tokens=len(tok.encode(p,add_special_tokens=False))) for mode,p in row['prompts'].items()}
  rows.append(dict(history=row['history'],request_index=row['request_index'],lengths=sizes))
 final=[r for r in rows if r['request_index']==4]
 def group(selected):
  return {mode:{unit:sum(r['lengths'][mode][unit] for r in selected)/len(selected) for unit in ['characters','words','tokens']} for mode in ['full_history','unchecked_state','checked_state']}
 result=dict(model=info,prepared_sha256=sha(ROOT/'prepared.json'),script_sha256=sha(Path(__file__)),tokenizer_sha256={p.name:sha(p) for p in folder.iterdir() if p.name in ['tokenizer.json','tokenizer_config.json']},versions={n:importlib.metadata.version(n) for n in ['transformers','tokenizers']},actual_new_language_model_calls=0,request_prefixes=12,rows=rows,all_prefix_means=group(rows),final_request_means=group(final))
 (ROOT/'prompt-lengths.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['final_request_means']))
if __name__=='__main__':main()
