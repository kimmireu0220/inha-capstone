"""Post-result diagnostic: isolate removal/restoration without pose distractors."""
import argparse
import json
import sys
import time
from pathlib import Path
from evaluate_images import sha, save
from run import SYSTEM, EXAMPLES, MODEL, REVISION, parse

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
CASES = [
    ('Remove the plant.', {'prop': 'none'}),
    ('Remove the necklace.', {'necklace': 'none'}),
    ('Restore the plant to the original.', {'prop': 'original'}),
    ('Restore the necklace to the original.', {'necklace': 'original'}),
    ('Remove the plant. Restore the necklace to the original.', {'prop': 'none', 'necklace': 'original'}),
    ('Restore the plant to the original. Remove the necklace.', {'prop': 'original', 'necklace': 'none'}),
    ('Restore the necklace to the original. Remove the plant.', {'prop': 'none', 'necklace': 'original'}),
    ('Remove the necklace. Restore the plant to the original.', {'prop': 'original', 'necklace': 'none'}),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prepare', action='store_true')
    args = ap.parse_args()
    freeze = dict(post_hoc=True, purpose='Distinguish operation confusion from pose complexity',
                  model=MODEL, revision=REVISION, temperature=0, max_tokens=320,
                  cases=CASES, sha256={n: sha(ROOT / n) for n in ['check_operations.py', 'run.py']})
    # Normalize tuples before comparison with the stored JSON.
    freeze = json.loads(json.dumps(freeze))
    path = ROOT / 'operation-control-frozen.json'
    if path.exists():
        assert json.loads(path.read_text()) == freeze
    else:
        save(path, freeze)
    if args.prepare:
        print('Frozen eight post-result diagnostic requests before new inference')
        return
    from huggingface_hub import snapshot_download
    from mlx_lm import load
    sys.path.insert(0, str(REPO / 'local-studio'))
    from request_state import StateExtractor
    extractor = StateExtractor.__new__(StateExtractor)
    extractor.model, extractor.tokenizer = load(snapshot_download(MODEL, revision=REVISION, local_files_only=True))
    output = ROOT / 'operation-control.json'
    records = json.loads(output.read_text()) if output.exists() else {}
    for i, (request, expected) in enumerate(CASES, 1):
        if str(i) in records:
            continue
        first = extractor.ask(SYSTEM, request, max_tokens=320, examples=EXAMPLES)
        review_request = request + '\nProposed patch: ' + first + '\nReview against the request. Correct errors and return only a flat JSON patch.'
        second = extractor.ask(SYSTEM, review_request, max_tokens=320, examples=EXAMPLES)
        scores = []
        for raw in [first, second]:
            try:
                scores.append(parse(raw) == expected)
            except (ValueError, TypeError):
                scores.append(False)
        records[str(i)] = dict(request=request, expected=expected, first=first, second=second,
                               first_exact=scores[0], review_exact=scores[1])
        save(output, records)
        print(i, scores, flush=True)


if __name__ == '__main__':
    main()
