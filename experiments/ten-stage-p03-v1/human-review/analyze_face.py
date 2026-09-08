"""Rebuild only the retained ordinal face ratings from an explicitly derived extract."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent
source = ROOT / 'face-responses.json'
data = json.loads(source.read_text())
assert data['schema'] == 'p03-face-extract-v1' and data['derived_extract'] is True
responses = data['responses']
assert len(responses) == 20 and all(r['kind'] == 'face' for r in responses)
assert {(r['run'], r['step']) for r in responses} == {(run, step) for run in (1, 2) for step in range(1, 11)}
metrics = json.loads((EXP / 'metrics/metrics.json').read_text())
agents = json.loads((EXP / 'agent-review/comparison.json').read_text())['rows']
groups = []
for run in (1, 2):
    rows = sorted((r for r in responses if r['run'] == run), key=lambda r: r['step'])
    scores = [r['answer']['values'][0] for r in rows]
    assert all(len(r['answer']['values']) == 1 for r in rows)
    assert set(scores) <= {'0', '1', '2', '3', 'uncertain'}
    counts = {}
    for name in ('mae', 'ssim', 'lpips', 'face_agent'):
        c = dict(TP=0, TN=0, FP=0, FN=0, excluded=0)
        for step, value in enumerate(scores, 1):
            agent = next(a for a in agents if a['run'] == run and a['step'] == step)
            if value == 'uncertain' or (name == 'face_agent' and agent['uncertain']):
                c['excluded'] += 1
                continue
            pred = agent['naturalness'] >= 2 if name == 'face_agent' else next(m for m in metrics['results'] if m['run'] == run and m['step'] == step)['alarms'][name]
            positive = int(value) >= 2
            c['TP' if pred and positive else 'FP' if pred else 'FN' if positive else 'TN'] += 1
        counts[name] = c
    groups.append(dict(run=run, face_scores=scores, first_clear_derived=next((i for i, v in enumerate(scores, 1) if v != 'uncertain' and int(v) >= 2), None), first_fixed_alarms=metrics['first_alarm_steps'][f'run-{run}'], comparison_against_this_human_binary_gte2=counts))
result = dict(schema='p03-face-analysis-v1', source='face-responses.json', source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), rater_code=data['rater'], responses_validated=20, groups=groups, limits=['Historical stage ratings; same 0–3 face-artifact scale, displayed stage order.', 'Not pooled with current final-output ratings.', 'Comparison-choice and usability responses excluded by protocol format.'])
(ROOT / 'face-analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('Verified retained P03 face ratings: 20 responses, 2 dependent trajectories.')
