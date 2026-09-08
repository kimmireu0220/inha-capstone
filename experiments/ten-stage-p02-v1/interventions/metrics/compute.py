"""Compute fixed original-relative P02 face metrics and full-image blind review copies.
Run from repo root with .venv-metrics/bin/python and this script path.
No human/agent ratings read; baseline equality is verified against saved metrics.
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
EXP = OUT.parent.parent
ROOT = EXP.parents[1]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save_json(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def tensor(a):
    return torch.from_numpy(a.transpose(2, 0, 1).copy()).unsqueeze(0) * 2 - 1


def main():
    original_config = EXP / 'metrics/config.json'
    config = json.loads(original_config.read_text())
    roi = tuple(config['roi_xyxy'])
    assert roi == (352, 160, 672, 520)
    config['intervention_policy'] = 'Same preregistered P02 ROI and metric algorithms; no ratings read and no threshold fitting. Blind review uses byte-identical full image copies, not metric crops.'
    config['original_config_sha256'] = sha(original_config)
    save_json(OUT / 'config.json', config)
    ref_path = ROOT / config['reference']
    sources = {'baseline_step_2': EXP / 'step-2.png', **{name: OUT.parent / f'{name}.png' for name in ['repair', 'rollback', 'rebase']}}
    ref_image = Image.open(ref_path).convert('RGB')
    assert ref_image.size == (1024, 1536)
    images = {}
    for name, path in sources.items():
        images[name] = Image.open(path).convert('RGB')
        assert images[name].size == ref_image.size
    full = OUT / 'blind-full'
    full.mkdir(exist_ok=True)
    mapping_path = OUT / 'blind-mapping.json'
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text())
    else:
        names = list(sources)
        secrets.SystemRandom().shuffle(names)
        mapping = {'presentation_order': [{'file': f'{secrets.token_hex(6)}.png', 'candidate': name} for name in names]}
        save_json(mapping_path, mapping)
    assert sorted(e['candidate'] for e in mapping['presentation_order']) == sorted(sources)
    shutil.copyfile(ref_path, full / 'reference.png')
    for e in mapping['presentation_order']:
        assert Path(e['file']).name == e['file']
        shutil.copyfile(sources[e['candidate']], full / e['file'])
    save_json(OUT / 'blind-manifest.json', {
        'reference': str(full / 'reference.png'),
        'candidates': [str(full / e['file']) for e in mapping['presentation_order']],
        'instructions': 'Compare full images with reference in opaque randomized order. Do not read mapping, metrics, candidate names, or previous ratings before evaluation.',
    })
    torch.set_num_threads(2)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    backbone = Path(torch.hub.get_dir()) / 'checkpoints/alexnet-owt-7be5be79.pth'
    linear = Path(lpips.__file__).parent / 'weights/v0.1/alex.pth'
    assert backbone.is_file() and linear.is_file(), 'Cached pretrained weights required'
    network = lpips.LPIPS(net='alex', version='0.1', model_path=str(linear), verbose=False).cpu().eval()
    ref = np.asarray(ref_image.crop(roi), dtype=np.float32) / 255.0
    rows = []
    with torch.no_grad():
        ref_t = tensor(ref)
        for name, source in sources.items():
            arr = np.asarray(images[name].crop(roi), dtype=np.float32) / 255.0
            mae = float(np.mean(np.abs(arr - ref)))
            rows.append({'candidate': name, 'source_sha256': sha(source), 'mae_0_1': mae, 'mae_0_255': mae * 255,
                         'ssim': float(structural_similarity(ref, arr, channel_axis=2, data_range=1.0, win_size=7, gaussian_weights=False, use_sample_covariance=True)),
                         'lpips_alex_v0_1': float(network(ref_t, tensor(arr)).item())})
    prior_path = EXP / 'metrics/metrics.json'
    prior = next(row for row in json.loads(prior_path.read_text())['results'] if row['step'] == 2)
    keys = ['source_sha256', 'mae_0_1', 'mae_0_255', 'ssim', 'lpips_alex_v0_1']
    equality = {key: rows[0][key] == prior[key] for key in keys}
    assert all(equality.values()), equality
    save_json(OUT / 'results.json', {'config_sha256': sha(OUT / 'config.json'), 'reference_sha256': sha(ref_path), 'baseline_exact_match': equality, 'results': rows})
    save_json(OUT / 'provenance.json', {
        'python': platform.python_version(), 'platform': platform.platform(),
        'dependencies': {name: importlib.metadata.version(name) for name in ['torch', 'torchvision', 'lpips', 'numpy', 'Pillow', 'scikit-image', 'scipy']},
        'script_sha256': sha(__file__), 'config_sha256': sha(OUT / 'config.json'),
        'baseline_metrics_sha256': sha(prior_path),
        'weights': [{'path': str(p), 'sha256': sha(p)} for p in [backbone, linear]],
        'blind_full_sha256': {p.name: sha(p) for p in sorted(full.glob('*.png'))},
        'blind_mapping_sha256': sha(mapping_path),
    })
    print(json.dumps({'baseline_exact_match': equality, 'results': rows}, indent=2))


if __name__ == '__main__':
    main()
