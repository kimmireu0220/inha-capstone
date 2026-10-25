"""Additional frozen evaluation; historical inference and reducers unchanged."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT.parent / 'clause-normalization-v1'))
spec = importlib.util.spec_from_file_location('transfer_core', ROOT.parent / 'clause-normalization-v1/run.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
sys.path.insert(0, str(REPO / 'scripts'))
import compare_plain_patch as plain

CONFIGS = [
    dict(name='A', setup='Use a garden background with a bench. Wear a gray blazer over a navy sweater. Add a red triangular pin on the viewer-left lapel and a gold round pendant necklace.',
         initial=dict(background='garden',prop='bench',jacket='gray',top='navy_sweater',pin='red_triangle_left',necklace='gold_round'),
         restore='sweater and pin',keep='gray blazer and garden background',reset=dict(top='original',pin='original'),
         remove='bench',field='prop',follow='Change the necklace to a silver teardrop necklace.',final=dict(necklace='silver_teardrop')),
    dict(name='B', setup='Use a library background with a floor lamp. Wear a navy blazer over an ivory crew-neck shirt. Add a gold square pin on the viewer-right lapel and a silver teardrop necklace.',
         initial=dict(background='library',prop='lamp',jacket='navy',top='ivory_crewneck',pin='gold_square_right',necklace='silver_teardrop'),
         restore='blazer and necklace',keep='library background and lamp',reset=dict(jacket='original',necklace='original'),
         remove='pin',field='pin',follow='Change the shirt to a gray sweater.',final=dict(top='gray_sweater')),
    dict(name='C', setup='Use a pale-blue studio with a plant. Wear a green blazer over a white crew-neck shirt. Add a blue circular pin on the viewer-left lapel and a gold round pendant necklace.',
         initial=dict(background='blue_studio',prop='plant',jacket='green',top='white_crewneck',pin='blue_circle_left',necklace='gold_round'),
         restore='shirt and necklace',keep='green blazer and pale-blue studio background',reset=dict(top='original',necklace='original'),
         remove='plant',field='prop',follow='Change the pin to a red triangular pin on the viewer-left lapel.',final=dict(pin='red_triangle_left')),
    dict(name='D', setup='Use a red-brick studio with a bench. Wear a beige blazer over a gray sweater. Add a blue circular pin on the viewer-left lapel and a silver teardrop necklace.',
         initial=dict(background='brick_studio',prop='bench',jacket='beige',top='gray_sweater',pin='blue_circle_left',necklace='silver_teardrop'),
         restore='pin and sweater',keep='beige blazer and red-brick studio background',reset=dict(pin='original',top='original'),
         remove='necklace',field='necklace',follow='Replace the bench with a plant.',final=dict(prop='plant')),
]
FORMS = {
    'recombined': ('Preserve the {keep}; bring the {restore} back to the original photo.',
                   'Do not alter the {keep}. Remove the {remove}.'),
    'unseen': ('Revert the {restore} to how they looked in the source photo, keeping the {keep} exactly as it is now.',
               'Get rid of the {remove} entirely, and leave the {keep} alone.'),
    'revision': ('Restore the original {keep}; actually, keep the {keep} unchanged. Restore the original {restore}.',
                 'Keep the {remove} unchanged; actually, remove the {remove}. Keep the {keep} unchanged.'),
}

def benchmark():
    return {c['name']+'__'+form: [dict(request=c['setup'],updates=c['initial']),
        dict(request=templates[0].format(**c),updates=c['reset']),
        dict(request=templates[1].format(**c),updates={c['field']:'none'}),
        dict(request=c['follow'],updates=c['final'])]
        for c in CONFIGS for form,templates in FORMS.items()}

def main():
    histories=benchmark()
    paths=set(core.freeze()['sha256']) | {str((ROOT/n).relative_to(REPO)) for n in ['run.py','PROTOCOL.md']}
    paths.add('scripts/compare_plain_patch.py')
    frozen=dict(sha256={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in sorted(paths)},
                histories=histories,model=core.source.base.MODEL,revision=core.source.base.REVISION,
                temperature=0,max_tokens=260)
    target=ROOT/'frozen.json'
    if target.exists(): assert json.loads(target.read_text())==frozen
    else: core.source.save(target,frozen)
    path=ROOT/'transcripts.json'
    records=json.loads(path.read_text()) if path.exists() else {}
    extractor=None
    for name,requests in histories.items():
        for i,item in enumerate(requests,1):
            key=f'{name}-{i}'
            if key in records:
                assert records[key]['request']==item['request']
                continue
            if extractor is None:
                from huggingface_hub import snapshot_download
                from mlx_lm import load
                extractor=core.source.base.StateExtractor.__new__(core.source.base.StateExtractor)
                extractor.model,extractor.tokenizer=load(snapshot_download(core.source.base.MODEL,revision=core.source.base.REVISION,local_files_only=True))
            start=time.monotonic()
            first=extractor.ask(core.source.base.SYSTEM,item['request'],max_tokens=260,examples=core.source.base.EXAMPLES)
            user=item['request']+'\nProposed patch: '+first+'\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
            second=extractor.ask(core.source.base.SYSTEM,user,max_tokens=260,examples=core.source.base.EXAMPLES)
            records[key]=dict(request=item['request'],first=first,second_user=user,second=second,seconds=time.monotonic()-start)
            core.source.save(path,records)
            print('SAVED',key,flush=True)
    methods=core.score(histories,records)
    methods.update({'json_'+k:v for k,v in plain.score(histories,records).items()})
    core.source.save(ROOT/'results.json',dict(complete=True,actual_model_calls=len(records)*2,methods=methods))
    print('COMPLETE',len(records),flush=True)

if __name__=='__main__': main()
