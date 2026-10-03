"""A reuse match must include every prespecified image-generation input."""
import unittest
from run import signature


class ReuseSignatureTest(unittest.TestCase):
    def test_all_conditions_are_required(self):
        row = {'input_sha256': 'input', 'prompt_sha256': 'prompt', 'model': 'model',
               'steps': 4, 'width': 512, 'height': 768, 'seed': 42}
        for key in row:
            changed = {**row, key: str(row[key]) + '-different'}
            self.assertNotEqual(signature(row), signature(changed), key)

    def test_labels_are_not_generation_inputs(self):
        row = {'input_sha256': 'input', 'prompt_sha256': 'prompt', 'model': 'model',
               'steps': 4, 'width': 512, 'height': 768, 'seed': 42}
        self.assertEqual(signature(row), signature({**row, 'mode': 'new-label'}))


if __name__ == '__main__':
    unittest.main()
