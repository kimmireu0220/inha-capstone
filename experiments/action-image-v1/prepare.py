"""Build the predeclared 48 image conditions from predicted states, without generation."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE = ROOT.parent / 'action-plan-validation-v1'
REFERENCES = ROOT.parent / 'state-tracking-v2/references'
sys.path.insert(0, str(REPO / 'local-studio'))
from request_state import render_prompt


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def main():
    verification = json.loads((SOURCE / 'verification.json').read_text())
    assert verification['passed'] and verification['advance_to_images']
    for name, digest in verification['sha256'].items():
        assert sha(SOURCE / name) == digest
    results = json.loads((SOURCE / 'results.json').read_text())['methods']
    by_mode = {mode: {(r['dialogue'], r['turn']): r for r in results[mode]['rows']}
               for mode in ['generic_noop', 'action']}
    conditions, signatures = [], {}
    for hi, history in enumerate(['N1', 'N2', 'N3', 'N4', 'N5', 'N6']):
        for turn in [2, 4]:
            for pi, person in enumerate(['R01', 'R02']):
                order = ['generic_noop', 'action'] if (hi + pi + turn) % 2 else ['action', 'generic_noop']
                for mode in order:
                    row = by_mode[mode][(history, turn)]
                    prompt = render_prompt(row['observed'])
                    signature = hashlib.sha256((sha(REFERENCES / f'{person}.png') + '\n' + prompt).encode()).hexdigest()
                    job = signatures.setdefault(signature, 'img-' + signature[:16])
                    conditions.append({'id': f'{person}-{history}-t{turn}-{mode}', 'person': person,
                                       'history': history, 'turn': turn, 'mode': mode, 'job': job,
                                       'observed_state': row['observed'], 'expected_state': row['expected'],
                                       'prompt': prompt, 'signature': signature})
    inputs = {str(path.relative_to(REPO)): sha(path) for path in [Path(__file__), ROOT / 'PROTOCOL.md',
              SOURCE / 'results.json', SOURCE / 'verification.json', REPO / 'local-studio/request_state.py']}
    inputs.update({str((REFERENCES / f'{person}.png').relative_to(REPO)): sha(REFERENCES / f'{person}.png')
                   for person in ['R01', 'R02']})
    plan = {'generation_not_started': True, 'backend_pending_confirmation': True,
            'condition_count': len(conditions), 'unique_prompt_reference_jobs': len(signatures),
            'inputs': inputs, 'conditions': conditions}
    path = ROOT / 'prepared.json'
    if path.exists():
        assert json.loads(path.read_text()) == plan, 'Prepared image inputs changed'
    else:
        save(path, plan)
    print(f'Prepared {len(conditions)} conditions / {len(signatures)} unique prompt-reference jobs; no images generated')


if __name__ == '__main__':
    main()
