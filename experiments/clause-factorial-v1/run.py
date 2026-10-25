"""Frozen paired sentence-structure comparison with unchanged previous methods."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
CORE = ROOT.parent / 'clause-normalization-v1'
sys.path.insert(0, str(CORE))
spec = importlib.util.spec_from_file_location('frozen_clause_comparison', CORE / 'run.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

SCENARIOS = [
    dict(name='shirt_necklace',
         setup='Use a library background with a plant. Wear a navy blazer over a gray sweater. Add a blue circular pin on the viewer-left lapel and a gold round pendant necklace.',
         initial=dict(background='library', prop='plant', jacket='navy', top='gray_sweater', pin='blue_circle_left', necklace='gold_round'),
         restore='shirt and necklace', keep='navy blazer and library background',
         resets=dict(top='original', necklace='original'),
         follow='Remove the pin. Keep the plant unchanged.', final=dict(pin='none')),
    dict(name='pin_shirt',
         setup='Use an office background with a bench. Wear a beige blazer over a white crew-neck shirt. Add a red triangular pin on the viewer-left lapel and a silver teardrop necklace.',
         initial=dict(background='office', prop='bench', jacket='beige', top='white_crewneck', pin='red_triangle_left', necklace='silver_teardrop'),
         restore='pin and shirt', keep='beige blazer and office background',
         resets=dict(pin='original', top='original'),
         follow='Remove the bench. Keep the necklace unchanged.', final=dict(prop='none')),
    dict(name='blazer_necklace',
         setup='Use a red-brick studio with a floor lamp. Wear a green blazer over an ivory crew-neck shirt. Add a gold square pin on the viewer-right lapel and a gold round pendant necklace.',
         initial=dict(background='brick_studio', prop='lamp', jacket='green', top='ivory_crewneck', pin='gold_square_right', necklace='gold_round'),
         restore='blazer and necklace', keep='red-brick studio background and lamp',
         resets=dict(jacket='original', necklace='original'),
         follow='Change the shirt to a navy sweater. Keep the pin unchanged.', final=dict(top='navy_sweater')),
]
FORMS = dict(
    separated='Restore the original {restore}. Keep the {keep} unchanged.',
    leaving='Return the {restore} to the original photo, leaving the {keep} unchanged.',
    preserving='Restore the original {restore}, preserving the {keep}.',
    bring_back='Bring the {restore} back to the original photo. Do not alter the {keep}.',
)


def benchmark():
    return {item['name']+'__'+form: [
        dict(request=item['setup'], updates=item['initial']),
        dict(request=template.format(**item), updates=item['resets']),
        dict(request=item['follow'], updates=item['final']),
    ] for item in SCENARIOS for form, template in FORMS.items()}


def main():
    histories = benchmark()
    paths = set(core.freeze()['sha256']) | {str((ROOT / name).relative_to(REPO))
        for name in ['run.py', 'PROTOCOL.md']}
    frozen = dict(sha256={p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in sorted(paths)},
                  model=core.source.base.MODEL, revision=core.source.base.REVISION,
                  histories=histories, temperature=0, max_tokens=260)
    target = ROOT / 'frozen.json'
    if target.exists():
        assert json.loads(target.read_text()) == frozen
    else:
        core.source.save(target, frozen)
    path = ROOT / 'transcripts.json'
    records = json.loads(path.read_text()) if path.exists() else {}
    extractor = None
    for name, turns in histories.items():
        for i, turn in enumerate(turns, 1):
            key = f'{name}-{i}'
            if key in records:
                assert records[key]['request'] == turn['request']
                continue
            if extractor is None:
                from huggingface_hub import snapshot_download
                from mlx_lm import load
                extractor = core.source.base.StateExtractor.__new__(core.source.base.StateExtractor)
                extractor.model, extractor.tokenizer = load(snapshot_download(
                    core.source.base.MODEL, revision=core.source.base.REVISION, local_files_only=True))
            start = time.monotonic()
            first = extractor.ask(core.source.base.SYSTEM, turn['request'], max_tokens=260, examples=core.source.base.EXAMPLES)
            user = turn['request'] + '\nProposed patch: ' + first + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
            second = extractor.ask(core.source.base.SYSTEM, user, max_tokens=260, examples=core.source.base.EXAMPLES)
            records[key] = dict(request=turn['request'], first=first, second_user=user,
                                second=second, seconds=time.monotonic()-start)
            core.source.save(path, records)
            print('SAVED', key, flush=True)
    core.source.save(ROOT / 'results.json', dict(complete=True, actual_model_calls=len(records)*2,
                                               methods=core.score(histories, records)))
    print('COMPLETE', len(records), flush=True)


if __name__ == '__main__':
    main()
