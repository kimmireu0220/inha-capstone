"""Synthetic fixtures stay in a temporary directory, outside experiment evidence."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import report


class ReportIntegrationTest(unittest.TestCase):
    def run_fixture(self, new_control=False, mismatched_hash=False):
        with tempfile.TemporaryDirectory() as temporary:
            root, source = Path(temporary) / 'control', Path(temporary) / 'source'
            root.mkdir()
            source.mkdir()
            (root / 'prompts').mkdir()
            shutil.copyfile(report.SOURCE / 'report.py', source / 'report.py')
            def write(folder, name, value):
                (folder / name).write_text(json.dumps(value))
            mapping, linked, primary, secondary, base, control = {}, {}, {}, {}, [], []
            for p in range(1, 7):
                for h in range(1, 5):
                    for seed in [42, 314]:
                        key = f'R{p:02d}-U{h}-{seed}'
                        mapping[key] = {'A': 'agent', 'B': 'tracked', 'C': 'structured'}
                        primary[key] = {'scores': {'A': [0] * 6, 'B': [1] * 6}}
                        for label in 'AB':
                            secondary[key + '/' + label] = {'scores': primary[key]['scores'][label]}
                        for label, mode in mapping[key].items():
                            digest = 'agent-image' if mode == 'agent' else 'state-image'
                            linked[key + '/' + label] = {'source_comparison': key,
                                'source_label': 'A' if mode == 'agent' else 'B', 'output_sha256': digest}
                            row = {'person': f'R{p:02d}', 'history': f'U{h}', 'seed': seed, 'mode': mode,
                                   'output_sha256': digest, 'face_count': 1, 'identity_similarity': 0.8}
                            if mode == 'structured':
                                control.append({**row, 'reused': True, 'seconds': 0})
                            else:
                                base.append(row)
            pending, new_primary, new_secondary = {}, {}, {}
            if new_control:
                key = 'R01-U1-42/C'
                del linked[key]
                pending[key] = {'output_sha256': 'new-image'}
                control[0].update({'reused': False, 'seconds': 12,
                                  'output_sha256': 'wrong' if mismatched_hash else 'new-image'})
                new_primary[key] = {'scores': [1, 0, None, 1, 0, 1]}
                new_secondary[key] = {'scores': [1, 1, 0, 1, 0, 1]}
                write(root, 'ai-ratings.json', {'rater_type': 'AI', 'method_masked': True,
                                               'ratings': new_primary})
            write(root, 'blinding-map.json', mapping)
            write(root, 'linked-ratings.json', linked)
            write(root, 'pending-ratings.json', pending)
            write(root, 'face-results.json', {'rows': control})
            write(source, 'face-results.json', {'rows': base})
            write(source, 'ai-ratings.json', {'ratings': primary})
            write(source, 'second-ai-ratings.json', {'model': 'fixture', 'revision': 'fixture', 'ratings': secondary})
            write(root, 'second-ai-ratings.json', {'model': 'fixture', 'revision': 'fixture',
                  'rater_type': 'AI', 'method_masked': True, 'ratings': new_secondary})
            write(root, 'verification.json', {'complete': True, 'outputs': 48,
                  'frozen_inputs_prompts_and_output_hashes_verified': True})
            for name in ['plan.json', 'state-scores.json']:
                write(root, name, {})
            for h in range(1, 5):
                write(root / 'prompts', f'U{h}-transcript.json', {'model_calls': 2, 'seconds': 1})
            with patch.object(report, 'ROOT', root), patch.object(report, 'SOURCE', source):
                with contextlib.redirect_stdout(io.StringIO()):
                    report.main()
            return json.loads((root / 'summary.json').read_text())

    def test_all_reused_control_keeps_48_conditions_not_new_replicates(self):
        result = self.run_fixture()
        self.assertEqual(result['independent_people'], 6)
        self.assertEqual(result['control_reused_images'], 48)
        self.assertEqual(result['control_new_images'], 0)
        self.assertEqual(result['control_prompt_cost']['model_calls'], 8)
        self.assertEqual(result['primary_ai']['by_mode']['structured']['achieved'], 288)
        self.assertEqual(result['primary_ai']['by_mode']['agent']['achieved'], 0)
        self.assertEqual(result['descriptive_ai_agreement_including_reuse']['same'], 864)

    def test_new_image_scores_and_uncertainty_join_without_overwriting_source(self):
        result = self.run_fixture(new_control=True)
        self.assertEqual(result['control_reused_images'], 47)
        self.assertEqual(result['control_new_images'], 1)
        self.assertEqual(result['control_generation_seconds'], 12)
        primary = result['primary_ai']['by_mode']
        self.assertEqual(primary['structured']['achieved'], 285)
        self.assertEqual(primary['structured']['uncertain'], 1)
        self.assertEqual(primary['tracked']['achieved'], 288)
        self.assertEqual(result['secondary_ai']['by_mode']['structured']['achieved'], 286)
        self.assertEqual(result['descriptive_ai_agreement_including_reuse'],
                         {'same': 862, 'comparable': 863, 'unavailable': 1})

    def test_new_rating_must_match_measured_image_hash(self):
        with self.assertRaises(AssertionError):
            self.run_fixture(new_control=True, mismatched_hash=True)


if __name__ == '__main__':
    unittest.main()
