"""One fixed producer; shared raw outputs allow an exact reducer ablation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


method = module('fixed_slot_isolation', ROOT.parent / 'slot-isolation-v1/method.py')
noop = module('fixed_slot_noop', ROOT.parent / 'coverage-repair-v1/ablation.py')
contract = module('fixed_slot_restore', ROOT.parent / 'restore-contract-v1/contract.py')
from request_state import INITIAL, StateExtractor, MODEL, SYSTEM, EXAMPLES, apply_operations
REVISION = '4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25'


def save(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def score(benchmark, records):
    results = {}
    for mode in ['baseline_restore', 'latest_atomic_restore', 'isolated_restore', 'isolated', 'first_isolated_restore']:
        rows, final, damage = [], 0, 0
        for name, turns in benchmark.items():
            state, expected = dict(INITIAL), dict(INITIAL)
            for i, turn in enumerate(turns, 1):
                prior, previous_gold = dict(state), dict(expected)
                record = records[f'{name}-{i}']
                raws = [record['first']] + ([] if mode.startswith('first_') else [record['second']])
                if mode == 'baseline_restore':
                    operations, selected = noop.select_noop(raws, turn['request'], state)
                    state = apply_operations(state, operations, turn['request'])
                    errors = {} if selected is not None else {'patch': 'No valid patch'}
                else:
                    state, errors, selected = method.update(state, turn['request'], raws, atomic=mode == 'latest_atomic_restore')
                if mode.endswith('_restore'):
                    state, rules = contract.enforce(state, turn['request'])
                else:
                    rules = {}
                expected.update(turn['updates'])
                corrupted = [k for k in state if prior[k] == previous_gold[k] == expected[k] and state[k] != expected[k]]
                damage += len(corrupted)
                rows.append({'dialogue': name, 'turn': i, 'observed': dict(state), 'expected': dict(expected),
                             'exact': state == expected, 'correct_slots': sum(state[k] == expected[k] for k in state),
                             'newly_corrupted_slots': corrupted, 'errors': errors, 'selected': selected, 'rules': rules})
            final += state == expected
        results[mode] = {'exact_turns': sum(r['exact'] for r in rows), 'turns': len(rows),
                         'correct_slots': sum(r['correct_slots'] for r in rows), 'slots': len(rows) * 6,
                         'exact_final_dialogues': final, 'newly_corrupted_unchanged_slots': damage, 'rows': rows}
    return results


def main():
    files = [Path(__file__), ROOT / 'PROTOCOL.md', ROOT / 'benchmark.json',
             ROOT.parent / 'slot-isolation-v1/method.py', ROOT.parent / 'restore-contract-v1/contract.py',
             ROOT.parent / 'coverage-repair-v1/ablation.py', ROOT.parent / 'coverage-repair-v1/run.py',
             REPO / 'local-studio/request_state.py']
    frozen = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    frozen['model_revision'] = REVISION
    if (ROOT / 'frozen.json').exists():
        assert json.loads((ROOT / 'frozen.json').read_text()) == frozen
    else:
        save(ROOT / 'frozen.json', frozen)
    benchmark = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    path = ROOT / 'transcripts.json'
    records = json.loads(path.read_text()) if path.exists() else {}
    extractor = None
    for name, turns in benchmark.items():
        for i, turn in enumerate(turns, 1):
            key = f'{name}-{i}'
            if key in records:
                continue
            if extractor is None:
                from huggingface_hub import snapshot_download
                from mlx_lm import load
                extractor = StateExtractor.__new__(StateExtractor)
                extractor.model, extractor.tokenizer = load(snapshot_download(MODEL, revision=REVISION, local_files_only=True))
            start = time.monotonic()
            first = extractor.ask(SYSTEM, turn['request'], max_tokens=260, examples=EXAMPLES)
            user = (turn['request'] + '\nProposed patch: ' + first
                    + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.')
            second = extractor.ask(SYSTEM, user, max_tokens=260, examples=EXAMPLES)
            records[key] = {'request': turn['request'], 'first': first, 'second_user': user,
                            'second': second, 'seconds': time.monotonic() - start}
            save(path, records)
            print('SAVED', key, flush=True)
    results = score(benchmark, records)
    save(ROOT / 'results.json', {'complete': True, 'actual_model_calls': len(records) * 2, 'methods': results})
    print(json.dumps({m: {k: v for k, v in data.items() if k != 'rows'} for m, data in results.items()}, indent=2), flush=True)


if __name__ == '__main__':
    main()
