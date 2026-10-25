"""One model extraction followed by explicit instruction checks and prompt rendering."""
import argparse
import importlib.util
import json
from pathlib import Path

from request_state import INITIAL,VALUES,SYSTEM,EXAMPLES,StateExtractor,render_prompt

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline_instruction_checks',REPO/'experiments/instruction-eligibility-v1/method.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)

def process_request(prior,request,extractor):
    if not isinstance(prior,dict) or set(prior)!=set(INITIAL) or any(v not in VALUES[k]+['original'] for k,v in prior.items()):
        raise ValueError('State must contain all six supported fields with valid values')
    if not isinstance(request,str) or not request.strip():raise ValueError('Request is empty')
    raw=extractor.ask(SYSTEM,request,max_tokens=260,examples=EXAMPLES)
    state,trace=checks.update(dict(prior),request,[raw])
    return dict(state=state,prompt=render_prompt(state),response=raw,trace=trace,model_calls=1)

def load_state(path):
    if path is None:return dict(INITIAL)
    stored=json.loads(path.read_text())
    return stored.get('state',stored) if isinstance(stored,dict) else stored

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',type=Path,help='State JSON; defaults to original values')
    parser.add_argument('--request',required=True)
    parser.add_argument('--model',choices=['qwen3','llama32'],default='qwen3')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    models=json.loads((REPO/'experiments/operation-scope-validation-v1/models.json').read_text())
    info=models[args.model]
    from huggingface_hub import snapshot_download
    from mlx_lm import load
    extractor=StateExtractor.__new__(StateExtractor)
    extractor.model,extractor.tokenizer=load(snapshot_download(info['model'],revision=info['revision'],local_files_only=True))
    prior=load_state(args.state)
    result=process_request(prior,args.request,extractor)
    output=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(output)
    else:print(output,end='')

if __name__=='__main__':main()
