"""Audit the predeclared image snapshots before generating identical inputs."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / 'local-studio'))
from request_state import render_prompt


def main():
    verification = json.loads((ROOT / 'verification.json').read_text())
    assert verification['passed'] and verification['advance_to_images']
    for name, digest in verification['sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    results = json.loads((ROOT / 'results.json').read_text())['methods']
    methods = ['baseline_restore', 'isolated_restore']
    maps = {m: {(r['dialogue'], r['turn']): r for r in results[m]['rows']} for m in methods}
    rows = []
    for (dialogue, turn), left in maps[methods[0]].items():
        if turn not in [2, 4]:
            continue
        right = maps[methods[1]][(dialogue, turn)]
        a, b = render_prompt(left['observed']), render_prompt(right['observed'])
        rows.append({'dialogue': dialogue, 'turn': turn, 'same_state': left['observed'] == right['observed'],
                     'same_prompt': a == b, 'baseline_prompt_sha256': hashlib.sha256(a.encode()).hexdigest(),
                     'candidate_prompt_sha256': hashlib.sha256(b.encode()).hexdigest()})
    result = {'planned_conditions': 64, 'planned_paired_conditions': 32,
              'snapshots': len(rows), 'different_prompt_snapshots': sum(not r['same_prompt'] for r in rows),
              'new_images_generated': 0, 'rows': rows,
              'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in ['results.json', 'verification.json', 'image_input_audit.py']},
              'interpretation': 'Identical planned prompts cannot attribute image differences to this state-reduction method. No image improvement was measured.'}
    (ROOT / 'image-input-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
