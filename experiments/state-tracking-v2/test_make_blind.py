"""The shared plate generator creates AI inputs, not human rating forms."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

spec = importlib.util.spec_from_file_location(
    'shared_blind_test', Path(__file__).resolve().parents[1] / 'state-tracking-v1/make_blind.py')
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


class PlateGenerationTest(unittest.TestCase):
    def test_ai_inputs_without_rating_form(self):
        previous_root = shared.ROOT
        self.addCleanup(setattr, shared, 'ROOT', previous_root)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'references').mkdir()
            Image.new('RGB', (16, 24), 'gray').save(root / 'references/R01.png')
            calls = []
            for mode in ['agent', 'tracked']:
                (root / mode).mkdir()
                Image.new('RGB', (16, 24), 'blue').save(root / mode / 'output.png')
                calls.append(dict(person='R01', history='U1', seed=1, mode=mode, folder=mode))
            (root / 'calls.json').write_text(json.dumps({'calls': calls}))
            shared.main(root)
            mapping = (root / 'blinding-map.json').read_bytes()
            self.assertEqual(set(json.loads(mapping)['R01-U1-1'].values()), {'agent', 'tracked'})
            self.assertTrue((root / 'blind/R01-U1-1.png').exists())
            self.assertFalse((root / 'human-ratings.csv').exists())
            shared.main(root)
            self.assertEqual(mapping, (root / 'blinding-map.json').read_bytes())
            self.assertFalse((root / 'human-ratings.csv').exists())


if __name__ == '__main__':
    unittest.main()
