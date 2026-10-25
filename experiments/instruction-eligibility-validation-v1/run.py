"""Fresh eligibility validation, separate from its 32-request development data."""
import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value
parent=module('eligibility_parent_run',ROOT.parent/'operation-scope-validation-v1/run.py')
method=module('eligibility_final_method',ROOT.parent/'instruction-eligibility-v1/method.py')

def score(histories,records):
    methods=parent.score(histories,records)
    rows=[];final=0
    for name,requests in histories.items():
        state=dict(parent.plain.INITIAL);gold=dict(parent.plain.INITIAL)
        for i,item in enumerate(requests,1):
            r=records[f'{name}-{i}'];assert r['request']==item['request']
            state,trace=method.update(state,item['request'],[r['first'],r['second']])
            gold.update(item['updates'])
            rows.append(dict(dialogue=name,turn=i,observed=dict(state),expected=dict(gold),exact=state==gold,
                correct_slots=sum(state[k]==gold[k] for k in gold),trace=trace))
        final+=state==gold
    methods['eligible_normalization']=dict(exact_turns=sum(r['exact'] for r in rows),turns=len(rows),
        correct_slots=sum(r['correct_slots'] for r in rows),slots=len(rows)*6,exact_final_dialogues=final,
        new_errors_vs_baseline=sum(a['exact'] and not b['exact'] for a,b in zip(methods['baseline_restore']['rows'],rows,strict=True)),rows=rows)
    return methods

def freeze():
    data=parent.freeze();paths=set(data['sha256'])
    paths|={str((ROOT/n).relative_to(REPO)) for n in ['run.py','benchmark.json','PROTOCOL.md','test_design.py']}
    paths|={str((ROOT.parent/'instruction-eligibility-v1'/n).relative_to(REPO)) for n in ['method.py','test_method.py','PROTOCOL.md']}
    return dict(data,sha256={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in sorted(paths)})

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['qwen3','llama32','all'],default='all');p.add_argument('--freeze-only',action='store_true');args=p.parse_args()
    frozen=json.loads(json.dumps(freeze()));target=ROOT/'frozen.json'
    if target.exists():assert json.loads(target.read_text())==frozen,'Frozen inputs changed'
    else:parent.core.source.save(target,frozen)
    if args.freeze_only:print('Frozen 16 new requests and all methods');return
    histories=json.loads((ROOT/'benchmark.json').read_text())['histories']
    for key,info in frozen['models'].items():
        if args.model not in ['all',key]:continue
        path=ROOT/f'transcripts-{key}.json';records=json.loads(path.read_text()) if path.exists() else {};extractor=None
        for name,requests in histories.items():
            for i,item in enumerate(requests,1):
                rid=f'{name}-{i}'
                if rid in records:assert records[rid]['request']==item['request'];continue
                if extractor is None:
                    from huggingface_hub import snapshot_download
                    from mlx_lm import load
                    extractor=parent.core.source.base.StateExtractor.__new__(parent.core.source.base.StateExtractor)
                    extractor.model,extractor.tokenizer=load(snapshot_download(info['model'],revision=info['revision'],local_files_only=True))
                start=time.monotonic()
                first=extractor.ask(parent.core.source.base.SYSTEM,item['request'],max_tokens=260,examples=parent.core.source.base.EXAMPLES)
                user=item['request']+'\nProposed patch: '+first+'\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
                second=extractor.ask(parent.core.source.base.SYSTEM,user,max_tokens=260,examples=parent.core.source.base.EXAMPLES)
                records[rid]=dict(request=item['request'],first=first,second_user=user,second=second,seconds=time.monotonic()-start)
                parent.core.source.save(path,records);print('SAVED',key,rid,flush=True)
        parent.core.source.save(ROOT/f'results-{key}.json',dict(complete=True,model=info,actual_model_calls=len(records)*2,methods=score(histories,records)))
        print('COMPLETE',key,len(records),flush=True)
        del extractor;gc.collect()
        import mlx.core as mx
        mx.clear_cache()

if __name__=='__main__':main()
