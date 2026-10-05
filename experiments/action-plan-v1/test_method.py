import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('action_method_test', Path(__file__).with_name('method.py'))
method = importlib.util.module_from_spec(spec)
spec.loader.exec_module(method)


class ActionTests(unittest.TestCase):
    def plan(self, **actions):
        return json.dumps(dict.fromkeys(method.INITIAL, 'keep') | actions)

    def test_restore_not_keep(self):
        state, errors = method.compile_update(dict(method.INITIAL, top='white_crewneck'),
            'Restore the original shirt.', self.plan(top='reset'), '{}')
        self.assertEqual(state['top'], 'original')
        self.assertFalse(errors)

    def test_keep_does_not_revalidate_incomplete_attributes(self):
        state, errors = method.compile_update(dict(method.INITIAL, pin='gold_square_right'),
            'Keep the gold square pin. Use a library background.', self.plan(background='set'),
            '{"background":"library"}')
        self.assertEqual(state['background'], 'library')
        self.assertEqual(state['pin'], 'gold_square_right')
        self.assertFalse(errors)

    def test_invalid_value_is_local(self):
        state, errors = method.compile_update(method.INITIAL, 'Wear a green blazer. Remove the necklace.',
            self.plan(jacket='set', necklace='remove'), '{"jacket":"purple"}')
        self.assertEqual(state['jacket'], 'original')
        self.assertEqual(state['necklace'], 'none')
        self.assertIn('jacket', errors)

    def test_unmentioned_change_rejected(self):
        state, errors = method.compile_update(method.INITIAL, 'Keep the pin.',
            self.plan(jacket='remove'), '{}')
        self.assertEqual(state, method.INITIAL)
        self.assertIn('jacket', errors)

    def test_malformed_plan_preserves_state(self):
        state, errors = method.compile_update(method.INITIAL, 'Remove the pin.', '{}', '{}')
        self.assertEqual(state, method.INITIAL)
        self.assertIn('plan', errors)


if __name__ == '__main__':
    unittest.main()
