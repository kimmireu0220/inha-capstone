"""Post-hoc control: skip already-satisfied updates before lexical validation.

Uses only stored model outputs and the method's own previous state, never gold
labels, for decisions. This analysis was designed after inspecting pilot errors.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('coverage_pilot_ablation', ROOT / 'run.py')
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def select_noop(raws, request, state):
    for index in reversed(range(len(raws))):
        try:
            raw = raws[index]
            patch = json.loads(raw[raw.find('{'):raw.rfind('}') + 1], object_pairs_hook=run.unique_object)
            if not isinstance(patch, dict):
                raise ValueError('Expected an object')
            remaining = {k: v for k, v in patch.items() if k not in state or v != state[k]}
            return run.patch_operations(remaining, request), index
        except (ValueError, TypeError, KeyError):
            pass
    return [], None


def main():
    records = json.loads((ROOT / 'transcripts.json').read_text())
    histories = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    summary = {}
    for mode in ['first_only', 'generic']:
        rows = []
        for name, turns in histories.items():
            state, expected = dict(run.INITIAL), dict(run.INITIAL)
            for index, turn in enumerate(turns, 1):
                saved = records[f'{name}-{index}']
                raws = [saved['first']] + ([] if mode == 'first_only' else [saved['generic']['response']])
                operations, selected = select_noop(raws, turn['request'], state)
                state = run.apply_operations(state, operations, turn['request'])
                expected.update(turn['updates'])
                rows.append({'dialogue': name, 'turn': index, 'expected': dict(expected),
                             'observed': dict(state), 'selected': selected, 'exact': state == expected,
                             'correct_slots': sum(state[k] == expected[k] for k in state)})
        summary[mode + '_noop_guard'] = {'exact_turns': sum(r['exact'] for r in rows),
                                         'correct_slots': sum(r['correct_slots'] for r in rows),
                                         'rows': rows}
    result = {'posthoc': True, 'new_model_calls': 0, 'methods': summary}
    (ROOT / 'ablation-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: {f: v for f, v in row.items() if f != 'rows'} for k, row in summary.items()}, indent=2))


if __name__ == '__main__':
    main()
