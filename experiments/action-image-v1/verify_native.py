"""Verify native image study provenance and recompute descriptive aggregates."""
import json
from pathlib import Path
import sys
from evaluate import packet, sha, save
from summarize import aggregate
from analyze_pairs import compare


def main():
    root = Path(sys.argv[1]).resolve()
    plan = packet(root)
    assert plan == json.loads((root / 'evaluation-plan.json').read_text())
    frozen = json.loads((root / 'generation-plan.json').read_text())
    assert frozen['prepared_sha256'] == sha(root / 'prepared.json')
    assert frozen['preflight_sha256'] == sha(root / 'feasibility-preflight.json')
    for name, digest in frozen['evaluation_scripts_sha256'].items():
        assert sha(Path(__file__).parent / name) == digest, name
    assert frozen['manager_sha256'] == sha(root.parent / 'keep-image-v1/manage.py')
    summary = json.loads((root / 'summary.json').read_text())
    for name, digest in summary['input_sha256'].items():
        assert sha(root / name) == digest, name
    ratings = json.loads((root / 'ai-ratings.json').read_text())
    assert set(ratings['ratings']) == set(plan['items'])
    assert ratings['inputs']['evaluation_plan_sha256'] == sha(root / 'evaluation-plan.json')
    measured = json.loads((root / 'face-results.json').read_text())
    for name, digest in measured['input_sha256'].items():
        assert sha(root / name) == digest, name
    measured_rows = {r['id']: r for r in measured['rows']}
    assert len(measured_rows) == len(summary['rows']) == len(plan['mapping'])
    for row in summary['rows']:
        assert row['scores'] == ratings['ratings'][plan['mapping'][row['id']]]['scores']
        assert all(row[k] == v for k, v in measured_rows[row['id']].items())
    for mode, stats in summary['by_mode'].items():
        assert stats == aggregate([r for r in summary['rows'] if r['mode'] == mode])
    paired = json.loads((root / 'paired-audit.json').read_text())
    assert paired['summary_sha256'] == sha(root / 'summary.json')
    assert paired['script_sha256'] == sha(Path(__file__).with_name('analyze_pairs.py'))
    assert all(paired[k] == v for k, v in compare(summary['rows'], paired['modes']).items())
    names = ['prepared.json', 'generation-plan.json', 'calls.json', 'evaluation-plan.json',
             'ai-ratings.json', 'face-results.json', 'summary.json', 'paired-audit.json']
    verification = dict(passed=True, conditions=len(summary['rows']),
                        unique_jobs=measured['unique_jobs'], unique_rgb_images=measured['unique_rgb_images'],
                        verifier_sha256=sha(Path(__file__)), sha256={n: sha(root / n) for n in names})
    save(root / 'verification.json', verification)
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    main()
