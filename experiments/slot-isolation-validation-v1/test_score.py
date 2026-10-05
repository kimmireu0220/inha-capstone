import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('isolation_validation_test', Path(__file__).with_name('run.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ScoreTests(unittest.TestCase):
    def test_shared_outputs_separate_states(self):
        benchmark = {'test': [{'request': 'Use a library background.', 'updates': {'background': 'library'}},
                              {'request': 'Restore the original background.', 'updates': {'background': 'original'}}]}
        records = {'test-1': {'first': '{"background":"library","jacket":"navy"}', 'second': '{"background":"library","jacket":"navy"}'},
                   'test-2': {'first': '{"background":"keep"}', 'second': '{"background":"keep"}'}}
        scores = runner.score(benchmark, records)
        self.assertEqual(scores['baseline_restore']['exact_turns'], 1)
        self.assertEqual(scores['latest_atomic_restore']['exact_turns'], 1)
        self.assertEqual(scores['isolated_restore']['exact_turns'], 2)
        self.assertEqual(scores['isolated']['exact_turns'], 1)
        self.assertEqual(scores['first_isolated_restore']['exact_turns'], 2)
        for data in scores.values():
            self.assertEqual(data['newly_corrupted_unchanged_slots'], 0)


if __name__ == '__main__':
    unittest.main()
