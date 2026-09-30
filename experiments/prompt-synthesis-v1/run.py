"""Generate paired images for history, structured-state, and agent prompts."""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PEOPLE = {'R01': REPO / 'experiments/real-people-v1/reference-R01.png',
          'R02': REPO / 'experiments/real-people-v1/reference-R02.png'}
SEEDS = [42, 314]
MODES = ['history', 'state', 'agent']
PROMPTS = {mode: ROOT / f'{mode}-prompt.txt' for mode in MODES}
MODEL = 'Runpod/FLUX.2-klein-4B-mflux-4bit'
CLI = REPO / '.venv-local-image/bin/mflux-generate-flux2-edit'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)

def main():
    plan = {'people': {p: {'path': str(path.relative_to(REPO)), 'sha256': sha(path)}
                       for p, path in PEOPLE.items()},
            'seeds': SEEDS, 'modes': MODES,
            'prompt_sha256': {mode: sha(path) for mode, path in PROMPTS.items()},
            'history_sha256': sha(ROOT / 'history.json'),
            'prompt_audit_sha256': sha(ROOT / 'prompt-audit.json'),
            'protocol_sha256': sha(ROOT / 'PROTOCOL.md'),
            'prepare_code_sha256': sha(ROOT / 'prepare.py'),
            'model': MODEL, 'steps': 4, 'expected_outputs': 12}
    plan_path = ROOT / 'plan.json'
    if plan_path.exists():
        assert json.loads(plan_path.read_text()) == plan
    else:
        save(plan_path, plan)
    ledger_path = ROOT / 'calls.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'calls': []}
    for person_i, (person, reference) in enumerate(PEOPLE.items()):
        with Image.open(reference) as image:
            width, height = image.size
        for seed_i, seed in enumerate(SEEDS):
            order = MODES[(person_i + seed_i) % 3:] + MODES[:(person_i + seed_i) % 3]
            for mode in order:
                if any(c['person'] == person and c['seed'] == seed and c['mode'] == mode
                       for c in ledger['calls']):
                    continue
                folder = ROOT / 'generated' / f'{person}-{seed}-{mode}'
                folder.mkdir(parents=True, exist_ok=True)
                output = folder / 'output.png'
                if output.exists():
                    raise RuntimeError(f'Unrecorded output already exists: {output}')
                shutil.copyfile(reference, folder / 'input.png')
                shutil.copyfile(PROMPTS[mode], folder / 'prompt.txt')
                command = [str(CLI), '--model', MODEL, '--base-model', 'flux2-klein-4b',
                    '--quantize', '4', '--low-ram', '--image-paths', str(folder / 'input.png'),
                    '--prompt-file', str(folder / 'prompt.txt'), '--width', str(width),
                    '--height', str(height), '--steps', '4', '--seed', str(seed),
                    '--output', str(output)]
                save(ROOT / 'running.json', {'status': 'running', 'person': person,
                    'seed': seed, 'mode': mode, 'completed': len(ledger['calls'])})
                print('START', person, seed, mode, flush=True)
                start = time.monotonic()
                with (folder / 'model.log').open('w') as log:
                    result = subprocess.run(command, cwd=REPO, stdout=log,
                        stderr=subprocess.STDOUT, timeout=900)
                if result.returncode or not output.exists():
                    save(folder / 'failure.json', {'returncode': result.returncode,
                        'output_exists': output.exists()})
                    raise RuntimeError(f'Generation failed: {person} {seed} {mode}')
                with Image.open(output) as image:
                    image.verify()
                ledger['calls'].append({'person': person, 'seed': seed, 'mode': mode,
                    'source_sha256': sha(reference), 'input_sha256': sha(folder / 'input.png'),
                    'prompt_sha256': sha(folder / 'prompt.txt'), 'output_sha256': sha(output),
                    'width': width, 'height': height, 'seconds': time.monotonic() - start,
                    'folder': str(folder.relative_to(ROOT))})
                save(ledger_path, ledger)
                print('DONE', len(ledger['calls']), '/12', person, seed, mode, flush=True)
    save(ROOT / 'running.json', {'status': 'complete', 'outputs': len(ledger['calls'])})

if __name__ == '__main__':
    main()
