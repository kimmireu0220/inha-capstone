"""Read-only checks for the current catalog and saved diagnostic computations."""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CURRENT = ROOT.parents[2] / 'experiments/revised-tail-v1'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = read(ROOT/'results.json')
        cls.manifest = read(ROOT/'manifest.json')
        cls.inputs = read(CURRENT/'inputs.json')
        cls.progress = read(CURRENT/'progress.json')
        cls.curves = read(CURRENT/'curves.json')
        cls.rows = cls.result['rows']
        cls.stage_ids = {(r['branch'], r['stage']): r['id'] for r in cls.result['stage_ids']}

    def test_source_and_image_hashes_unchanged(self):
        self.assertEqual(sha(ROOT/'manifest.json'), self.result['manifest_sha256'])
        for path, digest in {**self.manifest['source_hashes'], **self.manifest['image_hashes']}.items():
            self.assertEqual(sha(path), digest, path)

    def test_only_current_catalog_outputs(self):
        expected = set()
        for branch in self.inputs:
            expected.update(branch['prefix_files'])
        for branch in self.progress['branches']:
            for row in branch['rows']:
                expected.update([row['raw'], row['final']])
        expected.update(r['path'] for r in self.curves)
        actual = {path for r in self.rows.values() for path in r['paths']}
        self.assertEqual(actual, expected)
        self.assertEqual({r['sha256'] for r in self.rows.values()}, {sha(path) for path in expected})
        self.assertEqual(len(self.stage_ids), 90)
        self.assertEqual(len(self.manifest['branches']), 9)
        self.assertEqual(self.manifest['unique_final_outputs'], 83)

    def test_curve_hashes_and_fixed_metric_reproduction(self):
        for curve in self.curves:
            row = self.rows[self.stage_ids[(curve['branch'], curve['stage'])]]
            self.assertEqual(row['sha256'], curve['sha256'])
            for k in ('mae', 'ssim', 'lpips'):
                self.assertLess(abs(row['face']['fixed'][k]-curve['metrics'][k]), 1e-6)

    def test_skin_regions_are_original_p04_only(self):
        self.assertEqual(self.manifest['regions'], {'forehead': [452,144,568,178],
            'cheek_viewer_left': [412,264,448,306], 'cheek_viewer_right': [572,264,604,306]})
        for row in self.rows.values():
            is_p04 = all(use['branch'].startswith('P04') for use in row['uses'])
            self.assertEqual('skin' in row, is_p04)

    def test_integer_bounded_locations_and_regions(self):
        for row in self.rows.values():
            self.assertEqual(set(row['locations']), {'1', '3', '6'})
            for location in row['locations'].values():
                for k in ('dx', 'dy'):
                    self.assertIsInstance(location[k], int)
                    self.assertLessEqual(abs(location[k]), 64)
                self.assertGreaterEqual(location['ncc'], -1.00001)
                self.assertLessEqual(location['ncc'], 1.00001)
                rois = [row['roi']] + (list(self.manifest['regions'].values()) if 'skin' in row else [])
                for x0, y0, x1, y1 in rois:
                    self.assertTrue(0 <= x0+location['dx'] < x1+location['dx'] <= 1024)
                    self.assertTrue(0 <= y0+location['dy'] < y1+location['dy'] <= 1536)

    def test_skin_weighting(self):
        for row in self.rows.values():
            if 'skin' not in row:
                continue
            for values in row['skin'].values():
                for k in ('mae', 'ssim', 'highpass_mae'):
                    weight = 'ssim_valid_count' if k == 'ssim' else 'pixel_count'
                    expected = sum(r[k]*r[weight] for r in values['regions'].values()) / sum(r[weight] for r in values['regions'].values())
                    self.assertAlmostEqual(expected, values[k], places=12)

    def test_averages_use_ten_stages_and_preserve_duplicates(self):
        for branch, summary in self.result['summary'].items():
            rows = [self.rows[self.stage_ids[(branch, s)]] for s in range(1, 11)]
            for scope in ('face', 'skin'):
                if scope not in summary:
                    continue
                for mode, endpoints in summary[scope].items():
                    for k, value in endpoints['mean'].items():
                        self.assertAlmostEqual(sum(r[scope][mode][k] for r in rows)/10, value, places=12)
                        self.assertEqual(endpoints['final'][k], rows[-1][scope][mode][k])

    def test_rankings_cover_settings_and_both_endpoints(self):
        ranks = self.result['p04_rankings']
        self.assertEqual(len(ranks), 5 * 4 * 2 * 3)
        for r in ranks:
            expected = sorted(r['values'], key=lambda b: (-r['values'][b] if r['metric'] == 'ssim' else r['values'][b], b))
            self.assertEqual(r['order_best_first'], expected)

    def test_controls_known_translation_and_unchanged_crop(self):
        controls = self.result['controls']
        self.assertEqual(len(controls), 11)
        for c in controls:
            if c['expected_translation'] is not None:
                for location in c['locations'].values():
                    self.assertEqual([location['dx'], location['dy']], c['expected_translation'])
            if c['name'] in ('identity', 'distant_surround_replacement') or c['name'].startswith('translation_'):
                for mode in ('1', '3', '6'):
                    self.assertEqual(c['face'][mode]['mae'], 0)
                    self.assertEqual(c['face'][mode]['ssim'], 1)
                    self.assertLess(abs(c['face'][mode]['lpips']), 1e-7)
                    self.assertEqual(c['skin'][mode]['mae'], 0)
                    self.assertEqual(c['skin'][mode]['ssim'], 1)
                    self.assertLess(c['skin'][mode]['highpass_mae'], 1e-7)

    def test_brightness_remains_and_wave_response_increases(self):
        for mode in ('1', '3', '6'):
            waves = [c['skin'][mode]['highpass_mae'] for c in self.result['controls'] if c['name'].startswith('added_skin_wave_')]
            self.assertTrue(waves[0] < waves[1] < waves[2])
            for c in self.result['controls']:
                if c['name'].startswith('brightness_'):
                    self.assertGreater(c['face'][mode]['mae'], .02)
                    self.assertGreater(c['skin'][mode]['mae'], .02)

    def test_no_generated_or_rated_result_claims(self):
        self.assertTrue(self.result['diagnostic_only'])
        self.assertEqual(self.result['human_evaluation'], 'not_collected')
        self.assertEqual(self.result['independent_agent_evaluation'], 'not_collected')
        self.assertEqual(self.manifest['settings']['primary_sigma'], 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
