"""Paired wording stress test; preserve frozen historical reducers and responses."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
spec = importlib.util.spec_from_file_location('paraphrase_source', ROOT.parent / 'request-contract-v3/run.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

REQUESTS = [
    ["Set the scene to a pale-blue studio containing a plant. Use a gray blazer over an ivory crew-neck shirt, with a silver teardrop necklace.",
     "Do not alter the necklace. Swap the shirt for a navy sweater and use a library instead of the pale-blue studio.",
     "Leave the plant as it is. Actually, remove the plant. The gray blazer must stay the same.",
     "Bring back the original shirt and necklace; retain the gray blazer and library background."],
    ["Choose an office scene with a bench, a beige blazer, a white crew-neck shirt, and a blue circular pin on the viewer-left lapel.",
     "Retain the pin as it is; switch to a gray sweater and a garden background.",
     "Take off the pin. Swap the bench for a floor lamp without altering the beige blazer.",
     "Return the blazer and shirt to their original appearance. Do not alter the garden or lamp."],
    ["Choose a green blazer, navy sweater, gold round pendant necklace, and library scene with a lamp.",
     "There should be no necklace. Keep the navy sweater and lamp as they are; use a red-brick studio instead of the library.",
     "Make the blazer navy. Preserve the lamp for now. Correction: remove the lamp.",
     "Return the necklace and shirt to the original photo, leaving the navy blazer and red-brick studio as they are."],
    ["Choose a navy blazer over a gray sweater and attach a red triangular pin to the viewer-left lapel. Set the scene in a garden with a plant.",
     "Make the blazer beige rather than preserving its color. Do not change the plant or gray sweater. Use an office instead of the garden.",
     "Exclude the pin from the image. Use a bench instead of the plant, with the office background kept as it is.",
     "Bring back the original blazer and shirt. Preserve the office setting and bench."],
    ["Choose a gray blazer, an ivory crew-neck shirt, and a gold round pendant necklace, in a red-brick studio containing a bench.",
     "I first wanted the necklace unchanged, but remove the necklace instead. Preserve the bench and use a white crew-neck shirt.",
     "Delete the bench from the scene. Retain the gray blazer and white shirt, and use a pale-blue studio background.",
     "Bring the shirt and necklace back to the original photo. Retain the pale-blue studio background."],
    ["Set the scene in a library with a plant. Choose a beige blazer, gray sweater, and silver circular pin on the viewer-right lapel.",
     "Do not alter the silver pin. Use a navy sweater rather than gray, and an office rather than a library.",
     "Preserve the plant. On second thought, remove the plant. Do not change the beige blazer or navy sweater.",
     "Bring back the original pin and shirt, preserving the beige blazer and office scene."],
    ["Choose a green blazer with a white crew-neck shirt and silver teardrop necklace. Use an office setting with a floor lamp.",
     "The blazer should now be gray. Retain the lamp, and use a garden instead of the office.",
     "Take the necklace out of the image. Do not change the white shirt or lamp.",
     "Return the shirt and necklace to the original photo. Preserve the gray blazer and garden setting."],
    ["Choose a navy blazer with an ivory crew-neck shirt and a gold square pin on the viewer-right lapel. Use a pale-blue studio with a bench.",
     "I said to retain the pin, but remove the pin instead. Use a gray sweater and do not change the bench.",
     "Do not change the navy blazer or gray sweater. Use a plant rather than a bench and a library rather than a pale-blue studio.",
     "Bring back the original blazer and pin. Preserve the library background and plant."],
]


def benchmark():
    original = json.loads((ROOT.parent / 'isolated-contract-v1/benchmark.json').read_text())['histories']
    assert len(original) == len(REQUESTS) == 8
    return {name: [dict(request=request, updates=turn['updates'])
                   for request, turn in zip(requests, turns, strict=True)]
            for (name, turns), requests in zip(original.items(), REQUESTS, strict=True)}


def main():
    histories = benchmark()
    paths = set(source.frozen_files()) | {
        str((ROOT / name).relative_to(REPO)) for name in ['run.py', 'PROTOCOL.md']
    } | {'experiments/isolated-contract-v1/benchmark.json'}
    frozen = {'sha256': {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in sorted(paths)},
              'model': source.base.MODEL, 'revision': source.base.REVISION, 'histories': histories}
    freeze_path = ROOT / 'frozen.json'
    if freeze_path.exists():
        assert json.loads(freeze_path.read_text()) == frozen, 'Frozen inputs changed'
    else:
        source.save(freeze_path, frozen)
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
                extractor = source.base.StateExtractor.__new__(source.base.StateExtractor)
                extractor.model, extractor.tokenizer = load(snapshot_download(
                    source.base.MODEL, revision=source.base.REVISION, local_files_only=True))
            start = time.monotonic()
            first = extractor.ask(source.base.SYSTEM, turn['request'], max_tokens=260, examples=source.base.EXAMPLES)
            review = turn['request'] + '\nProposed patch: ' + first + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
            second = extractor.ask(source.base.SYSTEM, review, max_tokens=260, examples=source.base.EXAMPLES)
            records[key] = dict(request=turn['request'], first=first, second_user=review,
                                second=second, seconds=time.monotonic() - start)
            source.save(path, records)
            print('SAVED', key, flush=True)
    methods = source.score(histories, records)
    baseline = methods['baseline_restore']['rows']
    for method in methods.values():
        method['new_errors_vs_baseline'] = sum(a['exact'] and not b['exact']
                                               for a, b in zip(baseline, method['rows'], strict=True))
    source.save(ROOT / 'results.json', dict(complete=True, actual_model_calls=len(records)*2, methods=methods))
    print(json.dumps({k: {a: b for a, b in v.items() if a != 'rows'} for k, v in methods.items()}, indent=2))


if __name__ == '__main__':
    main()
