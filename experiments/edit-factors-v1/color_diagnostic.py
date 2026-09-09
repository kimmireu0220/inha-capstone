"""Planned numerical decomposition; never writes modified image files."""
import json
from pathlib import Path

import numpy as np

from analyze import ROOT, M, local, save


def decompose(new, old):
    d = new.astype(np.float64) - old.astype(np.float64)
    bias = np.mean(d, axis=(0, 1), keepdims=True)
    residual = d - bias
    raw_mse = float(np.mean(d*d))
    bias_mse = float(np.mean(bias*bias))
    residual_mse = float(np.mean(residual*residual))
    assert abs(raw_mse-bias_mse-residual_mse) < 1e-12
    return {'raw_mae': float(np.abs(d).mean()), 'bias_abs_mean': float(np.abs(bias).mean()),
            'residual_mae': float(np.abs(residual).mean()), 'bias_rgb': bias.flatten().tolist(),
            'raw_mse': raw_mse, 'bias_mse': bias_mse, 'residual_mse': residual_mse,
            'pixel_count': int(d.shape[0]*d.shape[1])}


def main():
    result = json.loads((ROOT/'results.json').read_text())
    assert result['complete']
    plan = json.loads((ROOT/'plan.json').read_text())
    jobs = {j['id']: j for j in plan['jobs']}
    person = next(iter(plan['people'].values()))
    ref = M.image(local(person['reference']))
    M.REGIONS = person['skin_regions']
    control = M.crop(ref, M.REGIONS['forehead']).astype(np.float64)
    identity = decompose(control, control)
    offset = decompose(control + np.array([.03, -.02, .01]), control)
    assert identity['raw_mse'] == 0 and offset['residual_mse'] < 1e-24
    rows = []
    keys = ('raw_mae', 'bias_abs_mean', 'residual_mae', 'raw_mse', 'bias_mse', 'residual_mse')
    for row in result['rows']:
        person = plan['people'][row['person']]
        ref = M.image(local(person['reference'])); M.REGIONS = person['skin_regions']
        job = jobs[row['id']]; a = M.image(local(job['output']))
        out = {k: row[k] for k in ('id', 'person', 'order', 'repeat', 'stage', 'added')}
        for basis, old in [('original', ref), ('previous', M.image(local(job['input'])))]:
            out[basis] = {}
            for mode in M.MODES:
                loc = (0, 0) if mode == 'fixed' else tuple(row[basis]['locations'][mode][k] for k in ('dx', 'dy'))
                regions = {name: decompose(M.crop(a, roi, loc), M.crop(old, roi)) for name, roi in M.REGIONS.items()}
                weighted = {k: float(np.average([v[k] for v in regions.values()],
                                                weights=[v['pixel_count'] for v in regions.values()])) for k in keys}
                weighted['bias_mse_fraction'] = weighted['bias_mse']/weighted['raw_mse'] if weighted['raw_mse'] else 0
                assert abs(weighted['raw_mae']-row[basis]['skin'][mode]['mae']) < 1e-7
                out[basis][mode] = {**weighted, 'regions': regions}
        rows.append(out)
    indexed = {r['id']: r for r in rows}
    groups = {}
    for name, group in result['summary'].items():
        chosen = [indexed[k] for k in group['ids']]
        groups[name] = {basis: {mode: {k: float(np.mean([r[basis][mode][k] for r in chosen])) for k in keys}
                                for mode in M.MODES} for basis in ('original', 'previous')}
        for basis in groups[name].values():
            for v in basis.values():
                v['bias_mse_fraction'] = v['bias_mse']/v['raw_mse'] if v['raw_mse'] else 0
    save(ROOT/'color-results.json', {'status': 'planned_secondary', 'rows': rows, 'summary': groups,
                                     'controls': {'identity': identity, 'constant_offset': offset},
                                     'source_results_sha256': M.sha(ROOT/'results.json'),
                                     'plan_sha256': M.sha(ROOT/'PROTOCOL.md'),
                                     'analysis_sha256': M.sha(Path(__file__)), 'checks_passed': True})
    print(json.dumps({k: v['original']['fixed'] for k, v in groups.items() if ':final:' in k}, ensure_ascii=False))


if __name__ == '__main__':
    main()
