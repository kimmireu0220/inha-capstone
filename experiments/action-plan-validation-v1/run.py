"""Budget-matched frozen validation for direct-patch review and action/value separation."""
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


action = module('fixed_action_method', ROOT.parent / 'action-plan-v2/method.py')
direct = module('fixed_direct_method', ROOT.parent / 'coverage-repair-v1/run.py')
noop = module('fixed_noop_method', ROOT.parent / 'coverage-repair-v1/ablation.py')
from request_state import StateExtractor, MODEL, SYSTEM, EXAMPLES
REVISION = direct.REVISION


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def score(benchmark, records):
    results = {}
    for mode in ['first_only', 'generic', 'generic_noop', 'action', 'action_atomic']:
        rows, final, damage = [], 0, 0
        for name, turns in benchmark.items():
            state, expected = dict(action.INITIAL), dict(action.INITIAL)
            for i, turn in enumerate(turns, 1):
                old_state, old_expected = dict(state), dict(expected)
                key = f'{name}-{i}'
                if mode.startswith('action'):
                    record = records[key + '-action']
                    state, errors = action.compile_update(state, turn['request'], record['first'], record['second'])
                    if mode == 'action_atomic' and errors:
                        state = old_state
                else:
                    record = records[key + '-generic']
                    raws = [record['first']] + ([] if mode == 'first_only' else [record['second']])
                    if mode == 'generic_noop':
                        operations, selected = noop.select_noop(raws, turn['request'], state)
                        errors = {} if selected is not None else {'patch': 'No valid response'}
                    else:
                        operations, selected, reasons = direct.select(raws, turn['request'])
                        errors = {'patch': reasons} if reasons else {}
                    state = action.apply_operations(state, operations, turn['request'])
                expected.update(turn['updates'])
                corrupted = [k for k in state if old_state[k] == old_expected[k] == expected[k]
                             and state[k] != expected[k]]
                damage += len(corrupted)
                rows.append({'dialogue': name, 'turn': i, 'observed': dict(state), 'expected': dict(expected),
                             'exact': state == expected, 'correct_slots': sum(state[k] == expected[k] for k in state),
                             'newly_corrupted_slots': corrupted, 'errors': errors})
            final += state == expected
        results[mode] = {'exact_turns': sum(r['exact'] for r in rows), 'turns': len(rows),
                         'correct_slots': sum(r['correct_slots'] for r in rows), 'slots': len(rows) * 6,
                         'exact_final_dialogues': final, 'newly_corrupted_unchanged_slots': damage, 'rows': rows}
    return results


def main():
    files = [Path(__file__), ROOT / 'benchmark.json', ROOT / 'PROTOCOL.md',
             ROOT.parent / 'action-plan-v2/method.py', ROOT.parent / 'coverage-repair-v1/run.py',
             ROOT.parent / 'coverage-repair-v1/ablation.py', REPO / 'local-studio/request_state.py']
    frozen = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    frozen['model_revision'] = REVISION
    path = ROOT / 'frozen.json'
    if path.exists():
        assert json.loads(path.read_text()) == frozen, 'Frozen validation changed'
    else:
        save(path, frozen)
    benchmark = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    path = ROOT / 'transcripts.json'
    records = json.loads(path.read_text()) if path.exists() else {}
    extractor = None
    for hi, (name, turns) in enumerate(benchmark.items()):
        for ti, turn in enumerate(turns, 1):
            order = ['generic', 'action'] if (hi + ti) % 2 else ['action', 'generic']
            for mode in order:
                key = f'{name}-{ti}-{mode}'
                if key in records:
                    continue
                if extractor is None:
                    from huggingface_hub import snapshot_download
                    from mlx_lm import load
                    extractor = StateExtractor.__new__(StateExtractor)
                    extractor.model, extractor.tokenizer = load(snapshot_download(MODEL, revision=REVISION, local_files_only=True))
                request = turn['request']
                start = time.monotonic()
                if mode == 'generic':
                    first = extractor.ask(SYSTEM, request, max_tokens=260, examples=EXAMPLES)
                    user = (request + '\nProposed patch: ' + first
                            + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.')
                    second = extractor.ask(SYSTEM, user, max_tokens=260, examples=EXAMPLES)
                else:
                    first = extractor.ask(action.PLAN_SYSTEM, request, max_tokens=260, examples=action.PLAN_EXAMPLES)
                    try:
                        plan = action.parse_plan(first)
                    except (ValueError, TypeError):
                        plan = {k: 'keep' for k in action.INITIAL}
                    user = 'Request: ' + request + '\nAction plan: ' + json.dumps(plan)
                    second = extractor.ask(action.VALUE_SYSTEM, user, max_tokens=260, examples=action.VALUE_EXAMPLES)
                records[key] = {'request': request, 'first': first, 'second_user': user, 'second': second,
                                'seconds': time.monotonic() - start}
                save(path, records)
                print('SAVED', key, flush=True)
    results = score(benchmark, records)
    save(ROOT / 'results.json', {'complete': True, 'actual_model_calls': len(records) * 2,
                                'methods': results})
    print(json.dumps({m: {k: v for k, v in row.items() if k != 'rows'} for m, row in results.items()}, indent=2), flush=True)


if __name__ == '__main__':
    main()
