import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('noop_ablation', Path(__file__).with_name('ablation.py'))
ablation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ablation)


class NoopGuardTests(unittest.TestCase):
    def test_same_value_does_not_block_unrelated_valid_changes(self):
        state = dict(ablation.run.INITIAL, pin='red_triangle_left', background='garden', prop='bench')
        operations, index = ablation.select_noop(
            ['{"pin":"red_triangle_left","background":"blue_studio","prop":"none"}'],
            'Use a pale-blue studio, with no bench. Keep the red triangular pin.', state)
        self.assertEqual(index, 0)
        updated = ablation.run.apply_operations(state, operations,
            'Use a pale-blue studio, with no bench. Keep the red triangular pin.')
        self.assertEqual(updated['pin'], 'red_triangle_left')
        self.assertEqual(updated['background'], 'blue_studio')
        self.assertEqual(updated['prop'], 'none')

    def test_actual_ungrounded_change_still_rejected(self):
        operations, index = ablation.select_noop(['{"pin":"red_triangle_left"}'],
            'Keep the pin.', dict(ablation.run.INITIAL, pin='gold_square_right'))
        self.assertEqual(operations, [])
        self.assertIsNone(index)

    def test_duplicate_values_not_silently_resolved(self):
        _, index = ablation.select_noop(['{"pin":"none","pin":"keep"}'],
            'Keep the pin.', dict(ablation.run.INITIAL, pin='none'))
        self.assertIsNone(index)


if __name__ == '__main__':
    unittest.main()
