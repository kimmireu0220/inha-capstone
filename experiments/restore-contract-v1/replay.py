"""Post-hoc development replay, applying the same contract to both methods."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'action-plan-validation-v1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    runner = load('contract_replay_base', SOURCE / 'run.py')
    contract = load('contract_replay_rules', ROOT / 'contract.py')
    benchmark = json.loads((SOURCE / 'benchmark.json').read_text())['histories']
    records = json.loads((SOURCE / 'transcripts.json').read_text())
    result = {}
    for mode in ['generic_noop', 'action']:
        rows, final, damage = [], 0, 0
        for name, turns in benchmark.items():
            state, expected = dict(runner.action.INITIAL), dict(runner.action.INITIAL)
            for i, turn in enumerate(turns, 1):
                old_state, old_expected = dict(state), dict(expected)
                record = records[f'{name}-{i}-' + ('generic' if mode == 'generic_noop' else 'action')]
                if mode == 'action':
                    state, errors = runner.action.compile_update(state, turn['request'], record['first'], record['second'])
                else:
                    operations, _ = runner.noop.select_noop([record['first'], record['second']], turn['request'], state)
                    state = runner.action.apply_operations(state, operations, turn['request'])
                state, rules = contract.enforce(state, turn['request'])
                expected.update(turn['updates'])
                damage += sum(old_state[k] == old_expected[k] == expected[k] and state[k] != expected[k] for k in state)
                rows.append({'dialogue': name, 'turn': i, 'observed': dict(state), 'expected': dict(expected),
                             'rules': rules, 'exact': state == expected,
                             'correct_slots': sum(state[k] == expected[k] for k in state)})
            final += state == expected
        result[mode + '_restore'] = {'exact_turns': sum(r['exact'] for r in rows),
                                     'correct_slots': sum(r['correct_slots'] for r in rows),
                                     'exact_final_dialogues': final, 'newly_corrupted_unchanged_slots': damage,
                                     'rows': rows}
    files = [ROOT / 'contract.py', ROOT / 'PROTOCOL.md', Path(__file__), SOURCE / 'transcripts.json', SOURCE / 'benchmark.json']
    manifest = {str(p.relative_to(ROOT.parents[1])): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    output = {'posthoc_development': True, 'additional_model_calls': 0, 'methods': result, 'sha256': manifest}
    (ROOT / 'results.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({m: {k: v for k, v in data.items() if k != 'rows'} for m, data in result.items()}, indent=2))


if __name__ == '__main__':
    main()
