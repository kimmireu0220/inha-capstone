"""Run every fixed condition; resume only from verified ledger entries."""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PEOPLE = [f'R{i:02d}' for i in range(1, 7)]
HISTORIES = ['T1', 'T2', 'T3', 'T4']
SEEDS = [42, 314]
MODES = ['agent', 'tracked']
MODEL = 'Runpod/FLUX.2-klein-4B-mflux-4bit'
CLI = REPO / '.venv-local-image/bin/mflux-generate-flux2-edit'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def main():
    manifest = json.loads((ROOT / 'prepare-manifest.json').read_text())
    assert sha(ROOT / 'PROTOCOL.md') == manifest['inputs']['protocol']
    assert sha(ROOT / 'benchmark.json') == manifest['inputs']['benchmark']
    assert sha(REPO / 'local-studio/request_state.py') == manifest['inputs']['method']
    prompts = {(h, m): ROOT / 'prompts' / f'{h}-{m}.txt' for h in HISTORIES for m in MODES}
    references = {p: ROOT / 'references' / f'{p}.png' for p in PEOPLE}
    for (h, m), path in prompts.items():
        assert sha(path) == manifest['prompts'][f'{h}-{m}']
    plan = {'people': {p: sha(path) for p, path in references.items()},
        'prompts': {f'{h}-{m}': sha(path) for (h, m), path in prompts.items()},
        'prepare_manifest_sha256': sha(ROOT / 'prepare-manifest.json'),
        'protocol_sha256': sha(ROOT / 'PROTOCOL.md'),
        'benchmark_sha256': sha(ROOT / 'benchmark.json'),
        'method_sha256': manifest['inputs']['method'], 'runner_sha256': sha(Path(__file__)),
        'people_order': PEOPLE, 'histories': HISTORIES, 'seeds': SEEDS,
        'modes': MODES, 'model': MODEL, 'steps': 4, 'expected_outputs': 96}
    if (ROOT / 'plan.json').exists():
        assert json.loads((ROOT / 'plan.json').read_text()) == plan
    else:
        save(ROOT / 'plan.json', plan)
    ledger_path = ROOT / 'calls.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'calls': []}
    seen = set()
    for call in ledger['calls']:
        folder = ROOT / call['folder']
        for name, key in [('input.png', 'input_sha256'), ('prompt.txt', 'prompt_sha256'),
                          ('output.png', 'output_sha256')]:
            assert sha(folder / name) == call[key]
        seen.add((call['person'], call['history'], call['seed'], call['mode']))
    assert len(seen) == len(ledger['calls'])
    for hi, history in enumerate(HISTORIES):
        for pi, person in enumerate(PEOPLE):
            reference = references[person]
            with Image.open(reference) as image:
                width, height = image.size
            for si, seed in enumerate(SEEDS):
                order = MODES if (hi + pi + si) % 2 == 0 else list(reversed(MODES))
                for mode in order:
                    key = (person, history, seed, mode)
                    if key in seen:
                        continue
                    folder = ROOT / 'generated' / f'{person}-{history}-{seed}-{mode}'
                    folder.mkdir(parents=True, exist_ok=True)
                    if (folder / 'output.png').exists():
                        raise RuntimeError(f'Unrecorded output: {folder}')
                    shutil.copyfile(reference, folder / 'input.png')
                    shutil.copyfile(prompts[(history, mode)], folder / 'prompt.txt')
                    command = [str(CLI), '--model', MODEL, '--base-model', 'flux2-klein-4b',
                        '--quantize', '4', '--low-ram', '--image-paths', str(folder / 'input.png'),
                        '--prompt-file', str(folder / 'prompt.txt'), '--width', str(width),
                        '--height', str(height), '--steps', '4', '--seed', str(seed),
                        '--output', str(folder / 'output.png')]
                    save(ROOT / 'running.json', {'status': 'running', 'condition': list(key),
                        'completed': len(seen), 'expected': 96})
                    print('START', *key, flush=True)
                    started = time.monotonic()
                    with (folder / 'model.log').open('w') as log:
                        result = subprocess.run(command, cwd=REPO, stdout=log,
                            stderr=subprocess.STDOUT, timeout=900)
                    if result.returncode or not (folder / 'output.png').exists():
                        save(folder / 'failure.json', {'returncode': result.returncode})
                        raise RuntimeError(f'Failed condition: {key}')
                    with Image.open(folder / 'output.png') as image:
                        image.verify()
                    call = {'person': person, 'history': history, 'seed': seed, 'mode': mode,
                        'source_sha256': sha(reference), 'input_sha256': sha(folder / 'input.png'),
                        'prompt_sha256': sha(folder / 'prompt.txt'),
                        'output_sha256': sha(folder / 'output.png'), 'width': width, 'height': height,
                        'seconds': time.monotonic() - started, 'folder': str(folder.relative_to(ROOT))}
                    ledger['calls'].append(call)
                    seen.add(key)
                    save(ledger_path, ledger)
                    print('DONE', len(seen), '/96', *key, round(call['seconds'], 1), flush=True)
    assert len(seen) == 96
    save(ROOT / 'running.json', {'status': 'complete', 'outputs': 96})


if __name__ == '__main__':
    main()
