"""Incremental fixed-ROI metrics. No human ratings or threshold fitting."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image
import torch
import lpips
from skimage.metrics import structural_similarity

ROOT = Path(__file__).resolve().parent
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
config = json.loads((ROOT / 'config.json').read_text())
assert config['thresholds'] == {'mae': .0288375, 'ssim': .842874, 'lpips': .0555075}
torch.set_num_threads(2)
torch.manual_seed(0)
torch.use_deterministic_algorithms(True)
backbone = Path(torch.hub.get_dir()) / 'checkpoints/alexnet-owt-7be5be79.pth'
linear = Path(lpips.__file__).parent / 'weights/v0.1/alex.pth'
assert backbone.exists() and linear.exists()
network = lpips.LPIPS(net='alex', version='0.1', model_path=str(linear), verbose=False).cpu().eval()
def tensor(a):
    return torch.from_numpy(a.transpose(2, 0, 1).copy()).unsqueeze(0) * 2 - 1
for person in sys.argv[1:] or config['roi_xyxy']:
    folder = ROOT / person
    roi = config['roi_xyxy'][person]
    assert roi[2] - roi[0] == 320 and roi[3] - roi[1] == 360
    reference = Image.open(folder / 'reference.png').convert('RGB')
    assert list(reference.size) == config['size']
    ref = np.asarray(reference.crop(roi), dtype=np.float32) / 255
    (folder / 'crops').mkdir(exist_ok=True)
    reference.crop(roi).save(folder / 'crops/reference.png')
    output = folder / 'metrics.json'
    existing = json.loads(output.read_text()) if output.exists() else {'results': []}
    prior = {r['file']: r for r in existing['results']}
    rows = []
    for name in [f'step-{i}.png' for i in range(1, 11)] + ['rebase.png']:
        path = folder / name
        if not path.exists():
            continue
        source_sha = sha(path)
        if name in prior:
            assert prior[name]['source_sha256'] == source_sha
            rows.append(prior[name])
            continue
        candidate = Image.open(path).convert('RGB')
        assert candidate.size == reference.size, (person, name, candidate.size)
        candidate.crop(roi).save(folder / 'crops' / name)
        arr = np.asarray(candidate.crop(roi), dtype=np.float32) / 255
        with torch.no_grad():
            values = {'mae': float(np.mean(np.abs(arr-ref))),
                      'ssim': float(structural_similarity(ref, arr, channel_axis=2, data_range=1., win_size=7, gaussian_weights=False, use_sample_covariance=True)),
                      'lpips': float(network(tensor(ref), tensor(arr)).item())}
        rows.append({'file': name, 'stage': int(name[5:-4]) if name.startswith('step-') else None,
                     **values, 'source_sha256': source_sha,
                     'measured_at': datetime.now(timezone.utc).isoformat(),
                     'alarms': {k: (v <= config['thresholds'][k] if k == 'ssim' else v >= config['thresholds'][k]) for k,v in values.items()}})
    sequential = [r for r in rows if r['stage'] is not None]
    assert [r['stage'] for r in sequential] == list(range(1, len(sequential)+1))
    first = {k: next((r['stage'] for r in sequential if r['alarms'][k]), None) for k in config['thresholds']}
    trigger = folder / 'trigger.json'
    if first['lpips'] is not None:
        record = {'stage': first['lpips'], 'primary': 'lpips', 'threshold': config['thresholds']['lpips'],
                  'recorded_at': datetime.now(timezone.utc).isoformat(), 'steps_available_at_detection': len(sequential),
                  'baseline_sha256': next(r['source_sha256'] for r in sequential if r['stage'] == first['lpips'])}
        if trigger.exists():
            previous = json.loads(trigger.read_text())
            assert previous['stage'] == record['stage'] and previous['baseline_sha256'] == record['baseline_sha256']
        else:
            assert record['steps_available_at_detection'] == record['stage'], 'Not incremental first detection'
            save(trigger, record)
    save(output, {'person': person, 'roi_xyxy': roi, 'config_sha256': sha(ROOT/'config.json'),
                  'reference_sha256': sha(folder/'reference.png'), 'script_sha256': sha(__file__),
                  'weight_sha256': {'backbone': sha(backbone), 'linear': sha(linear)},
                  'first_alarm_steps': first, 'results': rows})
    print(json.dumps({'person': person, 'sequential_count': len(sequential), 'first_alarms': first, 'rebase': any(r['file']=='rebase.png' for r in rows)}))
