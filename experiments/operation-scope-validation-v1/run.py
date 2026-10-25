"""Frozen new-request evaluation on two pinned model families."""
import argparse
import gc
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(ROOT.parent/'clause-normalization-v1'))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value
core=module('scope_validation_core',ROOT.parent/'clause-normalization-v1/run.py')
improved=module('scope_validation_method',ROOT.parent/'operation-scope-v2/method.py')
sys.path.insert(0,str(REPO/'scripts'))
import compare_plain_patch as plain

def score(histories,records):
    methods=core.score(histories,records)
    rows=[];final=0
    for name,requests in histories.items():
        state=dict(plain.INITIAL);gold=dict(plain.INITIAL)
        for i,item in enumerate(requests,1):
            record=records[f'{name}-{i}'];assert record['request']==item['request']
            state,trace=improved.update(state,item['request'],[record['first'],record['second']])
            gold.update(item['updates'])
            rows.append(dict(dialogue=name,turn=i,observed=dict(state),expected=dict(gold),
                exact=state==gold,correct_slots=sum(state[k]==gold[k] for k in gold),trace=trace))
        final+=state==gold
    methods['expanded_normalization']=dict(exact_turns=sum(r['exact'] for r in rows),turns=len(rows),
        correct_slots=sum(r['correct_slots'] for r in rows),slots=len(rows)*6,
        exact_final_dialogues=final,rows=rows)
    methods.update({'json_'+k:v for k,v in plain.score(histories,records).items()})
    for data in methods.values():
        data['new_errors_vs_baseline']=sum(a['exact'] and not b['exact'] for a,b in zip(methods['baseline_restore']['rows'],data['rows'],strict=True))
    return methods

def freeze():
    paths=set(core.freeze()['sha256'])|{'scripts/compare_plain_patch.py'}
    paths|={str((ROOT/n).relative_to(REPO)) for n in ['run.py','benchmark.json','models.json','PROTOCOL.md','test_design.py']}
    paths|={str((ROOT.parent/'operation-scope-v2'/n).relative_to(REPO)) for n in ['method.py','test_method.py','PROTOCOL.md']}
    return dict(sha256={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in sorted(paths)},
        models=json.loads((ROOT/'models.json').read_text()),temperature=0,max_tokens=260,
        examples=core.source.base.EXAMPLES,
        libraries={p:importlib.metadata.version(p) for p in ['mlx','mlx-lm','transformers','huggingface-hub']})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=['qwen3','llama32','all'],default='all');args=parser.parse_args()
    frozen=json.loads(json.dumps(freeze()))
    target=ROOT/'frozen.json'
    if target.exists():assert json.loads(target.read_text())==frozen,'Frozen inputs changed'
    else:core.source.save(target,frozen)
    histories=json.loads((ROOT/'benchmark.json').read_text())['histories']
    for key,info in frozen['models'].items():
        if args.model not in ['all',key]:continue
        path=ROOT/f'transcripts-{key}.json';records=json.loads(path.read_text()) if path.exists() else {}
        extractor=None
        for name,requests in histories.items():
            for i,item in enumerate(requests,1):
                rid=f'{name}-{i}'
                if rid in records:
                    assert records[rid]['request']==item['request'];continue
                if extractor is None:
                    from huggingface_hub import snapshot_download
                    from mlx_lm import load
                    extractor=core.source.base.StateExtractor.__new__(core.source.base.StateExtractor)
                    extractor.model,extractor.tokenizer=load(snapshot_download(info['model'],revision=info['revision'],local_files_only=True))
                start=time.monotonic()
                first=extractor.ask(core.source.base.SYSTEM,item['request'],max_tokens=260,examples=core.source.base.EXAMPLES)
                user=item['request']+'\nProposed patch: '+first+'\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
                second=extractor.ask(core.source.base.SYSTEM,user,max_tokens=260,examples=core.source.base.EXAMPLES)
                records[rid]=dict(request=item['request'],first=first,second_user=user,second=second,seconds=time.monotonic()-start)
                core.source.save(path,records);print('SAVED',key,rid,flush=True)
        core.source.save(ROOT/f'results-{key}.json',dict(complete=True,model=info,actual_model_calls=len(records)*2,methods=score(histories,records)))
        print('COMPLETE',key,len(records),flush=True)
        del extractor;gc.collect()
        import mlx.core as mx
        mx.clear_cache()

if __name__=='__main__':main()
