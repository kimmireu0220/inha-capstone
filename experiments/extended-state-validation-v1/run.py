"""Frozen, resumable extension of the final state-update comparison."""
import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
spec = importlib.util.spec_from_file_location('extended_previous', ROOT.parent/'single-extraction-validation-v1/run.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
base = previous.parent.parent.core.source.base


def save(path, data):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    temporary.replace(path)


def freeze():
    frozen = previous.freeze()
    paths = set(frozen['sha256'])
    paths.update(str((ROOT/name).relative_to(REPO)) for name in ['run.py', 'benchmark.json', 'PROTOCOL.md', 'test_design.py'])
    frozen['sha256'] = {p: hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in sorted(paths)}
    return json.loads(json.dumps(frozen))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-only', action='store_true')
    parser.add_argument('--model', choices=['all', 'qwen3', 'llama32'], default='all')
    args = parser.parse_args()
    frozen = freeze()
    target = ROOT/'frozen.json'
    if target.exists():
        assert json.loads(target.read_text()) == frozen, 'Frozen inputs changed'
    else:
        save(target, frozen)
    if args.freeze_only:
        print('Frozen 96 requests, labels, methods and model settings')
        return
    histories = json.loads((ROOT/'benchmark.json').read_text())['histories']
    for key, info in frozen['models'].items():
        if args.model not in ['all', key]:
            continue
        path = ROOT/f'transcripts-{key}.json'
        records = json.loads(path.read_text()) if path.exists() else {}
        attempt_path = ROOT/f'attempts-{key}.json'
        attempts = json.loads(attempt_path.read_text()) if attempt_path.exists() else []
        extractor = None
        for name, requests in histories.items():
            for i, item in enumerate(requests, 1):
                rid = f'{name}-{i}'
                record = records.setdefault(rid, dict(request=item['request']))
                assert record['request'] == item['request']
                for phase in ['first', 'second']:
                    if phase in record:
                        continue
                    if extractor is None:
                        from huggingface_hub import snapshot_download
                        from mlx_lm import load
                        extractor = base.StateExtractor.__new__(base.StateExtractor)
                        extractor.model, extractor.tokenizer = load(snapshot_download(info['model'], revision=info['revision'], local_files_only=True))
                    user = item['request']
                    if phase == 'second':
                        user += '\nProposed patch: '+record['first']+'\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
                        record['second_user'] = user
                    attempt = dict(request_id=rid, phase=phase, status='started', started_unix=time.time())
                    attempts.append(attempt)
                    save(attempt_path, attempts)
                    start = time.monotonic()
                    try:
                        record[phase] = extractor.ask(base.SYSTEM, user, max_tokens=260, examples=base.EXAMPLES)
                    except Exception as exc:
                        attempt.update(status='error', error=type(exc).__name__+': '+str(exc))
                        save(attempt_path, attempts)
                        raise
                    record[phase+'_seconds'] = time.monotonic()-start
                    save(path, records)
                    attempt.update(status='completed', seconds=record[phase+'_seconds'])
                    save(attempt_path, attempts)
                    print('SAVED', key, rid, phase, flush=True)
        save(ROOT/f'results-{key}.json', dict(complete=True, model=info,
             actual_model_attempts=len(attempts), completed_responses=sum('first' in r for r in records.values())+sum('second' in r for r in records.values()),
             methods=previous.score(histories, records)))
        print('COMPLETE', key, len(records), flush=True)
        del extractor
        gc.collect()
        import mlx.core as mx
        mx.clear_cache()


if __name__ == '__main__':
    main()
