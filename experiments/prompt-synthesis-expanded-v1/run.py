"""Generate the preregistered 108 conditions, reusing the 12 identical H1 runs."""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OLD = ROOT.parent / 'prompt-synthesis-v1'
PEOPLE = [f'R{i:02d}' for i in range(1, 7)]
HISTORIES = ['H1', 'H2', 'H3']
SEEDS = [42, 314]
MODES = ['history', 'state', 'agent']
MODEL = 'Runpod/FLUX.2-klein-4B-mflux-4bit'
CLI = REPO / '.venv-local-image/bin/mflux-generate-flux2-edit'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def main():
    references = {p: ROOT / 'references' / f'{p}.png' for p in PEOPLE}
    prompts = {(h, m): ROOT / 'prompts' / f'{h}-{m}.txt'
               for h in HISTORIES for m in MODES}
    plan = {
        'people': {p: sha(path) for p, path in references.items()},
        'prompts': {f'{h}-{m}': sha(path) for (h, m), path in prompts.items()},
        'histories': {h: sha(ROOT / 'histories' / f'{h}.json') for h in HISTORIES},
        'protocol_sha256': sha(ROOT / 'PROTOCOL.md'),
        'prompt_audit_sha256': sha(ROOT / 'prompt-audit.json'),
        'prepare_manifest_sha256': sha(ROOT / 'prepare-manifest.json'),
        'people_order': PEOPLE, 'history_order': HISTORIES, 'seeds': SEEDS,
        'modes': MODES, 'model': MODEL, 'steps': 4,
        'expected_outputs': 108, 'reused_outputs': 12,
    }
    plan_path = ROOT / 'plan.json'
    if plan_path.exists():
        assert json.loads(plan_path.read_text()) == plan, 'Frozen plan changed'
    else:
        save(plan_path, plan)

    ledger_path = ROOT / 'calls.json'
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
    else:
        old_calls = json.loads((OLD / 'calls.json').read_text())['calls']
        assert len(old_calls) == 12
        ledger = {'calls': []}
        for old in old_calls:
            person, mode, seed = old['person'], old['mode'], old['seed']
            assert person in PEOPLE[:2] and mode in MODES and seed in SEEDS
            ref, prompt = references[person], prompts[('H1', mode)]
            folder = OLD / old['folder']
            assert sha(ref) == old['input_sha256'] == old['source_sha256']
            assert sha(prompt) == old['prompt_sha256']
            assert sha(folder / 'input.png') == old['input_sha256']
            assert sha(folder / 'prompt.txt') == old['prompt_sha256']
            assert sha(folder / 'output.png') == old['output_sha256']
            ledger['calls'].append({**old, 'history': 'H1', 'reused': True,
                'folder': str(Path('..') / folder.relative_to(ROOT.parent))})
        save(ledger_path, ledger)

    seen = {(c['person'], c['history'], c['seed'], c['mode']) for c in ledger['calls']}
    assert len(seen) == len(ledger['calls'])
    for person_i, person in enumerate(PEOPLE):
        reference = references[person]
        with Image.open(reference) as image:
            width, height = image.size
        for history_i, history in enumerate(HISTORIES):
            for seed_i, seed in enumerate(SEEDS):
                shift = (person_i + history_i + seed_i) % len(MODES)
                for mode in MODES[shift:] + MODES[:shift]:
                    key = (person, history, seed, mode)
                    if key in seen:
                        continue
                    prompt = prompts[(history, mode)]
                    folder = ROOT / 'generated' / f'{person}-{history}-{seed}-{mode}'
                    folder.mkdir(parents=True, exist_ok=True)
                    output = folder / 'output.png'
                    if output.exists():
                        raise RuntimeError(f'Unrecorded output exists: {output}')
                    shutil.copyfile(reference, folder / 'input.png')
                    shutil.copyfile(prompt, folder / 'prompt.txt')
                    command = [str(CLI), '--model', MODEL, '--base-model',
                        'flux2-klein-4b', '--quantize', '4', '--low-ram',
                        '--image-paths', str(folder / 'input.png'),
                        '--prompt-file', str(folder / 'prompt.txt'), '--width', str(width),
                        '--height', str(height), '--steps', '4', '--seed', str(seed),
                        '--output', str(output)]
                    save(ROOT / 'running.json', {'status': 'running', 'person': person,
                        'history': history, 'seed': seed, 'mode': mode,
                        'completed': len(ledger['calls']), 'expected': 108})
                    print('START', person, history, seed, mode, flush=True)
                    start = time.monotonic()
                    with (folder / 'model.log').open('w') as log:
                        result = subprocess.run(command, cwd=REPO, stdout=log,
                            stderr=subprocess.STDOUT, timeout=900)
                    if result.returncode or not output.exists():
                        save(folder / 'failure.json', {'returncode': result.returncode,
                            'output_exists': output.exists()})
                        raise RuntimeError(f'Generation failed: {key}')
                    with Image.open(output) as image:
                        image.verify()
                    call = {'person': person, 'history': history, 'seed': seed,
                        'mode': mode, 'reused': False, 'source_sha256': sha(reference),
                        'input_sha256': sha(folder / 'input.png'),
                        'prompt_sha256': sha(folder / 'prompt.txt'),
                        'output_sha256': sha(output), 'width': width, 'height': height,
                        'seconds': time.monotonic() - start,
                        'folder': str(folder.relative_to(ROOT))}
                    ledger['calls'].append(call)
                    seen.add(key)
                    save(ledger_path, ledger)
                    print('DONE', len(ledger['calls']), '/108', *key, flush=True)
    assert len(ledger['calls']) == 108
    save(ROOT / 'running.json', {'status': 'complete', 'outputs': 108})


if __name__ == '__main__':
    main()
