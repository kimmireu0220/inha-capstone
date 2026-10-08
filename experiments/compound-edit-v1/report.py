"""Recompute frozen text scores and preserve one-pass image judgments."""
import importlib.util
import json
from pathlib import Path
from collections import Counter
import run
from evaluate_images import sha, save, prepare

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def main():
    frozen = json.loads((ROOT / 'frozen.json').read_text())
    for name, digest in frozen['sha256'].items():
        assert sha(REPO / name) == digest
    data = json.loads((ROOT / 'benchmark.json').read_text())
    transcripts = json.loads((ROOT / 'transcripts.json').read_text())
    assert len(transcripts) == 48
    result = json.loads((ROOT / 'results.json').read_text())
    assert result['methods'] == run.score(data, transcripts)
    wrong = Counter()
    for row in result['methods']['review']['rows']:
        for field, expected in row['expected'].items():
            if row['observed'][field] != expected:
                wrong[f'{field}: {row["observed"][field]} -> {expected}'] += 1
    # Post-hoc component analysis, explicitly not a preregistered comparison.
    remove_exact = 0
    for name, turns in data.items():
        state, gold = dict(run.INITIAL), dict(run.INITIAL)
        for i, turn in enumerate(turns, 1):
            prior = dict(state)
            record = transcripts[f'{name}-{i}']
            for raw in [record['second'], record['first']]:
                try:
                    state.update(run.parse(raw))
                    break
                except (ValueError, TypeError):
                    pass
            guarded, events = run.guard(state, prior, turn['request'])
            for event in events:
                if event['action'] == 'remove':
                    state[event['field']] = guarded[event['field']]
            gold.update(turn['updates'])
            remove_exact += state == gold
    plan = prepare()
    ratings = json.loads((ROOT / 'image-ratings.json').read_text())
    assert ratings['frozen_sha256'] == sha(ROOT / 'image-evaluation-frozen.json')
    assert set(ratings['ratings']) == {x['id'] for x in plan['conditions']}
    image_rows = []
    for item in plan['conditions']:
        r = ratings['ratings'][item['id']]
        assert len(r['scores']) == len(item['goals'])
        image_rows.append(dict(id=item['id'], satisfied=sum(x == 1 for x in r['scores']),
                               total=len(r['scores']), unknown=sum(x is None for x in r['scores']),
                               scores=r['scores'], parse_error=r['parse_error']))
    summary = dict(complete=True, exploratory=True, rater_type='AI',
                   groups={k: v['groups'] for k, v in result['methods'].items()},
                   review_wrong_slots=dict(wrong),
                   post_hoc_remove_only_exact_turns=remove_exact,
                   image_rows=image_rows)
    control_freeze = json.loads((ROOT / 'operation-control-frozen.json').read_text())
    for name, digest in control_freeze['sha256'].items():
        assert sha(ROOT / name) == digest
    controls = json.loads((ROOT / 'operation-control.json').read_text())
    assert len(controls) == 8
    for i, (request, expected) in enumerate(control_freeze['cases'], 1):
        record = controls[str(i)]
        assert record['request'] == request and record['expected'] == expected
        for key, metric in [('first', 'first_exact'), ('second', 'review_exact')]:
            assert record[metric] == (run.parse(record[key]) == expected)
    summary['post_hoc_operation_control'] = dict(requests=8, model_calls=16,
        first_exact=sum(x['first_exact'] for x in controls.values()),
        review_exact=sum(x['review_exact'] for x in controls.values()),
        failed_ids=[k for k, x in controls.items() if not x['review_exact']])
    save(ROOT / 'summary.json', summary)
    files = ['run.py', 'benchmark.json', 'frozen.json', 'transcripts.json', 'results.json',
             'image-plan.json', 'image-evaluation-frozen.json', 'image-ratings.json',
             'summary.json', 'report.py', 'evaluate_images.py', 'generation-log.json',
             'check_operations.py', 'operation-control-frozen.json', 'operation-control.json']
    save(ROOT / 'verification.json', dict(passed=True, turns=48, image_conditions=6,
        scope='Recomputation and file integrity, not independent scientific validation',
        sha256={f: sha(ROOT / f) for f in files}))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
