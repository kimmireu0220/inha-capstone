"""Freeze, stage and record native image_gen outputs without editing pixels.

Generation itself is performed by the built-in tool, not this script. Never
replace a completed output with a preferred variant.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
REFERENCES = ROOT.parent / 'state-tracking-v2/references'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['next', 'finish', 'failure', 'status'])
    parser.add_argument('--job')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--message')
    args = parser.parse_args()
    prepared = json.loads((ROOT / 'prepared.json').read_text())
    assert prepared['planned_backend'] == 'builtin'
    for name, digest in prepared['inputs'].items():
        assert sha(REPO / name) == digest, name
    scripts = ['goals.py', 'evaluate.py', 'measure_faces.py', 'preflight.py', 'summarize.py']
    frozen = {'backend': 'builtin_image_gen', 'model_revision': 'not_exposed', 'seed': 'not_exposed',
              'transparent_background': False, 'prepared_sha256': sha(ROOT / 'prepared.json'),
              'preflight_sha256': sha(ROOT / 'feasibility-preflight.json'), 'manager_sha256': sha(Path(__file__)),
              'evaluation_scripts_sha256': {name: sha(ROOT.parent / 'action-image-v1' / name) for name in scripts}}
    plan = ROOT / 'generation-plan.json'
    if plan.exists():
        assert json.loads(plan.read_text()) == frozen, 'Frozen native generation study changed'
    else:
        save(plan, frozen)
    jobs = {}
    for row in prepared['conditions']:
        jobs.setdefault(row['job'], row)
    ledger_path = ROOT / 'calls.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'backend': 'builtin_image_gen', 'calls': [], 'failures': []}
    done = {}
    for row in ledger['calls']:
        assert row['job'] in jobs and row['job'] not in done
        for name, digest in row['sha256'].items():
            assert sha(ROOT / row['folder'] / name) == digest
        done[row['job']] = row
    if args.command in ['finish', 'failure']:
        assert args.job in jobs and args.job not in done
        row = jobs[args.job]
        folder = ROOT / 'generated' / args.job
        started = json.loads((folder / 'started.json').read_text())
        if args.command == 'failure':
            assert args.message
            ledger['failures'].append({'job': args.job, 'message': args.message, 'time': time.time()})
            save(ledger_path, ledger)
            print('Failure preserved; no completed image added')
            return
        from PIL import Image
        assert args.output and args.output.is_absolute() and args.output.is_file()
        assert not (folder / 'output.png').exists(), 'Never overwrite a generated output'
        with Image.open(args.output) as image:
            width, height, fmt = image.width, image.height, image.format
            image.verify()
        assert fmt == 'PNG', 'Preserve native image encoding; PNG expected by this protocol'
        shutil.copyfile(args.output, folder / 'output.png')
        call = {'job': args.job, 'person': row['person'], 'folder': str(folder.relative_to(ROOT)),
                'backend': 'builtin_image_gen', 'native_output_path': str(args.output),
                'width': width, 'height': height, 'seconds_since_staging': time.time() - started['time'],
                'sha256': {name: sha(folder / name) for name in ['input.png', 'prompt.txt', 'output.png']}}
        ledger['calls'].append(call)
        save(ledger_path, ledger)
        done[args.job] = call
    remaining = [job for job in jobs if job not in done]
    progress = {'completed_unique_jobs': len(done), 'total_unique_jobs': len(jobs),
                'total_conditions': prepared['condition_count'], 'status': 'complete' if not remaining else 'running'}
    save(ROOT / 'running.json', progress)
    if args.command != 'next' or not remaining:
        print(json.dumps(progress))
        return
    job, row = remaining[0], jobs[remaining[0]]
    folder = ROOT / 'generated' / job
    folder.mkdir(parents=True, exist_ok=True)
    assert not (folder / 'output.png').exists(), 'Recover unrecorded output instead of generating again'
    if not (folder / 'started.json').exists():
        shutil.copyfile(REFERENCES / f'{row["person"]}.png', folder / 'input.png')
        (folder / 'prompt.txt').write_text(row['prompt'] + '\n')
        save(folder / 'started.json', {'time': time.time(), 'job': job})
    assert sha(folder / 'input.png') == sha(REFERENCES / f'{row["person"]}.png')
    assert (folder / 'prompt.txt').read_text() == row['prompt'] + '\n'
    print(json.dumps({**progress, 'job': job, 'prompt': row['prompt'],
                      'referenced_image_paths': [str((folder / 'input.png').resolve())],
                      'transparent_background': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
