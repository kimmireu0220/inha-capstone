"""Run from repo root: .venv-metrics/bin/python experiments/ten-stage-v1/metrics/compute.py

Analytical crops only. ROI chosen by viewing original before any candidate.
Existing cached pretrained weights required; no network or detector used.
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
ROI = (340, 120, 660, 480)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def tensor(a):
    return torch.from_numpy(a.transpose(2, 0, 1).copy()).unsqueeze(0) * 2 - 1


def main():
    torch.set_num_threads(2)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    crops = OUT / 'blind-crops'
    crops.mkdir(exist_ok=True)
    mapping_path = OUT / 'blind-mapping.json'
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text())
    else:
        steps = list(range(1, 11))
        secrets.SystemRandom().shuffle(steps)
        mapping = {'presentation_order': [
            {'file': f'{secrets.token_hex(6)}.png', 'step': step} for step in steps
        ]}
        save_json(mapping_path, mapping)

    reference_path = ROOT / 'assets/people/P01.png'
    reference = Image.open(reference_path).convert('RGB')
    assert reference.size == (1024, 1536)
    reference.crop(ROI).save(crops / 'reference.png')
    ref = np.asarray(reference.crop(ROI), dtype=np.float32) / 255.0
    for entry in mapping['presentation_order']:
        source = EXP / f"step-{entry['step']}.png"
        candidate = Image.open(source).convert('RGB')
        assert candidate.size == reference.size, (source, candidate.size)
        candidate.crop(ROI).save(crops / entry['file'])
    save_json(OUT / 'blind-manifest.json', {
        'reference': str(crops / 'reference.png'),
        'candidates': [str(crops / e['file']) for e in mapping['presentation_order']],
        'instructions': 'Compare each crop with reference. Opaque randomized order. Do not read mapping or metrics before evaluation.',
    })

    backbone = Path(torch.hub.get_dir()) / 'checkpoints/alexnet-owt-7be5be79.pth'
    linear = Path(lpips.__file__).parent / 'weights/v0.1/alex.pth'
    assert backbone.is_file() and linear.is_file(), 'Cached pretrained weights required'
    network = lpips.LPIPS(net='alex', version='0.1', model_path=str(linear), verbose=False).cpu().eval()
    config = {
        'reference': str(reference_path.relative_to(ROOT)),
        'roi_xyxy': list(ROI), 'crop_size_wh': [320, 360],
        'roi_policy': 'Manually fixed using original before candidate inspection; Pillow exclusive right/bottom; identical coordinates for all images.',
        'image_processing': 'Decode Pillow RGB, crop only. No resizing, registration, adaptive alignment, color correction, or normalization beyond stated metric ranges.',
        'mae': 'Mean absolute error over RGB channels and pixels, float32 RGB [0,1]; also reported in [0,255] units.',
        'ssim': {'implementation': 'skimage.metrics.structural_similarity', 'channel_axis': 2, 'data_range': 1.0, 'win_size': 7, 'gaussian_weights': False, 'use_sample_covariance': True},
        'lpips': {'network': 'alex', 'version': '0.1', 'input_range': [-1, 1], 'spatial': False, 'device': 'cpu', 'eval': True},
        'limits': ['Descriptive image differences, not a validated detector or identity/surgery measure.', 'No threshold fitting and no use of human ratings.', 'Fixed crops can conflate pose, texture, lighting, and displacement with edited facial content.', 'Single reference and ten dependent outputs do not establish generalization.'],
    }
    save_json(OUT / 'config.json', config)
    rows = []
    with torch.no_grad():
        ref_t = tensor(ref)
        for step in range(1, 11):
            source = EXP / f'step-{step}.png'
            arr = np.asarray(Image.open(source).convert('RGB').crop(ROI), dtype=np.float32) / 255.0
            mae = float(np.mean(np.abs(arr - ref)))
            rows.append({'step': step, 'source_sha256': sha(source), 'mae_0_1': mae, 'mae_0_255': mae * 255,
                         'ssim': float(structural_similarity(ref, arr, channel_axis=2, data_range=1.0, win_size=7, gaussian_weights=False, use_sample_covariance=True)),
                         'lpips_alex_v0_1': float(network(ref_t, tensor(arr)).item())})
    dependencies = {name: importlib.metadata.version(name) for name in ['torch', 'torchvision', 'lpips', 'numpy', 'Pillow', 'scikit-image', 'scipy']}
    save_json(OUT / 'metrics.json', {'config_sha256': sha(OUT / 'config.json'), 'reference_sha256': sha(reference_path), 'results': rows})
    save_json(OUT / 'provenance.json', {
        'python': platform.python_version(), 'platform': platform.platform(), 'dependencies': dependencies,
        'config_sha256': sha(OUT / 'config.json'), 'script_sha256': sha(__file__),
        'weights': [{'path': str(p), 'sha256': sha(p)} for p in [backbone, linear]],
        'crop_sha256': {p.name: sha(p) for p in sorted(crops.glob('*.png'))},
        'blind_mapping_sha256': sha(mapping_path),
    })
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
