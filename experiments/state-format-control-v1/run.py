"""Evaluate all 48 control conditions, reusing only exactly matched inputs."""
import json
import shutil
import subprocess
import time
from pathlib import Path
from PIL import Image
from prepare import ROOT, REPO, SOURCE, save, sha

CLI = REPO / '.venv-local-image/bin/mflux-generate-flux2-edit'


def signature(row):
    return tuple(row[key] for key in ['input_sha256', 'prompt_sha256', 'model',
                                      'steps', 'width', 'height', 'seed'])


def verify_files(root, row):
    for name, key in [('input.png', 'input_sha256'), ('prompt.txt', 'prompt_sha256'),
                      ('output.png', 'output_sha256')]:
        assert sha(root / row['folder'] / name) == row[key], (row['folder'], name)


def main():
    original = json.loads((SOURCE / 'plan.json').read_text())
    source_calls = json.loads((SOURCE / 'calls.json').read_text())['calls']
    expected = {(p, h, s, m) for p in original['people_order']
                for h in original['histories'] for s in original['seeds']
                for m in original['modes']}
    actual = {(r['person'], r['history'], r['seed'], r['mode']) for r in source_calls}
    assert actual == expected and len(source_calls) == 96, 'Finish source batch first'
    manifest = json.loads((ROOT / 'prepare-manifest.json').read_text())
    for relative, digest in manifest['inputs'].items():
        assert sha(REPO / relative) == digest, relative
    for group in ['prompts', 'transcripts']:
        for name, digest in manifest[group].items():
            assert sha(ROOT / 'prompts' / name) == digest, name
    for person, digest in original['people'].items():
        assert sha(SOURCE / 'references' / f'{person}.png') == digest
    candidates = {}
    for row in source_calls:
        verify_files(SOURCE, row)
        assert row['input_sha256'] == original['people'][row['person']]
        assert row['prompt_sha256'] == original['prompts'][row['history'] + '-' + row['mode']]
        enriched = {**row, 'model': original['model'], 'steps': original['steps']}
        candidates.setdefault(signature(enriched), []).append(enriched)
    plan = {'source_plan_sha256': sha(SOURCE / 'plan.json'),
            'source_calls_sha256': sha(SOURCE / 'calls.json'),
            'prepare_manifest_sha256': sha(ROOT / 'prepare-manifest.json'),
            'runner_sha256': sha(Path(__file__)), 'model': original['model'],
            'steps': original['steps'], 'expected_outputs': 48,
            'reuse_rule': 'Exact input, prompt, model, steps, width, height, seed; no score selection'}
    if (ROOT / 'plan.json').exists():
        assert json.loads((ROOT / 'plan.json').read_text()) == plan
    else:
        save(ROOT / 'plan.json', plan)
    ledger_path = ROOT / 'calls.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'calls': []}
    seen = set()
    for row in ledger['calls']:
        verify_files(ROOT, row)
        seen.add((row['person'], row['history'], row['seed']))
    assert len(seen) == len(ledger['calls'])
    for history in original['histories']:
        prompt = ROOT / 'prompts' / f'{history}-structured.txt'
        for person in original['people_order']:
            reference = SOURCE / 'references' / f'{person}.png'
            with Image.open(reference) as image:
                width, height = image.size
            for seed in original['seeds']:
                key = (person, history, seed)
                if key in seen:
                    continue
                folder = ROOT / 'generated' / f'{person}-{history}-{seed}-structured'
                folder.mkdir(parents=True, exist_ok=True)
                if (folder / 'output.png').exists():
                    raise RuntimeError(f'Unrecorded output: {folder}')
                shutil.copyfile(reference, folder / 'input.png')
                shutil.copyfile(prompt, folder / 'prompt.txt')
                row = {'person': person, 'history': history, 'seed': seed,
                       'mode': 'structured', 'model': plan['model'], 'steps': plan['steps'],
                       'input_sha256': sha(reference), 'prompt_sha256': sha(prompt),
                       'width': width, 'height': height, 'folder': str(folder.relative_to(ROOT))}
                matches = candidates.get(signature(row), [])
                if matches:
                    # Deterministic path order, never an image or quality criterion.
                    source = sorted(matches, key=lambda r: r['folder'])[0]
                    shutil.copyfile(SOURCE / source['folder'] / 'output.png', folder / 'output.png')
                    row.update({'reused': True, 'reused_from': source['folder'],
                                'reused_output_sha256': source['output_sha256'],
                                'seconds': 0, 'new_generation_calls': 0})
                else:
                    command = [str(CLI), '--model', plan['model'], '--base-model', 'flux2-klein-4b',
                               '--quantize', '4', '--low-ram', '--image-paths', str(folder / 'input.png'),
                               '--prompt-file', str(folder / 'prompt.txt'), '--width', str(width),
                               '--height', str(height), '--steps', str(plan['steps']), '--seed', str(seed),
                               '--output', str(folder / 'output.png')]
                    save(ROOT / 'running.json', {'status': 'running', 'condition': list(key),
                                                 'completed': len(seen), 'expected': 48})
                    print('START', *key, flush=True)
                    started = time.monotonic()
                    with (folder / 'model.log').open('w') as log:
                        result = subprocess.run(command, cwd=REPO, stdout=log,
                                                stderr=subprocess.STDOUT, timeout=900)
                    if result.returncode or not (folder / 'output.png').exists():
                        save(folder / 'failure.json', {'returncode': result.returncode})
                        raise RuntimeError(f'Failed condition: {key}')
                    row.update({'reused': False, 'seconds': time.monotonic() - started,
                                'new_generation_calls': 1})
                with Image.open(folder / 'output.png') as image:
                    image.verify()
                row['output_sha256'] = sha(folder / 'output.png')
                if row['reused']:
                    assert row['output_sha256'] == row['reused_output_sha256']
                ledger['calls'].append(row)
                seen.add(key)
                save(ledger_path, ledger)
                print('DONE', len(seen), '/48', *key, 'reused' if row['reused'] else 'new', flush=True)
    assert len(seen) == 48
    save(ROOT / 'running.json', {'status': 'complete', 'outputs': 48,
         'reused': sum(row['reused'] for row in ledger['calls']),
         'new_generations': sum(row['new_generation_calls'] for row in ledger['calls'])})


if __name__ == '__main__':
    main()
