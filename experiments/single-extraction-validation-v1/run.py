"""Fresh paired comparison of one extraction with two model calls."""
import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
spec=importlib.util.spec_from_file_location('single_parent',ROOT.parent/'instruction-eligibility-validation-v1/run.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)

def score(histories,records):
    methods=parent.score(histories,records);rows=[];final=0
    for name,requests in histories.items():
        state=dict(parent.parent.plain.INITIAL);gold=dict(state)
        for i,item in enumerate(requests,1):
            record=records[f'{name}-{i}'];assert record['request']==item['request']
            state,trace=parent.method.update(state,item['request'],[record['first']])
            gold.update(item['updates'])
            rows.append(dict(dialogue=name,turn=i,observed=dict(state),expected=dict(gold),exact=state==gold,
                correct_slots=sum(state[k]==gold[k] for k in gold),trace=trace))
        final+=state==gold
    methods['single_extraction_checked']=dict(exact_turns=sum(r['exact'] for r in rows),turns=len(rows),
        correct_slots=sum(r['correct_slots'] for r in rows),slots=len(rows)*6,exact_final_dialogues=final,
        new_errors_vs_baseline=sum(a['exact'] and not b['exact'] for a,b in zip(methods['baseline_restore']['rows'],rows,strict=True)),rows=rows)
    for name,result in methods.items():result['required_model_calls_per_request']=1 if name in ['json_first_only','single_extraction_checked'] else 2
    return methods

def freeze():
    data=parent.freeze();paths=set(data['sha256'])
    paths|={str((ROOT/n).relative_to(REPO)) for n in ['run.py','benchmark.json','PROTOCOL.md','test_design.py']}
    return dict(data,sha256={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in sorted(paths)})

def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze-only',action='store_true');args=p.parse_args()
    frozen=json.loads(json.dumps(freeze()));target=ROOT/'frozen.json'
    if target.exists():assert json.loads(target.read_text())==frozen,'Frozen inputs changed'
    else:parent.parent.core.source.save(target,frozen)
    if args.freeze_only:print('Frozen one-extraction validation');return
    histories=json.loads((ROOT/'benchmark.json').read_text())['histories']
    for key,info in frozen['models'].items():
        path=ROOT/f'transcripts-{key}.json';records=json.loads(path.read_text()) if path.exists() else {};extractor=None
        for name,requests in histories.items():
            for i,item in enumerate(requests,1):
                rid=f'{name}-{i}'
                if rid in records:assert records[rid]['request']==item['request'];continue
                if extractor is None:
                    from huggingface_hub import snapshot_download
                    from mlx_lm import load
                    extractor=parent.parent.core.source.base.StateExtractor.__new__(parent.parent.core.source.base.StateExtractor)
                    extractor.model,extractor.tokenizer=load(snapshot_download(info['model'],revision=info['revision'],local_files_only=True))
                start=time.monotonic()
                first=extractor.ask(parent.parent.core.source.base.SYSTEM,item['request'],max_tokens=260,examples=parent.parent.core.source.base.EXAMPLES)
                user=item['request']+'\nProposed patch: '+first+'\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
                second=extractor.ask(parent.parent.core.source.base.SYSTEM,user,max_tokens=260,examples=parent.parent.core.source.base.EXAMPLES)
                records[rid]=dict(request=item['request'],first=first,second_user=user,second=second,seconds=time.monotonic()-start)
                parent.parent.core.source.save(path,records);print('SAVED',key,rid,flush=True)
        parent.parent.core.source.save(ROOT/f'results-{key}.json',dict(complete=True,model=info,actual_model_calls=len(records)*2,methods=score(histories,records)))
        print('COMPLETE',key,len(records),flush=True)
        del extractor;gc.collect()
        import mlx.core as mx
        mx.clear_cache()

if __name__=='__main__':main()
