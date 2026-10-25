"""Save the exploratory 32-request evidence that selected single extraction."""
import hashlib
import json
from pathlib import Path
import run

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    source=ROOT.parent/'operation-scope-validation-v1'
    h=json.loads((source/'benchmark.json').read_text())['histories'];methods={}
    paths=[source/'benchmark.json',ROOT/'run.py']
    for model in ['qwen3','llama32']:
        p=source/f'transcripts-{model}.json';records=json.loads(p.read_text());assert len(records)==32
        all_methods=run.score(h,records)
        methods[model]={k:all_methods[k] for k in ['eligible_normalization','single_extraction_checked']}
        paths.append(p)
    run.parent.parent.core.source.save(ROOT/'development-replay.json',dict(posthoc_development=True,additional_model_calls=0,
        requests_per_model=32,methods=methods,source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths}))
    print({m:{k:r['exact_turns'] for k,r in d.items()} for m,d in methods.items()})
if __name__=='__main__':main()
