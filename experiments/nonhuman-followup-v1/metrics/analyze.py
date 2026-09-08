"""Current-output, label-free registration and ROI sensitivity diagnostics.

No import or writes to historical experiment runners. Metric formulas are copied
from their pure calculations and checked against current curves for equivalence.
"""
import csv
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import lpips
import numpy as np
import scipy
import skimage
import torch
from PIL import Image
from scipy.ndimage import gaussian_filter
from skimage.color import rgb2gray
from skimage.feature import match_template
from skimage.metrics import structural_similarity

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
CURRENT = REPO / 'experiments/revised-tail-v1'
SIGMAS = (1, 3, 6)
RADIUS = 64
REGIONS = {'forehead': [452, 144, 568, 178],
           'cheek_viewer_left': [412, 264, 448, 306],
           'cheek_viewer_right': [572, 264, 604, 306]}
FACE_KEYS = ('mae', 'ssim', 'lpips')
SKIN_KEYS = ('mae', 'ssim', 'highpass_mae')
MODES = ('fixed', '1', '3', '6')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    path = ROOT / name
    assert path.parent == ROOT
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def image(path):
    with Image.open(path) as im:
        assert im.size == (1024, 1536), (path, im.size)
        return np.asarray(im.convert('RGB'), dtype=np.float32) / 255


def crop(a, roi, shift=(0, 0)):
    x0, y0, x1, y1 = roi
    dx, dy = shift
    assert 0 <= x0 + dx < x1 + dx <= a.shape[1]
    assert 0 <= y0 + dy < y1 + dy <= a.shape[0]
    return a[y0 + dy:y1 + dy, x0 + dx:x1 + dx]


def ssim(a, b):
    return float(structural_similarity(a, b, channel_axis=2, data_range=1.,
                 win_size=7, gaussian_weights=False, use_sample_covariance=True))


def tensor(a):
    return torch.from_numpy(a.transpose(2, 0, 1).copy()).unsqueeze(0) * 2 - 1


def face(a, b, network):
    with torch.no_grad():
        value = float(network(tensor(a), tensor(b)).item())
    return {'mae': float(np.mean(np.abs(a - b))), 'ssim': ssim(a, b), 'lpips': value}


def locate(a, ref, roi, sigma):
    x0, y0, x1, y1 = roi
    assert x0 >= RADIUS and y0 >= RADIUS
    assert x1 + RADIUS <= a.shape[1] and y1 + RADIUS <= a.shape[0]
    template = gaussian_filter(rgb2gray(ref), sigma)[y0:y1, x0:x1]
    gray = gaussian_filter(rgb2gray(a), sigma)
    scores = match_template(gray[y0-RADIUS:y1+RADIUS, x0-RADIUS:x1+RADIUS], template)
    assert scores.shape == (2 * RADIUS + 1, 2 * RADIUS + 1)
    iy, ix = np.unravel_index(np.argmax(scores), scores.shape)
    dx, dy = int(ix - RADIUS), int(iy - RADIUS)
    return {'dx': dx, 'dy': dy, 'ncc': float(scores[iy, ix]),
            'boundary': abs(dx) == RADIUS or abs(dy) == RADIUS}


def skin(a, ref, shift):
    gray, refgray = rgb2gray(a), rgb2gray(ref)
    hp = gray - gaussian_filter(gray, 2)
    refhp = refgray - gaussian_filter(refgray, 2)
    per = {}
    for name, roi in REGIONS.items():
        old, new = crop(ref, roi), crop(a, roi, shift)
        x0, y0, x1, y1 = roi
        per[name] = {'mae': float(np.mean(np.abs(old-new))), 'ssim': ssim(old, new),
                     'highpass_mae': float(np.mean(np.abs(crop(refhp, roi)-crop(hp, roi, shift)))),
                     'pixel_count': (x1-x0)*(y1-y0), 'ssim_valid_count': (x1-x0-6)*(y1-y0-6)}
    avg = {k: float(np.average([r[k] for r in per.values()],
            weights=[r['ssim_valid_count' if k == 'ssim' else 'pixel_count'] for r in per.values()]))
           for k in SKIN_KEYS}
    return dict(avg, regions=per)


def measure(a, ref, roi, network, with_skin):
    locations = {str(s): locate(a, ref, roi, s) for s in SIGMAS}
    shifts = {'fixed': (0, 0), **{s: (v['dx'], v['dy']) for s, v in locations.items()}}
    face_by_shift, skin_by_shift = {}, {}
    for shift in set(shifts.values()):
        face_by_shift[shift] = face(crop(ref, roi), crop(a, roi, shift), network)
        if with_skin:
            skin_by_shift[shift] = skin(a, ref, shift)
    spread = max(max(v[k] for v in locations.values())-min(v[k] for v in locations.values()) for k in ('dx', 'dy'))
    result = {'locations': locations, 'shift_spread_px': spread, 'setting_sensitive': spread > 3,
              'face': {s: face_by_shift[v] for s, v in shifts.items()}}
    if with_skin:
        result['skin'] = {s: skin_by_shift[v] for s, v in shifts.items()}
    return result


def catalog():
    inputs, progress, curves = [read(CURRENT / n) for n in ('inputs.json', 'progress.json', 'curves.json')]
    assert progress['complete']
    branches = {b['name']: b for b in inputs}
    progress_branches = {b['name']: b for b in progress['branches']}
    assert set(branches) == set(progress_branches)
    records, stage_ids = {}, {}

    def add(branch, path, role, expected_hash=None):
        b = branches[branch]
        digest = sha(path)
        if expected_hash:
            assert digest == expected_hash, path
        key = b['reference_sha256'] + ':' + digest
        value = records.setdefault(key, {'sha256': digest, 'reference_sha256': b['reference_sha256'],
                                        'reference': b['reference'], 'roi': b['roi'], 'paths': [], 'uses': []})
        assert value['roi'] == b['roi']
        if path not in value['paths']:
            value['paths'].append(path)
        if role not in value['uses']:
            value['uses'].append(role)
        return key

    for name, b in branches.items():
        assert sha(b['reference']) == b['reference_sha256']
        p = progress_branches[name]
        assert p['prefix_files'] == b['prefix_files'] and p['roi'] == b['roi']
        assert p['reference'] == b['reference'] and p['policy'] == b['policy']
        assert len(b['prefix_files']) == len(b['prefix_sha256']) == 8
        assert b['initial'] == b['prefix_files'][-1]
        assert [r['stage'] for r in p['rows']] == [9, 10]
        for stage, (path, digest) in enumerate(zip(b['prefix_files'], b['prefix_sha256']), 1):
            stage_ids[(name, stage)] = add(name, path, {'branch': name, 'stage': stage, 'role': 'final'}, digest)
        previous = b['initial']
        for r in p['rows']:
            assert r['input'] == previous
            add(name, r['raw'], {'branch': name, 'stage': r['stage'], 'role': 'raw'})
            stage_ids[(name, r['stage'])] = add(name, r['final'], {'branch': name, 'stage': r['stage'], 'role': 'final'})
            previous = r['final']
    assert len(curves) == len(stage_ids) == 90
    assert len({(r['branch'], r['stage']) for r in curves}) == len(curves)
    for r in curves:
        key = stage_ids[(r['branch'], r['stage'])]
        assert records[key]['sha256'] == r['sha256'] == sha(r['path'])
        assert r['path'] in records[key]['paths']
        records[key].setdefault('recorded_fixed', []).append(r['metrics'])
    return branches, progress_branches, curves, records, stage_ids


def controls(ref, roi, network):
    cases = [('identity', ref, (0, 0)),
             ('translation_24_35', np.roll(ref, (35, 24), axis=(0, 1)), (24, 35)),
             ('translation_-31_-20', np.roll(ref, (-20, -31), axis=(0, 1)), (-31, -20))]
    cases += [(f'brightness_{offset:.2f}', np.clip(ref + offset, 0, 1), (0, 0)) for offset in (.03, .10)]
    outside = ref.copy()
    outside[:, :280] = [.2, .6, .9]
    outside[:, 744:] = [.8, .3, .1]
    cases.append(('distant_surround_replacement', outside, (0, 0)))
    support = np.zeros(ref.shape[:2], dtype=np.float32)
    for x0, y0, x1, y1 in REGIONS.values():
        support[y0-10:y1+10, x0-10:x1+10] = 1
    support = gaussian_filter(support, 2)
    yy, xx = np.indices(support.shape)
    wave = np.sin(xx * 2*np.pi/12) * np.sin(yy * 2*np.pi/17) * support
    cases += [(f'added_skin_wave_{amplitude:.2f}', np.clip(ref + amplitude*wave[:, :, None], 0, 1).astype(np.float32), None)
              for amplitude in (.01, .03, .06)]
    cases += [(f'blur_{s}', gaussian_filter(ref, (s, s, 0)), None) for s in (1, 2)]
    rows = []
    for name, a, known in cases:
        measured = measure(a, ref, roi, network, True)
        if known is not None:
            assert all((v['dx'], v['dy']) == known for v in measured['locations'].values()), name
        if name in ('identity', 'distant_surround_replacement') or name.startswith('translation_'):
            for s in ('1', '3', '6'):
                assert measured['face'][s]['mae'] == 0 and measured['face'][s]['ssim'] == 1
                assert abs(measured['face'][s]['lpips']) < 1e-7
                assert measured['skin'][s]['mae'] == 0 and measured['skin'][s]['ssim'] == 1
                assert measured['skin'][s]['highpass_mae'] < 1e-7
        if name.startswith('brightness_'):
            assert all(measured['face'][s]['mae'] > .02 and measured['skin'][s]['mae'] > .02 for s in ('1', '3', '6'))
        rows.append(dict(name=name, expected_translation=known, **measured))
    for s in ('1', '3', '6'):
        wave_values = [v['skin'][s]['highpass_mae'] for v in rows if v['name'].startswith('added_skin_wave_')]
        assert wave_values[0] < wave_values[1] < wave_values[2]
    return rows


def summarize(branches, records, stage_ids):
    summary = {}
    for name, branch in branches.items():
        rows = [records[stage_ids[(name, s)]] for s in range(1, 11)]
        summary[name] = {'policy': branch['policy'], 'stages': 10}
        for scope, keys in [('face', FACE_KEYS), ('skin', SKIN_KEYS)]:
            if scope not in rows[0]:
                continue
            summary[name][scope] = {m: {
                'mean': {k: float(np.mean([r[scope][m][k] for r in rows])) for k in keys},
                'final': {k: rows[-1][scope][m][k] for k in keys}} for m in MODES}
            if scope == 'skin':
                summary[name]['skin_regions'] = {region: {m: {
                    'mean': {k: float(np.mean([r[scope][m]['regions'][region][k] for r in rows])) for k in keys},
                    'final': {k: rows[-1][scope][m]['regions'][region][k] for k in keys}}
                    for m in MODES} for region in REGIONS}
    rankings = []
    p04 = ['P04', 'P04-fixed3', 'P04-triggered']
    scopes = [('face', FACE_KEYS), ('skin', SKIN_KEYS)] + [(name, SKIN_KEYS) for name in REGIONS]
    for scope, keys in scopes:
        for mode in MODES:
            for endpoint in ('mean', 'final'):
                for k in keys:
                    scores = {b: (summary[b][scope] if scope in ('face', 'skin') else summary[b]['skin_regions'][scope])[mode][endpoint][k] for b in p04}
                    order = sorted(scores, key=lambda b: (-scores[b] if k == 'ssim' else scores[b], b))
                    rankings.append({'scope': scope, 'mode': mode, 'endpoint': endpoint, 'metric': k,
                                     'order_best_first': order, 'values': scores})
    return summary, rankings


def main():
    torch.set_num_threads(2)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    branches, progress, curves, records, stage_ids = catalog()
    sources = [CURRENT/n for n in ('inputs.json', 'progress.json', 'curves.json')]
    sources += [ROOT/'PROTOCOL.md', Path(__file__),
                REPO/'experiments/policy-pilot-v1/run.py',
                REPO/'experiments/policy-pilot-v1/alignment-diagnostic/analyze.py',
                REPO/'experiments/policy-pilot-v1/skin-diagnostic/analyze.py',
                REPO/'experiments/policy-pilot-v1/skin-diagnostic/PROTOCOL.md']
    source_hashes = {str(p): sha(p) for p in sources}
    image_hashes = {b['reference']: b['reference_sha256'] for b in branches.values()}
    image_hashes.update({path: r['sha256'] for r in records.values() for path in r['paths']})
    manifest = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
                'current_catalog_only': [str(p) for p in sources[:3]], 'source_hashes': source_hashes,
                'image_hashes': image_hashes, 'unique_outputs': len(records), 'unique_final_outputs': len({r['sha256'] for r in curves}),
                'stage_records': len(curves), 'branches': list(branches), 'regions': REGIONS,
                'settings': {'sigmas': list(SIGMAS), 'primary_sigma': 3, 'radius': RADIUS, 'skin_highpass_sigma': 2},
                'versions': {m: importlib.metadata.version(m) for m in ('numpy', 'scipy', 'scikit-image', 'torch', 'torchvision', 'lpips', 'Pillow')},
                'python': platform.python_version(), 'platform': platform.platform(),
                'human_evaluation': 'not_collected', 'independent_agent_evaluation': 'not_collected'}
    save('manifest.json', manifest)
    network = lpips.LPIPS(net='alex', version='0.1', verbose=False).cpu().eval()
    state_hash = hashlib.sha256()
    for name, value in sorted(network.state_dict().items()):
        state_hash.update(name.encode())
        state_hash.update(str(tuple(value.shape)).encode())
        state_hash.update(value.cpu().numpy().tobytes())
    manifest['lpips_state_dict_sha256'] = state_hash.hexdigest()
    manifest['lpips_weights_file'] = str(Path(lpips.__file__).parent/'weights/v0.1/alex.pth')
    manifest['lpips_weights_file_sha256'] = sha(manifest['lpips_weights_file'])
    save('manifest.json', manifest)
    refs = {b['reference_sha256']: image(b['reference']) for b in branches.values()}
    maximum_metric_error = {k: 0. for k in FACE_KEYS}
    for n, (key, row) in enumerate(records.items(), 1):
        measured = measure(image(row['paths'][0]), refs[row['reference_sha256']], row['roi'], network,
                           any(use['branch'].startswith('P04') for use in row['uses']))
        row.update(measured)
        for expected in row.get('recorded_fixed', []):
            for k in FACE_KEYS:
                error = abs(expected[k]-row['face']['fixed'][k])
                maximum_metric_error[k] = max(maximum_metric_error[k], error)
                assert error < 1e-6, (row['paths'][0], k, expected[k], row['face']['fixed'][k])
        print(f'[{n}/{len(records)}] {row["uses"][0]} shift3={row["locations"]["3"]} fixed_lpips={row["face"]["fixed"]["lpips"]:.6f}', flush=True)
    p04 = branches['P04']
    control_rows = controls(refs[p04['reference_sha256']], p04['roi'], network)
    summary, rankings = summarize(branches, records, stage_ids)
    interventions = []
    for name, b in progress.items():
        for row in b['rows']:
            if not row['rebased']:
                continue
            raw_key, final_key = [branches[name]['reference_sha256'] + ':' + sha(row[k]) for k in ('raw', 'final')]
            before, after = records[raw_key], records[final_key]
            interventions.append({'branch': name, 'stage': row['stage'], 'raw_id': raw_key, 'final_id': final_key,
                'face_raw_minus_final': {mode: {k: before['face'][mode][k]-after['face'][mode][k] for k in FACE_KEYS} for mode in MODES},
                'skin_raw_minus_final': {mode: {k: before['skin'][mode][k]-after['skin'][mode][k] for k in SKIN_KEYS} for mode in MODES}})
    for path, digest in {**source_hashes, **image_hashes}.items():
        assert sha(path) == digest, path
    result = {'manifest_sha256': sha(ROOT/'manifest.json'), 'rows': records,
              'stage_ids': [{'branch': b, 'stage': s, 'id': key} for (b, s), key in stage_ids.items()],
              'summary': summary, 'p04_rankings': rankings, 'tail_interventions': interventions,
              'controls': control_rows, 'fixed_reproduction_max_abs_error': maximum_metric_error,
              'unique_outputs': len(records), 'unique_p04_outputs': sum('skin' in r for r in records.values()),
              'boundary_hits': {str(s): sum(r['locations'][str(s)]['boundary'] for r in records.values()) for s in SIGMAS},
              'setting_sensitive_count': sum(r['setting_sensitive'] for r in records.values()),
              'max_shift_spread_px': max(r['shift_spread_px'] for r in records.values()),
              'diagnostic_only': True, 'tests_passed': True,
              'human_evaluation': 'not_collected', 'independent_agent_evaluation': 'not_collected'}
    save('results.json', result)
    with (ROOT/'curves.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['branch', 'stage', 'sha256', 'scope', 'region', 'mode', 'dx', 'dy', 'ncc', 'mae', 'ssim', 'lpips', 'highpass_mae'])
        writer.writeheader()
        for (branch, stage), key in stage_ids.items():
            row = records[key]
            for mode in MODES:
                location = {'dx': 0, 'dy': 0, 'ncc': ''} if mode == 'fixed' else row['locations'][mode]
                base = {'branch': branch, 'stage': stage, 'sha256': row['sha256'], 'mode': mode, **{k: location[k] for k in ('dx', 'dy', 'ncc')}}
                writer.writerow(dict(base, scope='face', region='whole_roi', **row['face'][mode]))
                if 'skin' in row:
                    writer.writerow(dict(base, scope='skin', region='weighted_three_regions', **{k: row['skin'][mode][k] for k in SKIN_KEYS}))
                    for region, values in row['skin'][mode]['regions'].items():
                        writer.writerow(dict(base, scope='skin', region=region, **{k: values[k] for k in SKIN_KEYS}))
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'stage_ids', 'controls', 'p04_rankings')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
