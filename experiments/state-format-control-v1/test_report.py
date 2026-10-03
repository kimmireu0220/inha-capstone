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
    def test_all_reused_control_keeps_48_conditions_not_new_replicates(self):
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
            write(root, 'blinding-map.json', mapping)
            write(root, 'linked-ratings.json', linked)
            write(root, 'pending-ratings.json', {})
            write(root, 'face-results.json', {'rows': control})
            write(source, 'face-results.json', {'rows': base})
            write(source, 'ai-ratings.json', {'ratings': primary})
            write(source, 'second-ai-ratings.json', {'model': 'fixture', 'revision': 'fixture', 'ratings': secondary})
            write(root, 'second-ai-ratings.json', {'model': 'fixture', 'revision': 'fixture', 'ratings': {}})
            write(root, 'verification.json', {'complete': True, 'outputs': 48,
                  'frozen_inputs_prompts_and_output_hashes_verified': True})
            for name in ['plan.json', 'state-scores.json']:
                write(root, name, {})
            for h in range(1, 5):
                write(root / 'prompts', f'U{h}-transcript.json', {'model_calls': 2, 'seconds': 1})
            with patch.object(report, 'ROOT', root), patch.object(report, 'SOURCE', source):
                with contextlib.redirect_stdout(io.StringIO()):
                    report.main()
            result = json.loads((root / 'summary.json').read_text())
            self.assertEqual(result['independent_people'], 6)
            self.assertEqual(result['control_reused_images'], 48)
            self.assertEqual(result['control_new_images'], 0)
            self.assertEqual(result['control_prompt_cost']['model_calls'], 8)
            self.assertEqual(result['primary_ai']['by_mode']['structured']['achieved'], 288)
            self.assertEqual(result['primary_ai']['by_mode']['agent']['achieved'], 0)
            self.assertEqual(result['descriptive_ai_agreement_including_reuse']['same'], 864)


if __name__ == '__main__':
    unittest.main()
