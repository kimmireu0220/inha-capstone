"""Frozen Q stress validation; shared inference and own-state reducers."""
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


p = module('q_p_base', ROOT.parent / 'keep-contract-validation-v1/run.py')
v2 = module('q_v2', ROOT / 'contract.py')
base = p.base
save = base.save


def score(benchmark, records):
    results = {}
    for mode, guard in [('baseline_restore', None), ('keep_v1', p.keep), ('keep_v2', v2)]:
        rows, final, damage = [], 0, 0
        for name, turns in benchmark.items():
            state, expected = dict(base.INITIAL), dict(base.INITIAL)
            for i, turn in enumerate(turns, 1):
                prior, previous_gold = dict(state), dict(expected)
                record = records[f'{name}-{i}']
                assert record['request'] == turn['request']
                operations, selected = base.noop.select_noop([record['first'], record['second']], turn['request'], state)
                state = base.apply_operations(state, operations, turn['request'])
                state, reset_rules = base.contract.enforce(state, turn['request'])
                keep_rules = {}
                if guard:
                    state, keep_rules = guard.enforce(state, turn['request'], prior)
                expected.update(turn['updates'])
                corrupted = [k for k in state if prior[k] == previous_gold[k] == expected[k] and state[k] != expected[k]]
                damage += len(corrupted)
                rows.append({'dialogue': name, 'turn': i, 'observed': dict(state), 'expected': dict(expected),
                             'exact': state == expected, 'correct_slots': sum(state[k] == expected[k] for k in state),
                             'newly_corrupted_slots': corrupted, 'selected': selected,
                             'reset_rules': reset_rules, 'keep_rules': keep_rules})
            final += state == expected
        results[mode] = {'exact_turns': sum(r['exact'] for r in rows), 'turns': len(rows),
                         'correct_slots': sum(r['correct_slots'] for r in rows), 'slots': len(rows) * 6,
                         'exact_final_dialogues': final, 'newly_corrupted_unchanged_slots': damage,
                         'protected_field_events': sum(len(r['keep_rules']) for r in rows), 'rows': rows}
    return results


def frozen_files():
    previous = json.loads((ROOT.parent / 'keep-contract-validation-v1/frozen.json').read_text())
    files = [REPO / name for name in previous if name != 'model_revision']
    files += [ROOT / name for name in ['run.py', 'contract.py', 'benchmark.json', 'PROTOCOL.md', 'test_contract.py']]
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def main():
    frozen = {**frozen_files(), 'model_revision': base.REVISION}
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
                assert records[key]['request'] == turn['request']
                continue
            if extractor is None:
                from huggingface_hub import snapshot_download
                from mlx_lm import load
                extractor = base.StateExtractor.__new__(base.StateExtractor)
                extractor.model, extractor.tokenizer = load(snapshot_download(base.MODEL, revision=base.REVISION, local_files_only=True))
            start = time.monotonic()
            first = extractor.ask(base.SYSTEM, turn['request'], max_tokens=260, examples=base.EXAMPLES)
            user = turn['request'] + '\nProposed patch: ' + first + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
            second = extractor.ask(base.SYSTEM, user, max_tokens=260, examples=base.EXAMPLES)
            records[key] = {'request': turn['request'], 'first': first, 'second_user': user,
                            'second': second, 'seconds': time.monotonic() - start}
            save(path, records)
            print('SAVED', key, flush=True)
    results = score(benchmark, records)
    save(ROOT / 'results.json', {'complete': True, 'actual_model_calls': len(records) * 2, 'methods': results})
    print(json.dumps({m: {k: v for k, v in row.items() if k != 'rows'} for m, row in results.items()}, indent=2), flush=True)


if __name__ == '__main__':
    main()
