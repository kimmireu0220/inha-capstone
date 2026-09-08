"""Run once all 20 outputs exist, from repository root:
.venv-metrics/bin/python experiments/ten-stage-p03-v1/metrics/compute.py

Analytical crops only. ROI fixed after viewing only the P03 original.
Exact MAE/SSIM/LPIPS algorithms from ten-stage-p02-v1/metrics/compute.py.
Cached pretrained weights required. No ratings read or thresholds fitted.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import secrets

import numpy as np
from PIL import Image
import torch
import lpips
from skimage.metrics import structural_similarity

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
EXP = OUT.parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def tensor(a):
    return torch.from_numpy(a.transpose(2, 0, 1).copy()).unsqueeze(0) * 2 - 1


def main():
    config_path = OUT / 'config.json'
    config = json.loads(config_path.read_text())
    roi = tuple(config['roi_xyxy'])
    assert roi == (352, 64, 672, 424), 'Preregistered ROI must remain fixed'
    assert config['crop_size_wh'] == [320, 360]
    assert config['reference'] == 'assets/people/P03.png'
    assert config['runs'] == [1, 2]
    assert config['steps'] == list(range(1, 11))
    thresholds = {'mae_0_1_gte': 0.0288375, 'ssim_lte': 0.842874, 'lpips_alex_v0_1_gte': 0.0555075}
    assert config['thresholds'] == thresholds, 'Transferred thresholds must remain fixed'
    reference_path = ROOT / config['reference']
    keys = [(run, step) for run in [1, 2] for step in range(1, 11)]
    sources = {(run, step): EXP / f'run-{run}/step-{step}.png' for run, step in keys}
    missing = [str(p) for p in sources.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError('All twenty outputs required: ' + ', '.join(missing))
    backbone = Path(torch.hub.get_dir()) / 'checkpoints/alexnet-owt-7be5be79.pth'
    linear = Path(lpips.__file__).parent / 'weights/v0.1/alex.pth'
    assert backbone.is_file() and linear.is_file(), 'Cached pretrained weights required'
    torch.set_num_threads(2)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    reference = Image.open(reference_path).convert('RGB')
    assert reference.size == (1024, 1536)
    candidates = {}
    for key, source in sources.items():
        candidate = Image.open(source).convert('RGB')
        assert candidate.size == reference.size, (source, candidate.size)
        candidates[key] = candidate

    crops = OUT / 'blind-crops'
    crops.mkdir(exist_ok=True)
    mapping_path = OUT / 'blind-mapping.json'
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text())
    else:
        shuffled = keys.copy()
        secrets.SystemRandom().shuffle(shuffled)
        mapping = {'presentation_order': [
            {'file': f'{secrets.token_hex(6)}.png', 'run': run, 'step': step}
            for run, step in shuffled
        ]}
        save_json(mapping_path, mapping)
    entries = mapping['presentation_order']
    assert sorted((e['run'], e['step']) for e in entries) == keys
    assert len({e['file'] for e in entries}) == 20
    assert all(Path(e['file']).name == e['file'] and e['file'].endswith('.png') and e['file'] != 'reference.png' for e in entries)
    reference.crop(roi).save(crops / 'reference.png')
    ref = np.asarray(reference.crop(roi), dtype=np.float32) / 255.0
    for entry in entries:
        candidates[(entry['run'], entry['step'])].crop(roi).save(crops / entry['file'])
    save_json(OUT / 'blind-manifest.json', {
        'reference': str(crops / 'reference.png'),
        'candidates': [str(crops / e['file']) for e in entries],
        'instructions': 'Compare each crop with reference. Opaque randomized order. Do not read mapping or metrics before evaluation.',
    })

    network = lpips.LPIPS(net='alex', version='0.1', model_path=str(linear), verbose=False).cpu().eval()
    rows = []
    with torch.no_grad():
        ref_t = tensor(ref)
        for run, step in keys:
            source = sources[(run, step)]
            arr = np.asarray(candidates[(run, step)].crop(roi), dtype=np.float32) / 255.0
            mae = float(np.mean(np.abs(arr - ref)))
            ssim = float(structural_similarity(ref, arr, channel_axis=2, data_range=1.0, win_size=7, gaussian_weights=False, use_sample_covariance=True))
            perceptual = float(network(ref_t, tensor(arr)).item())
            rows.append({'run': run, 'step': step, 'source_sha256': sha(source),
                         'mae_0_1': mae, 'mae_0_255': mae * 255,
                         'ssim': ssim, 'lpips_alex_v0_1': perceptual,
                         'alarms': {'mae': mae >= thresholds['mae_0_1_gte'],
                                    'ssim': ssim <= thresholds['ssim_lte'],
                                    'lpips': perceptual >= thresholds['lpips_alex_v0_1_gte']}})
    dependencies = {name: importlib.metadata.version(name) for name in ['torch', 'torchvision', 'lpips', 'numpy', 'Pillow', 'scikit-image', 'scipy']}
    first_alarms = {f'run-{run}': {metric: next((r['step'] for r in rows if r['run'] == run and r['alarms'][metric]), None)
                                  for metric in ['mae', 'ssim', 'lpips']} for run in [1, 2]}
    save_json(OUT / 'metrics.json', {'config_sha256': sha(config_path), 'reference_sha256': sha(reference_path),
                                    'thresholds': thresholds, 'first_alarm_steps': first_alarms, 'results': rows})
    save_json(OUT / 'provenance.json', {
        'python': platform.python_version(), 'platform': platform.platform(), 'dependencies': dependencies,
        'config_sha256': sha(config_path), 'script_sha256': sha(__file__),
        'algorithm_reference': 'experiments/ten-stage-p02-v1/metrics/compute.py',
        'algorithm_reference_sha256': sha(ROOT / 'experiments/ten-stage-p02-v1/metrics/compute.py'),
        'weights': [{'path': str(p), 'sha256': sha(p)} for p in [backbone, linear]],
        'crop_sha256': {p.name: sha(p) for p in sorted(crops.glob('*.png'))},
        'blind_mapping_sha256': sha(mapping_path),
    })
    print(json.dumps({'first_alarm_steps': first_alarms, 'results': rows}, indent=2))


if __name__ == '__main__':
    main()
