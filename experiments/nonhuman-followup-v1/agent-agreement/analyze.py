"""Frozen-threshold comparison with separate, blinded AI observations.

Reads completed reviewer files without editing, retraining, or adjudication.
"""
import csv
import hashlib
import importlib.metadata
import json
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
CURRENT = PARENT.parent/'revised-tail-v1'
THRESHOLDS = {'mae': .0288375, 'ssim': .842874, 'lpips': .0555075}
MODES = ('fixed', '1', '3', '6')
METRICS = ('mae', 'ssim', 'lpips')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def safe_ratio(n, d):
    return n/d if d else None


def valid_severity(value):
    return value is None or (type(value) is int and value in range(4))


def weighted_kappa(a, b, power=1):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        return {'value': None, 'reason': 'no_complete_pairs', 'n': 0}
    observed = np.zeros((4, 4), dtype=float)
    for x, y in pairs:
        observed[x, y] += 1
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0))/len(pairs)
    weights = (np.abs(np.arange(4)[:, None]-np.arange(4)[None, :])/3)**power
    numerator, denominator = float((weights*observed).sum()), float((weights*expected).sum())
    return {'value': 1-numerator/denominator if denominator > 0 else None,
            'reason': None if denominator > 0 else 'zero_expected_disagreement', 'n': len(pairs),
            'observed_weighted_disagreement_sum': numerator, 'expected_weighted_disagreement_sum': denominator}


def agreement(a, b):
    assert len(a) == len(b) and all(valid_severity(v) for v in [*a, *b])
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    counts = [[sum(x == i and y == j for x, y in pairs) for j in range(4)] for i in range(4)]
    binary = [[sum((x >= 2) == i and (y >= 2) == j for x, y in pairs) for j in range(2)] for i in range(2)]
    exact = sum(x == y for x, y in pairs)
    binary_equal = sum((x >= 2) == (y >= 2) for x, y in pairs)
    return {'n_total': len(a), 'n_complete': len(pairs), 'null_excluded': len(a)-len(pairs),
            'a_null': sum(x is None for x in a), 'b_null': sum(y is None for y in b),
            'ordinal_matrix_rows_a_columns_b': counts, 'ordinal_exact_count': exact,
            'ordinal_exact_agreement': safe_ratio(exact, len(pairs)),
            'linear_weighted_kappa': weighted_kappa(a, b, 1),
            'quadratic_weighted_kappa': weighted_kappa(a, b, 2),
            'binary_matrix_rows_a_columns_b': binary, 'binary_agreement_count': binary_equal,
            'binary_agreement': safe_ratio(binary_equal, len(pairs))}


def alarm(metric, value):
    return value <= THRESHOLDS[metric] if metric == 'ssim' else value >= THRESHOLDS[metric]


def confusion(predictions, severities):
    assert len(predictions) == len(severities)
    pairs = [(bool(p), s >= 2) for p, s in zip(predictions, severities) if s is not None]
    tp = sum(p and y for p, y in pairs)
    fp = sum(p and not y for p, y in pairs)
    tn = sum(not p and not y for p, y in pairs)
    fn = sum(not p and y for p, y in pairs)
    return {'n_total': len(severities), 'n_complete': len(pairs), 'null_excluded': len(severities)-len(pairs),
            'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn, 'ai_clear_count': tp+fn,
            'ai_not_clear_count': tn+fp, 'alarm_count': tp+fp,
            'precision': safe_ratio(tp, tp+fp), 'recall': safe_ratio(tp, tp+fn),
            'specificity': safe_ratio(tn, tn+fp), 'binary_agreement': safe_ratio(tp+tn, len(pairs))}


def spearman(x, y):
    assert len(x) == len(y)
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None and np.isfinite(a) and np.isfinite(b)]
    n = len(pairs)
    if n < 2:
        return {'rho': None, 'n_total': len(x), 'n_complete': n, 'null_excluded': len(x)-n, 'reason': 'fewer_than_two_pairs'}
    a, b = np.asarray(pairs, dtype=float).T
    a, b = rankdata(a), rankdata(b)
    a, b = a-a.mean(), b-b.mean()
    denominator = float(np.sqrt(np.dot(a, a)*np.dot(b, b)))
    return {'rho': float(np.dot(a, b)/denominator) if denominator else None,
            'n_total': len(x), 'n_complete': n, 'null_excluded': len(x)-n,
            'reason': None if denominator else 'zero_rank_variance'}


def compare_rows(rows):
    return {reviewer: {metric: confusion([alarm(metric, r['face']['fixed'][metric]) for r in rows],
                                        [r['ratings'][reviewer]['severity'] for r in rows])
                       for metric in METRICS} for reviewer in ('a', 'b')}


def correlate_rows(rows):
    out = {}
    for reviewer in ('a', 'b'):
        out[reviewer] = {}
        severity = [r['ratings'][reviewer]['severity'] for r in rows]
        for metric in METRICS:
            modes = {mode: spearman([1-r['face'][mode][metric] if metric == 'ssim' else r['face'][mode][metric] for r in rows], severity) for mode in MODES}
            out[reviewer][metric] = {'orientation': '1-ssim' if metric == 'ssim' else metric, 'modes': modes,
                 'delta_rho_sigma3_minus_fixed': (modes['3']['rho']-modes['fixed']['rho']) if modes['3']['rho'] is not None and modes['fixed']['rho'] is not None else None}
    return out


def main():
    key = read(PARENT/'private/face-key.json')
    public = read(PARENT/'blind-face/items.json')
    reviews = {r: read(PARENT/f'reviews/face-{r}.json') for r in ('a', 'b')}
    current_inputs = read(CURRENT/'inputs.json')
    current_progress = read(CURRENT/'progress.json')
    curves = read(CURRENT/'curves.json')
    metric_result = read(PARENT/'metrics/results.json')
    config = read(CURRENT.parent/'trigger-validation-v1/config.json')
    assert config['thresholds'] == THRESHOLDS
    sources = [Path(__file__), ROOT/'PROTOCOL.md', PARENT/'PROTOCOL.md', PARENT/'prepare_face.py',
               PARENT/'private/face-key.json', PARENT/'reviews/face-a.json', PARENT/'reviews/face-b.json',
               PARENT/'blind-face/items.json',
               PARENT/'metrics/results.json', PARENT/'metrics/manifest.json',
               CURRENT/'inputs.json', CURRENT/'progress.json', CURRENT/'curves.json',
               CURRENT.parent/'trigger-validation-v1/config.json']
    source_hashes = {str(p): sha(p) for p in sources}
    assert len(key) == len({r['id'] for r in key}) == 97
    ids = {r['id'] for r in key}
    public_paths = {r['id']: r['image'] for r in public}
    assert len(public) == len(public_paths) == 97 and set(public_paths) == ids
    indexed_reviews = {}
    for reviewer, doc in reviews.items():
        assert doc['human'] is False
        items = doc['items']
        assert len(items) == len({r['id'] for r in items}) == 97
        assert {r['id'] for r in items} == ids
        assert all(valid_severity(r['severity']) for r in items)
        assert all(r['same_person'] == 'not_assessed' for r in items)
        indexed_reviews[reviewer] = {r['id']: r for r in items}
    unique = [r for r in key if 'control' not in r and 'duplicate_of_source' not in r]
    controls = [r for r in key if r.get('control') == 'identity']
    repeats = [r for r in key if 'duplicate_of_source' in r]
    assert (len(unique), len(controls), len(repeats)) == (83, 6, 8)
    by_digest = {r['reference_sha256']+':'+r['output_sha256']: r for r in unique}
    assert len(by_digest) == 83
    branches = {b['name']: b for b in current_inputs}
    assert set(branches) == {b['name'] for b in current_progress['branches']}
    assert {(b['reference_sha256'], r['sha256']) for r in curves for b in [branches[r['branch']]]} == {
            (r['reference_sha256'], r['output_sha256']) for r in unique}
    assert len({r['reference_sha256'] for r in controls}) == 6
    image_hashes = {}
    for r in key:
        with Image.open(public_paths[r['id']]) as pair:
            assert pair.size == (660, 400)
            with Image.open(r['reference']) as ref:
                assert np.array_equal(np.asarray(pair.crop((0, 32, 320, 392))), np.asarray(ref.convert('RGB').crop(r['roi'])))
            with Image.open(r['path']) as out:
                assert np.array_equal(np.asarray(pair.crop((336, 32, 656, 392))), np.asarray(out.convert('RGB').crop(r['roi'])))
        image_hashes[public_paths[r['id']]] = sha(public_paths[r['id']])
        for p, digest in [(r['reference'], r['reference_sha256']), (r['path'], r['output_sha256'])]:
            assert sha(p) == digest
            image_hashes[p] = digest
        if r in controls:
            assert r['reference_sha256'] == r['output_sha256'] and r['sources'] == []
        else:
            wanted = sorted((c['branch'], c['stage']) for c in curves if c['sha256'] == r['output_sha256'] and branches[c['branch']]['reference_sha256'] == r['reference_sha256'])
            assert sorted((x['branch'], x['stage']) for x in r['sources']) == wanted
    manifest = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'source_hashes': source_hashes,
                'image_hashes': image_hashes, 'thresholds_frozen': THRESHOLDS, 'binary_ai_clear': 'severity >= 2',
                'versions': {k: importlib.metadata.version(k) for k in ('numpy', 'scipy', 'Pillow')},
                'rendered_pair_crop_bytes_match_sources': 97,
                'python': platform.python_version(), 'human_evaluation': 'not_collected',
                'reviewers': 'two independent sessions of the same base AI model',
                'null_policy': 'pairwise complete-case; every denominator retained', 'new_detector_training': False,
                'aligned_threshold_performance': 'not_computed', 'bootstrap_or_p_values': 'not_computed'}
    save('manifest.json', manifest)
    joined = []
    for row in unique:
        record = metric_result['rows'][row['reference_sha256']+':'+row['output_sha256']]
        assert record['roi'] == row['roi']
        joined.append({'id': row['id'], 'reference_sha256': row['reference_sha256'], 'output_sha256': row['output_sha256'],
                       'person': row['sources'][0]['branch'][:3], 'path': row['path'], 'sources': row['sources'],
                       'ratings': {r: indexed_reviews[r][row['id']] for r in ('a', 'b')}, 'face': record['face']})
    joined_by_id = {r['id']: r for r in joined}
    inter_rater = agreement([r['ratings']['a']['severity'] for r in joined], [r['ratings']['b']['severity'] for r in joined])
    inter_rater['disagreements'] = [{'id': r['id'], 'sources': r['sources'], 'a': r['ratings']['a']['severity'], 'b': r['ratings']['b']['severity']}
                                   for r in joined if r['ratings']['a']['severity'] != r['ratings']['b']['severity']]
    repeat_results, identity_results = {}, {}
    for reviewer in ('a', 'b'):
        pairs = []
        for r in repeats:
            assert r['duplicate_of_source'] == r['output_sha256']
            original = by_digest[r['reference_sha256']+':'+r['duplicate_of_source']]
            pairs.append({'original_id': original['id'], 'repeat_id': r['id'],
                          'original_severity': indexed_reviews[reviewer][original['id']]['severity'],
                          'repeat_severity': indexed_reviews[reviewer][r['id']]['severity']})
        repeat_results[reviewer] = dict(agreement([p['original_severity'] for p in pairs], [p['repeat_severity'] for p in pairs]), pairs=pairs)
        values = [indexed_reviews[reviewer][r['id']]['severity'] for r in controls]
        valid = [v for v in values if v is not None]
        identity_results[reviewer] = {'n_total': 6, 'n_complete': len(valid), 'null_excluded': 6-len(valid),
                                     'severity_gt0_count': sum(v > 0 for v in valid), 'severity_ge2_count': sum(v >= 2 for v in valid),
                                     'severity_gt0_rate': safe_ratio(sum(v > 0 for v in valid), len(valid)),
                                     'severity_ge2_rate': safe_ratio(sum(v >= 2 for v in valid), len(valid)),
                                     'items': [{'id': r['id'], 'reference_sha256': r['reference_sha256'], 'severity': indexed_reviews[reviewer][r['id']]['severity']} for r in controls]}
    stages = []
    for curve in curves:
        b = branches[curve['branch']]
        keyrow = by_digest[b['reference_sha256']+':'+curve['sha256']]
        row = joined_by_id[keyrow['id']]
        assert row['face']['fixed'] == curve['metrics']
        stages.append(dict(row, branch=curve['branch'], stage=curve['stage'], policy=b['policy']))
    sequential = [r for r in stages if r['policy'] == 'sequential']
    heldout = [r for r in sequential if r['branch'] != 'P01']
    assert len(sequential) == 70 and len(heldout) == 60
    assert len({r['person'] for r in sequential}) == 6 and len({r['person'] for r in heldout}) == 5
    timing = []
    for name, b in branches.items():
        if b['policy'] != 'sequential':
            continue
        branch_rows = sorted([r for r in sequential if r['branch'] == name], key=lambda r: r['stage'])
        assert [r['stage'] for r in branch_rows] == list(range(1, 11))
        alarms = {metric: next((r['stage'] for r in branch_rows if alarm(metric, r['face']['fixed'][metric])), None) for metric in METRICS}
        for reviewer in ('a', 'b'):
            first_clear = next((r['stage'] for r in branch_rows if r['ratings'][reviewer]['severity'] is not None and r['ratings'][reviewer]['severity'] >= 2), None)
            timing.append({'branch': name, 'reviewer': reviewer, 'first_ai_clear_stage': first_clear,
                           'first_frozen_alarm_stage': alarms,
                           'alarm_minus_ai_clear_stages': {metric: alarms[metric]-first_clear if alarms[metric] is not None and first_clear is not None else None for metric in METRICS},
                           'null_rating_stages': [r['stage'] for r in branch_rows if r['ratings'][reviewer]['severity'] is None]})
    result = {'manifest_sha256': sha(ROOT/'manifest.json'),
              'catalog': {'unique_candidates': 83, 'identity_controls': 6, 'hidden_repeats': 8, 'total': 97,
                          'current_final_stage_records': 90, 'sequential_stage_records': 70, 'excluding_p01_stage_records': 60},
              'inter_rater_unique': inter_rater, 'within_rater_hidden_repeats': repeat_results,
              'identity_false_positive': identity_results,
              'frozen_threshold_comparison': {'sequential70': compare_rows(sequential), 'excluding_p01_60': compare_rows(heldout)},
              'rank_correlations_exploratory': {'unique83': correlate_rows(joined), 'sequential70': correlate_rows(sequential), 'excluding_p01_60': correlate_rows(heldout)},
              'branch_rank_correlations_exploratory': {name: correlate_rows([r for r in sequential if r['branch'] == name]) for name,b in branches.items() if b['policy'] == 'sequential'},
              'first_observed_stages': timing, 'joined_unique': joined, 'joined_stages': stages,
              'rating_distributions_unique': {reviewer: dict(Counter(str(r['ratings'][reviewer]['severity']) for r in joined)) for reviewer in ('a', 'b')},
              'diagnostic_only': True, 'human_evaluation': 'not_collected', 'consensus_ground_truth': 'not_constructed'}
    for path, digest in {**source_hashes, **image_hashes}.items():
        assert sha(path) == digest, path
    save('results.json', result)
    with (ROOT/'joined-stages.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['branch', 'policy', 'stage', 'id', 'output_sha256', 'reviewer', 'severity', 'ai_clear', 'fixed_mae', 'fixed_ssim', 'fixed_lpips', 'mae_alarm', 'ssim_alarm', 'lpips_alarm', 'aligned3_mae', 'aligned3_ssim', 'aligned3_lpips'])
        writer.writeheader()
        for row in stages:
            for reviewer in ('a', 'b'):
                severity = row['ratings'][reviewer]['severity']
                writer.writerow({**{k: row[k] for k in ('branch', 'policy', 'stage', 'id', 'output_sha256')},
                                  'reviewer': reviewer, 'severity': severity, 'ai_clear': severity >= 2 if severity is not None else None,
                                  **{'fixed_'+k: row['face']['fixed'][k] for k in METRICS},
                                  **{k+'_alarm': alarm(k, row['face']['fixed'][k]) for k in METRICS},
                                  **{'aligned3_'+k: row['face']['3'][k] for k in METRICS}})
    print(json.dumps({k: result[k] for k in ('catalog', 'inter_rater_unique', 'frozen_threshold_comparison', 'first_observed_stages')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
