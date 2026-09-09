"""Check complete coverage, CSV joins, independent fixed MAE/SSIM and aggregation."""
import csv
import itertools
import json

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

from analyze import ROOT, REPO, M, local, save


def main():
    result = json.loads((ROOT/'results.json').read_text())
    plan = json.loads((ROOT/'plan.json').read_text())
    manifest = json.loads((ROOT/'manifest.json').read_text())
    assert result['complete'] and len(result['rows']) == 16
    jobs = {j['id']: j for j in plan['jobs']}
    assert set(jobs) == {r['id'] for r in result['rows']}
    assert {j['person'] for j in jobs.values()} == {'P05', 'P06'}
    assert {j['order'] for j in jobs.values()} == {'batch', 'SBP'}
    assert len({j['prompt'] for j in jobs.values() if j['stage']==(1 if j['order']=='batch' else 3)}) == 1
    for person in ('P05', 'P06'):
        for arm in ('batch', 'SBP'):
            assert result['summary'][person+':final:'+arm]['n_paths'] == 2
    for path, sha in manifest['files_sha256'].items():
        assert M.sha(REPO/path) == sha
    error = {'mae': 0., 'ssim': 0.}
    x0, y0, x1, y1 = next(iter(plan['people'].values()))['roi']

    def crop(path):
        with Image.open(path) as im:
            return np.array(im.convert('RGB'), dtype=np.float32)[y0:y1, x0:x1]/255

    rows = {r['id']: r for r in result['rows']}
    for row in rows.values():
        person = plan['people'][row['person']]
        x0, y0, x1, y1 = person['roi']
        job = jobs[row['id']]; new = crop(local(job['output']))
        for basis, old in [('original', crop(local(person['reference']))), ('previous', crop(local(job['input'])))]:
            observed = {'mae': float(np.mean(np.abs(new.astype(np.float64)-old))),
                        'ssim': float(structural_similarity(old, new, channel_axis=2, data_range=1.,
                                                           win_size=7, gaussian_weights=False, use_sample_covariance=True))}
            for k, v in observed.items():
                error[k] = max(error[k], abs(v-row[basis]['face']['fixed'][k]))
                assert error[k] < 1e-7
    with (ROOT/'metrics.csv').open() as f:
        flat = list(csv.DictReader(f))
    assert len(flat) == 16*2*4*5
    assert len({tuple(r[k] for k in ('id', 'basis', 'mode', 'scope', 'region')) for r in flat}) == len(flat)
    for r in flat:
        value = rows[r['id']][r['basis']][r['scope']][r['mode']]
        if r['scope'] == 'skin' and r['region'] != 'weighted_three_regions':
            value = value['regions'][r['region']]
        for k in M.FACE_KEYS if r['scope'] == 'face' else M.SKIN_KEYS:
            assert float(r[k]) == value[k]
    for group in result['summary'].values():
        for basis, scopes in group['metrics'].items():
            for scope, modes in scopes.items():
                for mode, metrics in modes.items():
                    for key, value in metrics.items():
                        values = [rows[k][basis][scope][mode][key] for k in group['ids']]
                        assert value['values'] == values
                        assert abs(value['mean']-sum(values)/len(values)) < 1e-12
    save(ROOT/'verification.json', {'passed': True, 'complete_outputs': 16,
                                    'independent_fixed_metric_pairs': 32, 'max_abs_error': error,
                                    'csv_rows_verified': len(flat), 'final_prompt_identical': True,
                                    'balanced_person_arm_repeat_cells': True, 'aggregation_verified': True,
                                    'results_sha256': M.sha(ROOT/'results.json'),
                                    'manifest_sha256': M.sha(ROOT/'manifest.json')})
    print((ROOT/'verification.json').read_text())


if __name__ == '__main__':
    main()
