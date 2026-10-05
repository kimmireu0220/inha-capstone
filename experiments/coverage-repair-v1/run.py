"""Fixed-budget request-repair pilot. No image generation or annotations in prompts."""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / 'local-studio'))
from request_state import (StateExtractor, INITIAL, MENTIONS, SYSTEM, EXAMPLES,
                           unique_object, patch_operations, apply_operations, MODEL)

REVISION = '4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25'


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def parse(raw, request, coverage=False):
    patch = json.loads(raw[raw.find('{'):raw.rfind('}') + 1], object_pairs_hook=unique_object)
    if not isinstance(patch, dict):
        raise ValueError('Patch must be an object')
    if coverage:
        missing = [key for key, pattern in MENTIONS.items()
                   if re.search(pattern, request, re.I) and key not in patch]
        if missing:
            raise ValueError('Missing decisions for mentioned slots: ' + ', '.join(missing))
    return patch_operations(patch, request)


def select(raws, request, coverage=False):
    errors = []
    for index in reversed(range(len(raws))):
        try:
            return parse(raws[index], request, coverage), index, errors
        except (ValueError, TypeError, KeyError) as error:
            errors.append(str(error))
    return [], None, errors


def main():
    files = [Path(__file__), ROOT / 'benchmark.json', ROOT / 'PROTOCOL.md',
             REPO / 'local-studio/request_state.py']
    frozen = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    frozen['model_revision'] = REVISION
    manifest = ROOT / 'frozen.json'
    if manifest.exists():
        assert json.loads(manifest.read_text()) == frozen, 'Frozen experiment changed'
    else:
        save(manifest, frozen)
    histories = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    output = ROOT / 'transcripts.json'
    records = json.loads(output.read_text()) if output.exists() else {}
    extractor = None
    for hi, (name, turns) in enumerate(histories.items()):
        for ti, turn in enumerate(turns):
            key = f'{name}-{ti + 1}'
            if key in records:
                continue
            if extractor is None:
                from huggingface_hub import snapshot_download
                from mlx_lm import load
                extractor = StateExtractor.__new__(StateExtractor)
                cached = snapshot_download(MODEL, revision=REVISION, local_files_only=True)
                extractor.model, extractor.tokenizer = load(cached)
            request = turn['request']
            start = time.monotonic()
            first = extractor.ask(SYSTEM, request, max_tokens=260, examples=EXAMPLES)
            record = {'request': request, 'first': first, 'first_seconds': time.monotonic() - start}
            order = ['generic', 'coverage'] if (hi + ti) % 2 == 0 else ['coverage', 'generic']
            for mode in order:
                user = request + '\nProposed patch: ' + first
                user += '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
                if mode == 'coverage':
                    mentioned = [k for k, p in MENTIONS.items() if re.search(p, request, re.I)]
                    try:
                        parse(first, request, True)
                        diagnostic = 'No schema, lexical-support or coverage error detected.'
                    except (ValueError, TypeError, KeyError) as error:
                        diagnostic = str(error)
                    user += ('\nMentioned slots: ' + ', '.join(mentioned) + '\nValidator: ' + diagnostic
                             + '\nReturn an explicit decision for EVERY mentioned slot. Use keep when unchanged. '
                             'Do not omit background or prop decisions. Distinguish negated removals from removals.')
                start = time.monotonic()
                raw = extractor.ask(SYSTEM, user, max_tokens=260, examples=EXAMPLES)
                record[mode] = {'user': user, 'response': raw, 'seconds': time.monotonic() - start}
            records[key] = record
            save(output, records)
            print('SAVED', key, flush=True)
    # Annotation access for scoring happens after all inference has finished.
    results = {}
    for mode in ['first_only', 'generic', 'coverage']:
        rows = []
        for name, turns in histories.items():
            state, expected = dict(INITIAL), dict(INITIAL)
            for ti, turn in enumerate(turns):
                record = records[f'{name}-{ti + 1}']
                before = dict(expected)
                expected.update(turn['updates'])
                raws = [record['first']] + ([] if mode == 'first_only' else [record[mode]['response']])
                operations, selected, errors = select(raws, turn['request'], mode == 'coverage')
                state = apply_operations(state, operations, turn['request'])
                changed = [k for k in INITIAL if expected[k] != before[k]]
                unchanged = [k for k in INITIAL if expected[k] == before[k]]
                rows.append({'dialogue': name, 'turn': ti + 1, 'expected': dict(expected),
                             'observed': dict(state), 'exact': state == expected,
                             'correct_slots': sum(state[k] == expected[k] for k in INITIAL),
                             'changed_correct': sum(state[k] == expected[k] for k in changed),
                             'changed_total': len(changed),
                             'unchanged_wrong': sum(state[k] != expected[k] for k in unchanged),
                             'selected': selected, 'validation_errors': errors})
        results[mode] = {'exact_turns': sum(r['exact'] for r in rows), 'turns': len(rows),
                         'correct_slots': sum(r['correct_slots'] for r in rows), 'slots': len(rows) * 6,
                         'exact_final_dialogues': sum(r['exact'] for r in rows if r['turn'] == 4),
                         'unchanged_wrong': sum(r['unchanged_wrong'] for r in rows),
                         'changed_correct': sum(r['changed_correct'] for r in rows),
                         'changed_total': sum(r['changed_total'] for r in rows),
                         'rejected_turns': sum(r['selected'] is None for r in rows),
                         'logical_model_calls': len(rows) * (1 if mode == 'first_only' else 2),
                         'seconds': sum(r['first_seconds'] + (0 if mode == 'first_only' else r[mode]['seconds'])
                                        for r in records.values()), 'rows': rows}
    save(ROOT / 'results.json', {'complete': True, 'actual_model_calls': len(records) * 3, 'methods': results})
    for mode, result in results.items():
        print(mode, {k: v for k, v in result.items() if k != 'rows'}, flush=True)


if __name__ == '__main__':
    main()
