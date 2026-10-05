"""Resume local FLUX jobs only after an explicit execution configuration is supplied.

Preparing this runner does not execute images or imply backend confirmation.
"""
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from PIL import Image
from prepare import ROOT, REPO, REFERENCES, save, sha

MODEL = 'Runpod/FLUX.2-klein-4B-mflux-4bit'
REVISION = '7ee1b3aa8178a1240050490072196a57da2bf2a9'
CLI = REPO / '.venv-local-image/bin/mflux-generate-flux2-edit'


def main():
    config_path = ROOT / 'execution.json'
    if not config_path.exists():
        raise RuntimeError('Backend confirmation is pending; no images generated')
    config = json.loads(config_path.read_text())
    assert config['backend'] == 'local_flux' and config['user_confirmed'] is True
    assert config['model'] == MODEL and config['revision'] == REVISION
    assert config['steps'] == 4 and config['seed'] == 42
    cache = Path.home() / '.cache/huggingface/hub/models--Runpod--FLUX.2-klein-4B-mflux-4bit'
    assert (cache / 'refs/main').read_text().strip() == REVISION
    prepared = json.loads((ROOT / 'prepared.json').read_text())
    for name, digest in prepared['inputs'].items():
        assert sha(REPO / name) == digest, name
    inputs = {'prepared_sha256': sha(ROOT / 'prepared.json'), 'execution_sha256': sha(config_path),
              'runner_sha256': sha(Path(__file__)), 'model': MODEL, 'revision': REVISION,
              'steps': config['steps'], 'seed': config['seed']}
    plan_path = ROOT / 'generation-plan.json'
    if plan_path.exists():
        assert json.loads(plan_path.read_text()) == inputs, 'Frozen generation inputs changed'
    else:
        save(plan_path, inputs)
    jobs = {}
    for row in prepared['conditions']:
        jobs.setdefault(row['job'], row)
    ledger_path = ROOT / 'calls.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'calls': []}
    done = {}
    for record in ledger['calls']:
        folder = ROOT / record['folder']
        for filename in ['input.png', 'prompt.txt', 'output.png']:
            assert sha(folder / filename) == record['sha256'][filename], filename
        assert record['job'] in jobs and record['job'] not in done
        done[record['job']] = record
    environment = dict(os.environ, HF_HUB_OFFLINE='1')
    for job, row in jobs.items():
        if job in done:
            continue
        folder = ROOT / 'generated' / job
        folder.mkdir(parents=True, exist_ok=True)
        if (folder / 'output.png').exists():
            raise RuntimeError(f'Unrecorded output retained for recovery: {folder}')
        shutil.copyfile(REFERENCES / f'{row["person"]}.png', folder / 'input.png')
        (folder / 'prompt.txt').write_text(row['prompt'] + '\n')
        with Image.open(folder / 'input.png') as image:
            width, height = image.size
        command = [str(CLI), '--model', MODEL, '--base-model', 'flux2-klein-4b',
                   '--quantize', '4', '--low-ram', '--image-paths', str(folder / 'input.png'),
                   '--prompt-file', str(folder / 'prompt.txt'), '--width', str(width), '--height', str(height),
                   '--steps', '4', '--seed', '42', '--output', str(folder / 'output.png')]
        save(ROOT / 'running.json', {'status': 'running', 'job': job, 'completed_unique_jobs': len(done),
                                    'total_unique_jobs': len(jobs), 'total_conditions': 48})
        print('START', job, len(done), '/', len(jobs), flush=True)
        start = time.monotonic()
        with (folder / 'model.log').open('w') as log:
            process = subprocess.run(command, cwd=REPO, env=environment, stdout=log,
                                     stderr=subprocess.STDOUT, timeout=900)
        seconds = time.monotonic() - start
        if process.returncode or not (folder / 'output.png').exists():
            save(folder / 'failure.json', {'returncode': process.returncode, 'seconds': seconds})
            raise RuntimeError('Image generation failed: ' + job)
        with Image.open(folder / 'output.png') as image:
            image.verify()
        record = {'job': job, 'person': row['person'], 'folder': str(folder.relative_to(ROOT)),
                  'seconds': seconds, 'width': width, 'height': height,
                  'sha256': {name: sha(folder / name) for name in ['input.png', 'prompt.txt', 'output.png']}}
        ledger['calls'].append(record)
        save(ledger_path, ledger)
        done[job] = record
        print('DONE', job, flush=True)
    save(ROOT / 'running.json', {'status': 'complete', 'completed_unique_jobs': len(done),
                                'total_unique_jobs': len(jobs), 'total_conditions': 48})


if __name__ == '__main__':
    main()
