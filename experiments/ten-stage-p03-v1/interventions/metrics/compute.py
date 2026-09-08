"""Run only after all six planned intervention images have completed.

.venv-metrics/bin/python experiments/ten-stage-p03-v1/interventions/metrics/compute.py

Reuse preregistered P03 ROI and exact sequential metric algorithms. No ratings
are read. Full image copies retain source bytes; analytical crops use fixed ROI.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import secrets
import shutil

import numpy as np
from PIL import Image
import torch
import lpips
from skimage.metrics import structural_similarity

OUT = Path(__file__).resolve().parent
INTERVENTIONS = OUT.parent
EXP = INTERVENTIONS.parent
ROOT = EXP.parents[1]
METHODS = ['baseline', 'repair', 'rollback', 'rebase']
CONFIG_SHA256 = '9af1e4f6f4d0c4e7e2d921de22a0c9a4301a421c6337efc38b5ce14ba0553995'
REQUIREMENTS = ['Small silver hoop earrings on both ears.',
                'A thin silver necklace with one small round silver pendant.']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def tensor(a):
    return torch.from_numpy(a.transpose(2, 0, 1).copy()).unsqueeze(0) * 2 - 1


def main():
    config_path = EXP / 'metrics/config.json'
    assert sha(config_path) == CONFIG_SHA256, 'Preregistered configuration changed'
    config = json.loads(config_path.read_text())
    roi = tuple(config['roi_xyxy'])
    assert roi == (352, 64, 672, 424)
    thresholds = config['thresholds']
    assert thresholds == {'mae_0_1_gte': 0.0288375, 'ssim_lte': 0.842874, 'lpips_alex_v0_1_gte': 0.0555075}
    prompts_path = INTERVENTIONS / 'prompts.json'
    jobs = json.loads(prompts_path.read_text())['jobs']
    assert sorted((j['run'], j['method']) for j in jobs) == sorted((r, m) for r in [1, 2] for m in METHODS[1:])
    assert all(j['stage'] == 2 and all('- ' + requirement in j['prompt'] for requirement in REQUIREMENTS) for j in jobs)
    sources = {(r, 'baseline'): EXP / f'run-{r}/step-2.png' for r in [1, 2]}
    for job in jobs:
        expected = INTERVENTIONS / f"run-{job['run']}/{job['method']}.png"
        assert Path(job['output']) == expected
        sources[(job['run'], job['method'])] = expected
    missing = [str(p) for p in sources.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError('All six interventions and both baselines required: ' + ', '.join(missing))
    prior_path = EXP / 'metrics/metrics.json'
    prior = json.loads(prior_path.read_text())
    assert prior['config_sha256'] == CONFIG_SHA256
    assert all(prior['first_alarm_steps'][f'run-{r}']['lpips'] == 2 for r in [1, 2])
    reference_path = ROOT / config['reference']
    assert sha(reference_path) == prior['reference_sha256']
    backbone = Path(torch.hub.get_dir()) / 'checkpoints/alexnet-owt-7be5be79.pth'
    linear = Path(lpips.__file__).parent / 'weights/v0.1/alex.pth'
    assert backbone.is_file() and linear.is_file(), 'Cached pretrained weights required'
    torch.set_num_threads(2)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    reference = Image.open(reference_path).convert('RGB')
    assert reference.size == (1024, 1536)
    ref = np.asarray(reference.crop(roi), dtype=np.float32) / 255.0
    candidates = {}
    for key, path in sources.items():
        candidate = Image.open(path).convert('RGB')
        assert candidate.size == reference.size, (path, candidate.size)
        candidates[key] = candidate
    network = lpips.LPIPS(net='alex', version='0.1', model_path=str(linear), verbose=False).cpu().eval()
    rows = []
    with torch.no_grad():
        ref_t = tensor(ref)
        for run in [1, 2]:
            for method in METHODS:
                arr = np.asarray(candidates[(run, method)].crop(roi), dtype=np.float32) / 255.0
                mae = float(np.mean(np.abs(arr - ref)))
                ssim = float(structural_similarity(ref, arr, channel_axis=2, data_range=1.0, win_size=7, gaussian_weights=False, use_sample_covariance=True))
                perceptual = float(network(ref_t, tensor(arr)).item())
                row = {'run': run, 'stage': 2, 'method': method, 'source_sha256': sha(sources[(run, method)]),
                       'mae_0_1': mae, 'mae_0_255': mae * 255, 'ssim': ssim, 'lpips_alex_v0_1': perceptual,
                       'alarms': {'mae': mae >= thresholds['mae_0_1_gte'], 'ssim': ssim <= thresholds['ssim_lte'],
                                  'lpips': perceptual >= thresholds['lpips_alex_v0_1_gte']}}
                if method == 'baseline':
                    old = next(r for r in prior['results'] if r['run'] == run and r['step'] == 2)
                    for field in ['source_sha256', 'mae_0_1', 'mae_0_255', 'ssim', 'lpips_alex_v0_1', 'alarms']:
                        assert row[field] == old[field], ('Baseline must match exactly', run, field, row[field], old[field])
                rows.append(row)

    # Keep labels out of public manifests and image filenames. Retain mappings
    # for reproducible reruns, separately from each run's blinded materials.
    mapping_path = OUT / 'blind-mapping.json'
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text())
    else:
        mapping = {}
        for run in [1, 2]:
            methods = METHODS.copy()
            secrets.SystemRandom().shuffle(methods)
            mapping[f'run-{run}'] = [{'file': secrets.token_hex(6) + '.png', 'method': method} for method in methods]
        save_json(mapping_path, mapping)
    mapping_path.chmod(0o600)
    copy_hashes = {}
    for run in [1, 2]:
        entries = mapping[f'run-{run}']
        assert sorted(e['method'] for e in entries) == sorted(METHODS)
        assert len({e['file'] for e in entries}) == 4
        assert all(Path(e['file']).name == e['file'] and e['file'].endswith('.png') and e['file'] != 'reference.png' for e in entries)
        run_dir = OUT / f'run-{run}'
        full = run_dir / 'blind-full'
        crops = run_dir / 'blind-crops'
        full.mkdir(parents=True, exist_ok=True)
        crops.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(reference_path, full / 'reference.png')
        assert sha(full / 'reference.png') == sha(reference_path)
        reference.crop(roi).save(crops / 'reference.png')
        for entry in entries:
            source = sources[(run, entry['method'])]
            shutil.copyfile(source, full / entry['file'])
            assert sha(full / entry['file']) == sha(source), 'Full copies must be byte-identical'
            candidates[(run, entry['method'])].crop(roi).save(crops / entry['file'])
        save_json(run_dir / 'blind-manifest.json', {
            'reference': str(full / 'reference.png'), 'reference_crop': str(crops / 'reference.png'),
            'candidates': [{'image': str(full / e['file']), 'crop': str(crops / e['file'])} for e in entries],
            'requirements': REQUIREMENTS,
            'instructions': 'Compare each randomized candidate with reference. Use full images for requirements and fixed face crops for facial changes. Do not inspect mappings, metrics, generation prompts or other ratings before evaluation.'})
        copy_hashes[f'run-{run}'] = {str(p.relative_to(run_dir)): sha(p) for folder in [full, crops] for p in sorted(folder.glob('*.png'))}
    save_json(OUT / 'metrics.json', {'config_sha256': CONFIG_SHA256, 'reference_sha256': sha(reference_path),
                                    'thresholds': thresholds, 'baseline_exact_match': True, 'results': rows})
    save_json(OUT / 'provenance.json', {
        'python': platform.python_version(), 'platform': platform.platform(),
        'dependencies': {name: importlib.metadata.version(name) for name in ['torch', 'torchvision', 'lpips', 'numpy', 'Pillow', 'scikit-image', 'scipy']},
        'config_sha256': CONFIG_SHA256, 'script_sha256': sha(__file__), 'prompts_sha256': sha(prompts_path),
        'sequential_metrics_sha256': sha(prior_path),
        'algorithm_reference': 'experiments/ten-stage-p03-v1/metrics/compute.py',
        'algorithm_reference_sha256': sha(EXP / 'metrics/compute.py'),
        'weights': [{'path': str(p), 'sha256': sha(p)} for p in [backbone, linear]],
        'blind_mapping_sha256': sha(mapping_path), 'blinded_image_sha256': copy_hashes})
    print(json.dumps({'baseline_exact_match': True, 'results': rows}, indent=2))


if __name__ == '__main__':
    main()
