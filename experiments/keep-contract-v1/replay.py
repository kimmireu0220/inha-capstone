"""Post-hoc development on all stored N, M and O conversations."""
import hashlib
import importlib.util
import json
from pathlib import Path
from contract import enforce

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def main():
    runner = module('keep_development_source', ROOT.parent / 'slot-isolation-validation-v1/run.py')
    studies = {}
    files = [Path(__file__), ROOT / 'contract.py', ROOT / 'PROTOCOL.md', ROOT.parent / 'slot-isolation-v1/method.py',
             ROOT.parent / 'restore-contract-v1/contract.py', REPO / 'local-studio/request_state.py']
    for source in ['action-plan-validation-v1', 'restore-contract-validation-v1', 'slot-isolation-validation-v1']:
        folder = ROOT.parent / source
        benchmark = json.loads((folder / 'benchmark.json').read_text())['histories']
        records = json.loads((folder / 'transcripts.json').read_text())
        files += [folder / 'benchmark.json', folder / 'transcripts.json']
        results = {}
        for mode in ['baseline_restore', 'isolated_restore', 'baseline_restore_keep', 'isolated_restore_keep']:
            rows, final, damage = [], 0, 0
            for name, turns in benchmark.items():
                state, expected = dict(runner.INITIAL), dict(runner.INITIAL)
                for i, turn in enumerate(turns, 1):
                    prior, previous_gold = dict(state), dict(expected)
                    record = records[f'{name}-{i}' + ('' if source == 'slot-isolation-validation-v1' else '-generic')]
                    raws = [record['first'], record['second']]
                    if mode.startswith('baseline'):
                        operations, selected = runner.noop.select_noop(raws, turn['request'], state)
                        state = runner.apply_operations(state, operations, turn['request'])
                    else:
                        state, _, selected = runner.method.update(state, turn['request'], raws)
                    state, reset_rules = runner.contract.enforce(state, turn['request'])
                    keep_rules = {}
                    if mode.endswith('_keep'):
                        state, keep_rules = enforce(state, turn['request'], prior)
                    expected.update(turn['updates'])
                    corrupted = [k for k in state if prior[k] == previous_gold[k] == expected[k] and state[k] != expected[k]]
                    damage += len(corrupted)
                    rows.append({'dialogue': name, 'turn': i, 'observed': dict(state), 'expected': dict(expected),
                                 'exact': state == expected, 'correct_slots': sum(state[k] == expected[k] for k in state),
                                 'selected': selected, 'reset_rules': reset_rules, 'keep_rules': keep_rules,
                                 'newly_corrupted_slots': corrupted})
                final += state == expected
            results[mode] = {'exact_turns': sum(r['exact'] for r in rows),
                             'correct_slots': sum(r['correct_slots'] for r in rows),
                             'exact_final_dialogues': final, 'newly_corrupted_unchanged_slots': damage, 'rows': rows}
        studies[source] = results
    result = {'posthoc_development': True, 'additional_model_calls': 0, 'studies': studies,
              'sha256': {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (ROOT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({study: {mode: {k: v for k, v in data.items() if k != 'rows'} for mode, data in modes.items()}
                      for study, modes in studies.items()}, indent=2))


if __name__ == '__main__':
    main()
