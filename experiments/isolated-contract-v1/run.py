"""Frozen component interaction test using unchanged existing components."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
spec = importlib.util.spec_from_file_location('isolation_contract_source', ROOT.parent / 'request-contract-v3/run.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)
base, save = source.base, source.save
MODES = [('baseline_restore', False, False), ('isolated_restore', True, False),
         ('keep_remove', False, True), ('isolated_keep_remove', True, True)]


def score(benchmark, records):
    methods = {}
    for mode, isolate, guard in MODES:
        rows, final, damage = [], 0, 0
        for name, turns in benchmark.items():
            state, gold = dict(base.INITIAL), dict(base.INITIAL)
            for i, turn in enumerate(turns, 1):
                prior, old_gold = dict(state), dict(gold)
                record = records[f'{name}-{i}']
                assert record['request'] == turn['request']
                raws = [record['first'], record['second']]
                if isolate:
                    state, errors, selected = base.method.update(state, turn['request'], raws, atomic=False)
                else:
                    operations, selected = base.noop.select_noop(raws, turn['request'], state)
                    state = base.apply_operations(state, operations, turn['request'])
                    errors = {} if selected is not None else {'patch': 'No valid patch'}
                state, reset = base.contract.enforce(state, turn['request'])
                rules = {}
                if guard:
                    state, rules = source.contract.enforce(state, turn['request'], prior)
                gold.update(turn['updates'])
                corrupted = [k for k in state if prior[k] == old_gold[k] == gold[k] and state[k] != gold[k]]
                damage += len(corrupted)
                rows.append(dict(dialogue=name, turn=i, observed=dict(state), expected=dict(gold),
                                 exact=state == gold, correct_slots=sum(state[k] == gold[k] for k in state),
                                 newly_corrupted_slots=corrupted, errors=errors, selected=selected,
                                 reset_rules=reset, keep_rules=rules))
            final += state == gold
        methods[mode] = dict(exact_turns=sum(r['exact'] for r in rows), turns=len(rows),
                             correct_slots=sum(r['correct_slots'] for r in rows), slots=len(rows) * 6,
                             exact_final_dialogues=final, newly_corrupted_unchanged_slots=damage, rows=rows)
    return methods


def frozen_files():
    files = [REPO / name for name in source.frozen_files()]
    files += [ROOT / name for name in ['run.py', 'benchmark.json', 'PROTOCOL.md', 'test_run.py']]
    return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def main():
    freeze = {**frozen_files(), 'model_revision': base.REVISION}
    if (ROOT / 'frozen.json').exists():
        assert json.loads((ROOT / 'frozen.json').read_text()) == freeze
    else:
        save(ROOT / 'frozen.json', freeze)
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
            started = time.monotonic()
            first = extractor.ask(base.SYSTEM, turn['request'], max_tokens=260, examples=base.EXAMPLES)
            review = turn['request'] + '\nProposed patch: ' + first + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
            second = extractor.ask(base.SYSTEM, review, max_tokens=260, examples=base.EXAMPLES)
            records[key] = dict(request=turn['request'], first=first, second_user=review,
                                second=second, seconds=time.monotonic() - started)
            save(path, records)
            print('SAVED', key, flush=True)
    methods = score(benchmark, records)
    save(ROOT / 'results.json', dict(complete=True, actual_model_calls=len(records) * 2, methods=methods))
    print(json.dumps({m: {k: v for k, v in r.items() if k != 'rows'} for m, r in methods.items()}, indent=2))


if __name__ == '__main__':
    main()
