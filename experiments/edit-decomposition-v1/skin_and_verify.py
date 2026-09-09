"""Post-hoc interior-ROI sensitivity check and independent result verification."""
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

from analyze import ARMS, METRIC, REPO, ROOT, local, save


def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    result = json.loads((ROOT / 'results.json').read_text())
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    assert METRIC.sha(ROOT / 'manifest.json') == result['manifest_sha256']
    for path, digest in manifest['source_sha256'].items():
        assert METRIC.sha(REPO / path) == digest
    prior = json.loads((REPO / 'experiments/nonhuman-followup-v1/metrics/manifest.json').read_text())
    assert manifest['lpips_state_dict_sha256'] == prior['lpips_state_dict_sha256']
    assert manifest['lpips_weights_file_sha256'] == prior['lpips_weights_file_sha256']
    jobs = {j['id']: j for j in plan['jobs']}
    ref = METRIC.image(local(plan['reference']))
    identity = METRIC.skin(ref, ref, (0, 0))
    assert identity['mae'] == identity['highpass_mae'] == 0 and identity['ssim'] == 1
    rows, error = [], {'mae': 0., 'ssim': 0.}
    x0, y0, x1, y1 = plan['roi']
    for row in result['rows']:
        job = jobs[row['id']]
        output = METRIC.image(local(job['output']))
        skins = {'fixed': METRIC.skin(output, ref, (0, 0))}
        for mode, loc in row['original']['locations'].items():
            skins[mode] = METRIC.skin(output, ref, (loc['dx'], loc['dy']))
        rows.append({**{k: row[k] for k in ('id', 'arm', 'repeat', 'stage')}, 'skin': skins})
        # Independent crop and formula path; both original and immediate-input bases.
        for basis, path in [('original', local(plan['reference'])), ('previous', local(job['input']))]:
            with Image.open(path) as im:
                old = np.array(im.convert('RGB'), dtype=np.float32)[y0:y1, x0:x1] / 255.
            with Image.open(local(job['output'])) as im:
                new = np.array(im.convert('RGB'), dtype=np.float32)[y0:y1, x0:x1] / 255.
            check = {'mae': float(np.abs(new.astype(np.float64) - old.astype(np.float64)).mean()),
                     'ssim': float(structural_similarity(old, new, channel_axis=2, data_range=1.,
                                                        win_size=7, gaussian_weights=False, use_sample_covariance=True))}
            for k in error:
                error[k] = max(error[k], abs(check[k] - row[basis]['face']['fixed'][k]))
                assert error[k] < 1e-7, (row['id'], basis, k)
    with (ROOT / 'metrics.csv').open() as f:
        flat = list(csv.DictReader(f))
    assert len(flat) == 14 * 2 * 4
    indexed = {r['id']: r for r in result['rows']}
    assert len({(r['id'], r['basis'], r['mode']) for r in flat}) == len(flat)
    for r in flat:
        for k in METRIC.FACE_KEYS:
            assert float(r[k]) == indexed[r['id']][r['basis']]['face'][r['mode']][k]
    final = {}
    for arm in ARMS:
        chosen = [r for r in rows if r['arm'] == arm and r['stage'] == (1 if arm == 'batch' else 3)]
        final[arm] = {mode: {k: {'mean': float(np.mean(v)), 'min': min(v), 'max': max(v), 'values': v}
                            for k in METRIC.SKIN_KEYS for v in [[r['skin'][mode][k] for r in chosen]]}
                      for mode in METRIC.MODES}
    save('skin-results.json', {'status': 'post_hoc_exploratory', 'regions': METRIC.REGIONS,
                              'rows': rows, 'final': final,
                              'analysis_sha256': METRIC.sha(Path(__file__)),
                              'plan_sha256': METRIC.sha(ROOT / 'POSTHOC_SKIN.md'),
                              'primary_results_sha256': METRIC.sha(ROOT / 'results.json')})
    with (ROOT / 'skin-metrics.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'arm', 'repeat', 'stage', 'mode', 'region',
                                              'mae', 'ssim', 'highpass_mae'], lineterminator='\n')
        writer.writeheader()
        for r in rows:
            for mode, v in r['skin'].items():
                for region, values in [('weighted_three_regions', v), *v['regions'].items()]:
                    writer.writerow({**{k: r[k] for k in ('id', 'arm', 'repeat', 'stage')},
                                     'mode': mode, 'region': region, **{k: values[k] for k in METRIC.SKIN_KEYS}})
    checks = {'passed': True, 'source_hashes_checked': len(manifest['source_sha256']),
              'primary_csv_rows_checked': len(flat), 'independently_recomputed_metric_pairs': 28,
              'fixed_max_absolute_error': error, 'same_lpips_weights_as_prior_analysis': True,
              'identity_control': {'mae': identity['mae'], 'ssim': identity['ssim'], 'highpass_mae': identity['highpass_mae']},
              'generation_chains_and_first_attempts_checked_by': 'analyze.py',
              'unique_decoded_outputs': result['unique_pixel_outputs']}
    save('verification.json', checks)
    print(json.dumps({'verification': checks, 'skin_final': {arm: v['fixed'] for arm, v in final.items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
