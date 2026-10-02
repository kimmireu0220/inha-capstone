"""Development-only checks using the discarded T1-T4 parser benchmark."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from request_state import INITIAL, StateExtractor

if __name__ == '__main__':
    benchmark = ROOT.parent / 'experiments/state-tracking-v1/benchmark.json'
    histories = json.loads(benchmark.read_text())['histories']
    model = StateExtractor()
    results = {'scope': 'development checks, not held-out evaluation',
        'method_sha256': hashlib.sha256((ROOT / 'request_state.py').read_bytes()).hexdigest(),
        'histories': {}}
    for name, history in histories.items():
        state, ledger = model.replay([turn['request'] for turn in history['turns']])
        expected = dict(INITIAL)
        errors = []
        for turn, row in zip(history['turns'], ledger):
            expected.update(turn['updates'])
            wrong = {key: {'expected': expected[key], 'actual': row['state'][key]}
                     for key in INITIAL if expected[key] != row['state'][key]}
            if wrong:
                errors.append({'turn': row['turn'], 'wrong': wrong})
        results['histories'][name] = {'ledger': ledger, 'errors': errors,
            'final_correct': state == expected, 'expected': expected, 'observed': state}
        (ROOT / 'checks/request-extractor-development.json').write_text(
            json.dumps(results, indent=2) + '\n')
        print(name, 'final_correct', state == expected, 'turn_errors', len(errors), flush=True)
