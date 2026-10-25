"""Frozen new-dialogue validation plus separately labeled development replay."""
import hashlib
import json
from pathlib import Path
import time

import method

ROOT = Path(__file__).resolve().parent
source = method.source


def score(histories, records):
    common = source.score(histories, records)
    results = {name: common[name] for name in ['baseline_restore', 'keep_remove']}
    for mode in ['normalized_atomic', 'isolated_keep_remove', 'normalized_isolated']:
        rows, final, damaged = [], 0, 0
        for name, turns in histories.items():
            state, gold = dict(source.base.INITIAL), dict(source.base.INITIAL)
            for i, turn in enumerate(turns, 1):
                prior, old_gold = dict(state), dict(gold)
                r = records[f'{name}-{i}']
                assert r['request'] == turn['request']
                raws = [r['first'], r['second']]
                if mode == 'isolated_keep_remove':
                    state, errors, selected = source.base.method.update(prior, turn['request'], raws, atomic=False)
                    state, reset = source.base.contract.enforce(state, turn['request'])
                    state, rules = source.contract.enforce(state, turn['request'], prior)
                    trace = dict(errors=errors, selected=selected, reset=reset, rules=rules)
                else:
                    state, trace = method.update(prior, turn['request'], raws, atomic=mode == 'normalized_atomic')
                gold.update(turn['updates'])
                bad = [k for k in state if prior[k] == old_gold[k] == gold[k] and state[k] != gold[k]]
                damaged += len(bad)
                rows.append(dict(dialogue=name, turn=i, observed=dict(state), expected=dict(gold),
                                 exact=state == gold, correct_slots=sum(state[k] == gold[k] for k in state),
                                 newly_corrupted_slots=bad, trace=trace))
            final += state == gold
        results[mode] = dict(exact_turns=sum(r['exact'] for r in rows), turns=len(rows),
                            correct_slots=sum(r['correct_slots'] for r in rows), slots=len(rows)*6,
                            exact_final_dialogues=final, newly_corrupted_unchanged_slots=damaged, rows=rows)
    for data in results.values():
        data['new_errors_vs_baseline'] = sum(a['exact'] and not b['exact'] for a, b in zip(
            results['baseline_restore']['rows'], data['rows'], strict=True))
    return results


def freeze():
    paths = set(source.frozen_files()) | {str((ROOT / name).relative_to(method.source.REPO))
        for name in ['run.py', 'method.py', 'benchmark.json', 'PROTOCOL.md', 'test_method.py']}
    return {'sha256': {p: hashlib.sha256((method.source.REPO / p).read_bytes()).hexdigest() for p in sorted(paths)},
            'model': source.base.MODEL, 'revision': source.base.REVISION,
            'temperature': 0, 'max_tokens': 260, 'examples': source.base.EXAMPLES}


def main():
    frozen = json.loads(json.dumps(freeze()))
    manifest = ROOT / 'frozen.json'
    if manifest.exists():
        assert json.loads(manifest.read_text()) == frozen, 'Frozen validation changed'
    else:
        source.save(manifest, frozen)
    histories = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    path = ROOT / 'transcripts.json'
    records = json.loads(path.read_text()) if path.exists() else {}
    extractor = None
    for name, turns in histories.items():
        for i, turn in enumerate(turns, 1):
            key = f'{name}-{i}'
            if key in records:
                assert records[key]['request'] == turn['request']
                continue
            if extractor is None:
                from huggingface_hub import snapshot_download
                from mlx_lm import load
                extractor = source.base.StateExtractor.__new__(source.base.StateExtractor)
                extractor.model, extractor.tokenizer = load(snapshot_download(source.base.MODEL,
                    revision=source.base.REVISION, local_files_only=True))
            start = time.monotonic()
            first = extractor.ask(source.base.SYSTEM, turn['request'], max_tokens=260, examples=source.base.EXAMPLES)
            user = turn['request'] + '\nProposed patch: ' + first + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
            second = extractor.ask(source.base.SYSTEM, user, max_tokens=260, examples=source.base.EXAMPLES)
            records[key] = dict(request=turn['request'], first=first, second_user=user,
                                second=second, seconds=time.monotonic()-start)
            source.save(path, records)
            print('SAVED', key, flush=True)
    source.save(ROOT / 'results.json', dict(complete=True, actual_model_calls=len(records)*2,
                                          methods=score(histories, records)))
    print('COMPLETE', len(records), flush=True)


if __name__ == '__main__':
    main()
