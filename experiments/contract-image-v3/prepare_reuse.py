"""Freeze exact input reuse eligibility before S generation or AI evaluation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'keep-image-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = json.loads((SOURCE / 'prepared.json').read_text())
    target = json.loads((ROOT / 'prepared.json').read_text())
    ledger = json.loads((SOURCE / 'calls.json').read_text())
    previous = {r['job']: r for r in source['conditions']}
    jobs = {r['job']: r for r in target['conditions']}
    assert {r['job'] for r in ledger['calls']} == set(previous), 'P generation incomplete'
    shared = set(previous) & set(jobs)
    for job in shared:
        assert previous[job]['signature'] == jobs[job]['signature']
        assert previous[job]['prompt'] == jobs[job]['prompt']
    result = {'selection_uses_evaluation_scores': False, 'reused_jobs': len(shared),
              'new_jobs': len(jobs) - len(shared), 'total_jobs': len(jobs),
              'shared_jobs': sorted(shared), 'source_prepared_sha256': sha(SOURCE / 'prepared.json'),
              'source_calls_sha256': sha(SOURCE / 'calls.json'), 'target_prepared_sha256': sha(ROOT / 'prepared.json'),
              'script_sha256': sha(Path(__file__))}
    output = ROOT / 'reuse-plan.json'
    if output.exists():
        assert json.loads(output.read_text()) == result
    else:
        output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
