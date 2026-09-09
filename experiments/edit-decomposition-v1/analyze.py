"""Analyze the 14 first outputs using frozen existing face metric functions.

No generation, human responses, or historical runner main functions are invoked.
Run from any directory with the repository's .venv-metrics/bin/python.
"""
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import lpips
import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE = REPO / 'experiments/nonhuman-followup-v1/metrics/analyze.py'
SPEC = importlib.util.spec_from_file_location('frozen_face_metrics', SOURCE)
METRIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(METRIC)
ARMS = ('batch', 'sequential', 'no_change')


def local(recorded):
    """Resolve recorded absolute provenance paths in the current checkout."""
    return REPO / ('experiments/' + recorded.split('/experiments/', 1)[1])


def save(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def pixel_sha(path):
    with Image.open(path) as im:
        assert im.size == (1024, 1536), (str(path), im.size)
        return hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()


def main():
    torch.set_num_threads(2)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    plan = json.loads((ROOT / 'plan.json').read_text())
    assert METRIC.sha(ROOT / 'PROTOCOL.md') == plan['protocol_sha256']
    assert METRIC.sha(local(plan['reference'])) == plan['reference_sha256']
    assert plan['roi'] == [352, 88, 672, 448]
    jobs = plan['jobs']
    assert len(jobs) == len({j['id'] for j in jobs}) == 14
    expected = {f'{arm}-r{rep}-s{stage}' for arm in ARMS for rep in (1, 2)
                for stage in range(1, (1 if arm == 'batch' else 3) + 1)}
    assert {j['id'] for j in jobs} == expected
    assert {p.stem for p in (ROOT / 'generated').glob('*.png')} == expected
    hashes = {str(p.relative_to(REPO)): METRIC.sha(p) for p in
              [SOURCE, Path(__file__), ROOT / 'plan.json', ROOT / 'PROTOCOL.md', local(plan['reference'])]}
    logs = {}
    duplicate_files, duplicate_pixels = defaultdict(list), defaultdict(list)
    for job in jobs:
        path = local(job['output'])
        log = json.loads(path.with_suffix('.call.json').read_text())
        assert all(log[k] == v for k, v in job.items())
        assert log['status'] == 'success' and log['attempt'] == 1
        assert METRIC.sha(path) == log['output_sha256']
        assert METRIC.sha(local(job['input'])) == log['input_sha256']
        previous = (plan['reference'] if job['stage'] == 1 else
                    next(j['output'] for j in jobs if j['id'] ==
                         f"{job['arm']}-r{job['repeat']}-s{job['stage'] - 1}"))
        assert job['input'] == previous, job['id']
        if job['stage'] > 1:
            prevlog = json.loads(local(previous).with_suffix('.call.json').read_text())
            assert prevlog['completed'] <= log['started']
        logs[job['id']] = log
        duplicate_files[log['output_sha256']].append(job['id'])
        duplicate_pixels[pixel_sha(path)].append(job['id'])
        for p in (path, path.with_suffix('.call.json')):
            hashes[str(p.relative_to(REPO))] = METRIC.sha(p)
    for rep in (1, 2):
        assert logs[f'batch-r{rep}-s1']['prompt'] == logs[f'sequential-r{rep}-s3']['prompt']

    network = lpips.LPIPS(net='alex', version='0.1', verbose=False).cpu().eval()
    state_hash = hashlib.sha256()
    for name, value in sorted(network.state_dict().items()):
        state_hash.update(name.encode())
        state_hash.update(str(tuple(value.shape)).encode())
        state_hash.update(value.cpu().numpy().tobytes())
    ref = METRIC.image(local(plan['reference']))
    roi = plan['roi']
    identity = METRIC.measure(ref, ref, roi, network, False)
    for mode in METRIC.MODES:
        assert identity['face'][mode]['mae'] == 0
        assert identity['face'][mode]['ssim'] == 1
        assert abs(identity['face'][mode]['lpips']) < 1e-7
    assert all((v['dx'], v['dy']) == (0, 0) for v in identity['locations'].values())
    rows = []
    for i, job in enumerate(jobs, 1):
        output = METRIC.image(local(job['output']))
        original = METRIC.measure(output, ref, roi, network, False)
        previous = original if job['stage'] == 1 else METRIC.measure(
            output, METRIC.image(local(job['input'])), roi, network, False)
        row = {k: job[k] for k in ('id', 'arm', 'repeat', 'stage')}
        row.update(output_sha256=logs[job['id']]['output_sha256'],
                   pixel_sha256=pixel_sha(local(job['output'])),
                   original=original, previous=previous)
        for basis in ('original', 'previous'):
            for mode in METRIC.MODES:
                v = row[basis]['face'][mode]
                assert all(np.isfinite(list(v.values())))
                assert 0 <= v['mae'] <= 1 and -1 <= v['ssim'] <= 1 and v['lpips'] >= -1e-7
        rows.append(row)
        print(f"[{i}/14] {job['id']}: {original['face']['fixed']}", flush=True)

    final = {}
    for arm in ARMS:
        selected = [r for r in rows if r['arm'] == arm and r['stage'] == (1 if arm == 'batch' else 3)]
        assert len(selected) == 2
        final[arm] = {'ids': [r['id'] for r in selected], 'calls_per_path': 1 if arm == 'batch' else 3,
                      'by_mode': {mode: {k: {'mean': float(np.mean(values)), 'min': min(values),
                                            'max': max(values), 'values': values}
                               for k in METRIC.FACE_KEYS
                               for values in [[r['original']['face'][mode][k] for r in selected]]}
                                  for mode in METRIC.MODES}}
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': hashes,
                'python': platform.python_version(), 'platform': platform.platform(),
                'packages': {k: importlib.metadata.version(k) for k in
                             ('numpy', 'Pillow', 'torch', 'torchvision', 'lpips', 'scipy', 'scikit-image', 'matplotlib')},
                'lpips_state_dict_sha256': state_hash.hexdigest(),
                'lpips_weights_file_sha256': METRIC.sha(Path(lpips.__file__).parent / 'weights/v0.1/alex.pth'),
                'roi': roi, 'device': 'cpu', 'metric_torch_seed': 0, 'threads': 2,
                'generation_tool': 'image_gen.imagegen', 'generation_model_version': 'not_exposed',
                'generation_seed': 'not_exposed', 'human_evaluation': 'not_collected',
                'independent_agent_evaluation': 'not_collected',
                'attempts': 14, 'successes': 14, 'failures': 0, 'quality_retries': 0,
                'execution_note': 'First single-image output of each requested call; no output selection.'}
    result = {'rows': rows, 'final': final, 'identity_control': identity,
              'unique_file_outputs': len(duplicate_files), 'unique_pixel_outputs': len(duplicate_pixels),
              'duplicate_file_groups': [v for v in duplicate_files.values() if len(v) > 1],
              'duplicate_pixel_groups': [v for v in duplicate_pixels.values() if len(v) > 1],
              'boundary_hits': {basis: sum(v['boundary'] for r in rows for v in r[basis]['locations'].values())
                                for basis in ('original', 'previous')},
              'max_shift_spread_px': {basis: max(r[basis]['shift_spread_px'] for r in rows)
                                      for basis in ('original', 'previous')},
              'checks_passed': True, 'interpretation': 'Descriptive pilot: one portrait, two paths per condition. No severity labels.'}
    for path, digest in hashes.items():
        assert METRIC.sha(REPO / path) == digest, path
    save('manifest.json', manifest)
    result['manifest_sha256'] = METRIC.sha(ROOT / 'manifest.json')
    save('results.json', result)
    with (ROOT / 'metrics.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'arm', 'repeat', 'stage', 'basis', 'mode',
                                              'dx', 'dy', 'ncc', 'mae', 'ssim', 'lpips'], lineterminator='\n')
        writer.writeheader()
        for r in rows:
            for basis in ('original', 'previous'):
                for mode in METRIC.MODES:
                    loc = {'dx': 0, 'dy': 0, 'ncc': ''} if mode == 'fixed' else r[basis]['locations'][mode]
                    writer.writerow({**{k: r[k] for k in ('id', 'arm', 'repeat', 'stage')},
                                     'basis': basis, 'mode': mode, **{k: loc[k] for k in ('dx', 'dy', 'ncc')},
                                     **r[basis]['face'][mode]})
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'identity_control')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
