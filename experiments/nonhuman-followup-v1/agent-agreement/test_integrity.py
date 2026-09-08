"""Meaningful numerical edge cases and independent saved-data integrity checks."""
import importlib.util
import json
import unittest
from pathlib import Path

from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('agreement_calculations', ROOT/'analyze.py')
calc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)


class NumericalSafety(unittest.TestCase):
    def test_thresholds_inclusive_and_directional(self):
        for name, threshold in calc.THRESHOLDS.items():
            self.assertTrue(calc.alarm(name, threshold))
            delta = 1e-7 if name == 'ssim' else -1e-7
            self.assertFalse(calc.alarm(name, threshold+delta))
            self.assertTrue(calc.alarm(name, threshold-delta))

    def test_hand_calculated_confusion_and_null_exclusion(self):
        c = calc.confusion([True, True, False, False, True], [3, 0, 0, 2, None])
        self.assertEqual([c[k] for k in ('tp', 'fp', 'tn', 'fn')], [1, 1, 1, 1])
        self.assertEqual(c['n_complete'], 4)
        self.assertEqual(c['null_excluded'], 1)
        for k in ('precision', 'recall', 'specificity', 'binary_agreement'):
            self.assertEqual(c[k], .5)

    def test_zero_denominators_are_null(self):
        c = calc.confusion([False, False], [0, 1])
        self.assertIsNone(c['precision'])
        self.assertIsNone(c['recall'])
        self.assertEqual(c['specificity'], 1)
        empty = calc.confusion([True], [None])
        self.assertEqual(empty['n_complete'], 0)
        self.assertIsNone(empty['binary_agreement'])

    def test_weighted_kappa_hand_examples(self):
        for power in (1, 2):
            self.assertAlmostEqual(calc.weighted_kappa([0, 0, 1, 1], [0, 1, 1, 1], power)['value'], .5)
            self.assertAlmostEqual(calc.weighted_kappa([0, 3], [3, 0], power)['value'], -1)
            self.assertEqual(calc.weighted_kappa([0, 1, 2, 3], [0, 1, 2, 3], power)['value'], 1)
            self.assertIsNone(calc.weighted_kappa([3, 3], [3, 3], power)['value'])
            self.assertEqual(calc.weighted_kappa([3, 3], [3, 3], power)['reason'], 'zero_expected_disagreement')
            self.assertIsNone(calc.weighted_kappa([None], [1], power)['value'])

    def test_agreement_null_and_binary_boundary(self):
        result = calc.agreement([0, 1, 2, 3, None], [0, 2, 1, 3, 0])
        self.assertEqual(result['n_complete'], 4)
        self.assertEqual(result['ordinal_exact_count'], 2)
        self.assertEqual(result['binary_agreement_count'], 2)
        self.assertEqual(result['null_excluded'], 1)

    def test_spearman_ties_agree_with_scipy(self):
        x, y = [1, 1, 3, 4, 4], [0, 2, 2, 3, 1]
        self.assertAlmostEqual(calc.spearman(x, y)['rho'], float(spearmanr(x, y).statistic), places=14)
        self.assertEqual(calc.spearman([1, 2, 3], [3, 2, 1])['rho'], -1)

    def test_spearman_zero_variance_null_and_small_sample(self):
        self.assertEqual(calc.spearman([1, 1], [0, 3])['reason'], 'zero_rank_variance')
        self.assertIsNone(calc.spearman([1, 1], [0, 3])['rho'])
        self.assertEqual(calc.spearman([1, None], [3, 2])['reason'], 'fewer_than_two_pairs')
        self.assertEqual(calc.spearman([1, None, 3], [0, 1, 3])['n_complete'], 2)


class SavedIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = calc.read(ROOT/'results.json')
        cls.m = calc.read(ROOT/'manifest.json')
        cls.key = calc.read(ROOT.parent/'private/face-key.json')
        cls.unique = cls.d['joined_unique']
        cls.stages = cls.d['joined_stages']

    def test_all_sources_including_reviews_are_unchanged(self):
        self.assertEqual(calc.sha(ROOT/'manifest.json'), self.d['manifest_sha256'])
        for path, digest in {**self.m['source_hashes'], **self.m['image_hashes']}.items():
            self.assertEqual(calc.sha(path), digest, path)

    def test_exact_packet_split_and_main_exclusion(self):
        candidates = [r for r in self.key if 'control' not in r and 'duplicate_of_source' not in r]
        identity = [r for r in self.key if r.get('control') == 'identity']
        repeats = [r for r in self.key if 'duplicate_of_source' in r]
        self.assertEqual([len(candidates), len(identity), len(repeats)], [83, 6, 8])
        self.assertEqual({r['id'] for r in candidates}, {r['id'] for r in self.unique})
        excluded = {r['id'] for r in identity+repeats}
        self.assertFalse(excluded & {r['id'] for r in self.stages})
        self.assertEqual(self.m['rendered_pair_crop_bytes_match_sources'], 97)

    def test_reviews_join_exactly_without_adjudication(self):
        for reviewer in ('a', 'b'):
            source = {r['id']: r for r in calc.read(ROOT.parent/f'reviews/face-{reviewer}.json')['items']}
            for r in self.unique:
                self.assertEqual(r['ratings'][reviewer], source[r['id']])

    def test_matrix_counts_and_margins(self):
        m = self.d['inter_rater_unique']
        matrix = m['ordinal_matrix_rows_a_columns_b']
        self.assertEqual(sum(sum(r) for r in matrix), m['n_complete'])
        self.assertEqual(sum(matrix[i][i] for i in range(4)), m['ordinal_exact_count'])
        for i in range(4):
            self.assertEqual(sum(matrix[i]), sum(r['ratings']['a']['severity'] == i for r in self.unique))
            self.assertEqual(sum(row[i] for row in matrix), sum(r['ratings']['b']['severity'] == i for r in self.unique))

    def test_sequential_counts_person_dependence_and_frozen_scores(self):
        sequential = [r for r in self.stages if r['policy'] == 'sequential']
        heldout = [r for r in sequential if r['branch'] != 'P01']
        self.assertEqual((len(sequential), len(heldout)), (70, 60))
        self.assertEqual((len({r['person'] for r in sequential}), len({r['person'] for r in heldout})), (6, 5))
        self.assertEqual(len({r['branch'] for r in sequential}), 7)
        curves = {(r['branch'], r['stage']): r for r in calc.read(calc.CURRENT/'curves.json')}
        for r in self.stages:
            self.assertEqual(r['face']['fixed'], curves[(r['branch'], r['stage'])]['metrics'])

    def test_confusion_reconstructed_from_current_stage_rows(self):
        for cohort, number in [('sequential70', 70), ('excluding_p01_60', 60)]:
            rows = [r for r in self.stages if r['policy'] == 'sequential' and (number == 70 or r['branch'] != 'P01')]
            for reviewer, metrics in self.d['frozen_threshold_comparison'][cohort].items():
                for metric, c in metrics.items():
                    pairs = [(calc.alarm(metric, r['face']['fixed'][metric]), r['ratings'][reviewer]['severity']) for r in rows]
                    expected = {name: sum(s is not None and p == pred and (s >= 2) == target for p,s in pairs)
                                for name,pred,target in [('tp', True, True), ('fp', True, False), ('tn', False, False), ('fn', False, True)]}
                    self.assertEqual({k: c[k] for k in expected}, expected)
                    self.assertEqual(c['n_total'], number)
                    self.assertEqual(sum(expected.values()), c['n_complete'])

    def test_saved_correlations_match_scipy(self):
        cohorts = {'unique83': self.unique,
                   'sequential70': [r for r in self.stages if r['policy'] == 'sequential'],
                   'excluding_p01_60': [r for r in self.stages if r['policy'] == 'sequential' and r['branch'] != 'P01']}
        for name, rows in cohorts.items():
            for reviewer, metrics in self.d['rank_correlations_exploratory'][name].items():
                for metric, values in metrics.items():
                    for mode, result in values['modes'].items():
                        pairs = [(1-r['face'][mode][metric] if metric == 'ssim' else r['face'][mode][metric], r['ratings'][reviewer]['severity']) for r in rows if r['ratings'][reviewer]['severity'] is not None]
                        x,y = zip(*pairs)
                        self.assertAlmostEqual(result['rho'], float(spearmanr(x,y).statistic), places=13)

    def test_timing_is_first_observed_stage(self):
        for t in self.d['first_observed_stages']:
            rows = [r for r in self.stages if r['branch'] == t['branch']]
            clear = [r['stage'] for r in rows if r['ratings'][t['reviewer']]['severity'] is not None and r['ratings'][t['reviewer']]['severity'] >= 2]
            self.assertEqual(t['first_ai_clear_stage'], min(clear) if clear else None)
            for metric, first in t['first_frozen_alarm_stage'].items():
                alarms = [r['stage'] for r in rows if calc.alarm(metric, r['face']['fixed'][metric])]
                self.assertEqual(first, min(alarms) if alarms else None)

    def test_no_human_or_aligned_threshold_claim(self):
        self.assertEqual(self.d['human_evaluation'], 'not_collected')
        self.assertEqual(self.d['consensus_ground_truth'], 'not_constructed')
        self.assertEqual(self.m['aligned_threshold_performance'], 'not_computed')
        self.assertFalse(self.m['new_detector_training'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
