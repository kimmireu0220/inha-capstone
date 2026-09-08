"""Reuse the preregistered ten-stage metric configuration without tuning.
Run from repository root with .venv-metrics/bin/python and this script path.
"""
from pathlib import Path
import importlib.util
import json
import secrets
import shutil
import platform
import importlib.metadata
import numpy as np
from PIL import Image
import torch
import lpips
from skimage.metrics import structural_similarity

OUT = Path(__file__).resolve().parent
EXP = OUT.parents[1]
ROOT = EXP.parents[1]
spec = importlib.util.spec_from_file_location('prior_metrics', EXP / 'metrics/compute.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
sha, save_json, tensor = prior.sha, prior.save_json, prior.tensor


def main():
    sources = {'repair': OUT.parent / 'repair.png', 'rollback': OUT.parent / 'rollback.png',
               'rebase': OUT.parent / 'rebase.png', 'step-3-baseline': EXP / 'step-3.png'}
    original = ROOT / 'assets/people/P01.png'
    blind = OUT / 'blind-full-images'
    blind.mkdir(exist_ok=True)
    mapping_path = OUT / 'blind-mapping.json'
    if mapping_path.exists():
        mapping = json.loads(mapping_path.read_text())
    else:
        names = list(sources)
        secrets.SystemRandom().shuffle(names)
        mapping = {'presentation_order': [{'file': secrets.token_hex(6) + '.png', 'candidate': name} for name in names]}
        save_json(mapping_path, mapping)
    shutil.copyfile(original, blind / 'reference.png')
    for entry in mapping['presentation_order']:
        shutil.copyfile(sources[entry['candidate']], blind / entry['file'])
    save_json(OUT / 'blind-manifest.json', {
        'reference': str(blind / 'reference.png'),
        'candidates': [str(blind / entry['file']) for entry in mapping['presentation_order']],
        'instructions': 'Full-image byte copies in randomized opaque order. Compare with original reference. Do not read mapping or metrics until independent evaluation is recorded.',
    })
    print('MANIFEST: ' + str(OUT / 'blind-manifest.json'), flush=True)
    config_path = EXP / 'metrics/config.json'
    shutil.copyfile(config_path, OUT / 'config.json')
    config = json.loads(config_path.read_text())
    roi = tuple(config['roi_xyxy'])
    reference = Image.open(original).convert('RGB')
    ref = np.asarray(reference.crop(roi), dtype=np.float32) / 255.0
    torch.set_num_threads(2)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    backbone = Path(torch.hub.get_dir()) / 'checkpoints/alexnet-owt-7be5be79.pth'
    linear = Path(lpips.__file__).parent / 'weights/v0.1/alex.pth'
    assert backbone.is_file() and linear.is_file()
    network = lpips.LPIPS(net='alex', version='0.1', model_path=str(linear), verbose=False).cpu().eval()
    rows = []
    with torch.no_grad():
        ref_t = tensor(ref)
        for name, source in sources.items():
            img = Image.open(source).convert('RGB')
            assert img.size == reference.size == (1024, 1536)
            arr = np.asarray(img.crop(roi), dtype=np.float32) / 255.0
            mae = float(np.mean(np.abs(arr-ref)))
            rows.append({'candidate': name, 'source': str(source.relative_to(ROOT)), 'source_sha256': sha(source),
                'mae_0_1': mae, 'mae_0_255': mae*255,
                'ssim': float(structural_similarity(ref, arr, channel_axis=2, data_range=1.0, win_size=7, gaussian_weights=False, use_sample_covariance=True)),
                'lpips_alex_v0_1': float(network(ref_t, tensor(arr)).item())})
    save_json(OUT / 'metrics.json', {'config_sha256': sha(OUT / 'config.json'), 'reference_sha256': sha(original), 'results': rows})
    save_json(OUT / 'provenance.json', {
        'python': platform.python_version(), 'platform': platform.platform(),
        'dependencies': {n: importlib.metadata.version(n) for n in ['torch', 'torchvision', 'lpips', 'numpy', 'Pillow', 'scikit-image', 'scipy']},
        'config_sha256': sha(OUT / 'config.json'), 'original_config_sha256': sha(config_path),
        'script_sha256': sha(__file__), 'imported_script_sha256': sha(EXP / 'metrics/compute.py'),
        'weights': [{'path': str(p), 'sha256': sha(p)} for p in [backbone, linear]],
        'blind_files_sha256': {p.name: sha(p) for p in sorted(blind.glob('*.png'))},
        'blind_mapping_sha256': sha(mapping_path),
        'limitations': config['limits'],
    })
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
