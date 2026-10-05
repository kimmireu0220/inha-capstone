"""Four-way contract ablation on one frozen set of producer responses."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


q = module('contract_v3_q_reducer', ROOT.parent / 'keep-contract-v2/run.py')
contract = module('contract_v3_method', ROOT / 'contract.py')
base, save = q.base, q.save


def score(benchmark, records):
    # Each invocation initializes its own full state trajectory; only the
    # deterministic guard changes. Never provide the gold prior to any method.
    results = {}
    original_guard = q.v2
    try:
        for name, use_keep, use_remove in [('baseline_restore', False, False), ('keep_only', True, False),
                                         ('remove_only', False, True), ('keep_remove', True, True)]:
            q.v2 = SimpleNamespace(enforce=lambda state, request, prior: contract.enforce(
                state, request, prior, use_keep=use_keep, use_remove=use_remove))
            row = q.score(benchmark, records)['keep_v2']
            row['contract_field_events'] = row.pop('protected_field_events')
            results[name] = row
    finally:
        q.v2 = original_guard
    return results


def frozen_files():
    files = [REPO / name for name in q.frozen_files()]
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
    methods = score(benchmark, records)
    save(ROOT / 'results.json', {'complete': True, 'actual_model_calls': len(records) * 2, 'methods': methods})
    print(json.dumps({m: {k: v for k, v in row.items() if k != 'rows'} for m, row in methods.items()}, indent=2), flush=True)


if __name__ == '__main__':
    main()
