"""Frozen development run on previously observed V1–V4 dialogues."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE = ROOT.parent / 'coverage-validation-v1'
spec = importlib.util.spec_from_file_location('action_method', ROOT / 'method.py')
method = importlib.util.module_from_spec(spec)
spec.loader.exec_module(method)
from request_state import StateExtractor, MODEL
REVISION = '4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25'


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def main():
    files = [Path(__file__), ROOT / 'method.py', ROOT / 'PROTOCOL.md', SOURCE / 'benchmark.json',
             REPO / 'local-studio/request_state.py']
    frozen = {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    frozen['model_revision'] = REVISION
    path = ROOT / 'frozen.json'
    if path.exists():
        assert json.loads(path.read_text()) == frozen, 'Frozen inputs changed'
    else:
        save(path, frozen)
    benchmark = json.loads((SOURCE / 'benchmark.json').read_text())['histories']
    path = ROOT / 'transcripts.json'
    transcripts = json.loads(path.read_text()) if path.exists() else {}
    extractor = None
    for name, turns in benchmark.items():
        for i, turn in enumerate(turns, 1):
            key = f'{name}-{i}'
            if key in transcripts:
                continue
            if extractor is None:
                from huggingface_hub import snapshot_download
                from mlx_lm import load
                extractor = StateExtractor.__new__(StateExtractor)
                extractor.model, extractor.tokenizer = load(snapshot_download(MODEL, revision=REVISION, local_files_only=True))
            request = turn['request']
            start = time.monotonic()
            plan = extractor.ask(method.PLAN_SYSTEM, request, max_tokens=260, examples=method.PLAN_EXAMPLES)
            try:
                parsed = method.parse_plan(plan)
                plan_error = None
            except (ValueError, TypeError) as error:
                parsed = {key: 'keep' for key in method.INITIAL}
                plan_error = str(error)
            user = 'Request: ' + request + '\nAction plan: ' + json.dumps(parsed)
            values = extractor.ask(method.VALUE_SYSTEM, user, max_tokens=260, examples=method.VALUE_EXAMPLES)
            transcripts[key] = {'request': request, 'plan': plan, 'plan_error': plan_error,
                                'values_user': user, 'values': values, 'seconds': time.monotonic() - start}
            save(path, transcripts)
            print('SAVED', key, flush=True)
    rows, damage, final = [], 0, 0
    for name, turns in benchmark.items():
        state, expected = dict(method.INITIAL), dict(method.INITIAL)
        for i, turn in enumerate(turns, 1):
            previous, old_expected = dict(state), dict(expected)
            record = transcripts[f'{name}-{i}']
            state, errors = method.compile_update(state, turn['request'], record['plan'], record['values'])
            expected.update(turn['updates'])
            damage += sum(previous[k] == old_expected[k] == expected[k] and state[k] != expected[k] for k in state)
            rows.append({'dialogue': name, 'turn': i, 'expected': dict(expected), 'observed': dict(state),
                         'exact': state == expected, 'correct_slots': sum(state[k] == expected[k] for k in state),
                         'errors': errors})
        final += state == expected
    result = {'development_only': True, 'complete': True, 'actual_model_calls': len(transcripts) * 2,
              'exact_turns': sum(r['exact'] for r in rows), 'turns': len(rows),
              'correct_slots': sum(r['correct_slots'] for r in rows), 'slots': len(rows) * 6,
              'exact_final_dialogues': final, 'newly_corrupted_unchanged_slots': damage,
              'seconds': sum(r['seconds'] for r in transcripts.values()), 'rows': rows}
    save(ROOT / 'results.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

