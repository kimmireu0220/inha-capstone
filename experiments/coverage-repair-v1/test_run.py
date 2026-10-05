import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('coverage_run', Path(__file__).with_name('run.py'))
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


class CoverageTests(unittest.TestCase):
    def test_missing_prop_is_rejected(self):
        with self.assertRaises(ValueError):
            run.parse('{"background":"library"}', 'Use a library with a lamp.', True)

    def test_keep_is_a_decision_but_not_an_edit(self):
        self.assertEqual(run.parse('{"pin":"keep"}', 'Keep the pin.', True), [])

    def test_no_guess_on_invalid_outputs(self):
        operations, index, errors = run.select(['oops', '{"pin":"purple"}'], 'Change the pin.', True)
        self.assertEqual(operations, [])
        self.assertIsNone(index)
        self.assertEqual(len(errors), 2)

    def test_first_valid_fallback(self):
        operations, index, _ = run.select(['{"pin":"none"}', 'bad'], 'Remove the pin.', True)
        self.assertEqual(index, 0)
        self.assertEqual(operations[0]['value'], 'none')

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):
            run.parse('{"pin":"none","pin":"keep"}', 'Remove the pin.', True)


if __name__ == '__main__':
    unittest.main()
