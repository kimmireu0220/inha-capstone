import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('validation_score_test', Path(__file__).with_name('run.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ScoreTests(unittest.TestCase):
    def test_methods_replayed_with_separate_states(self):
        benchmark = {'test': [
            {'request': 'Add a silver circular pin on the viewer-right lapel.', 'updates': {'pin': 'silver_circle_right'}},
            {'request': 'Restore the original pin.', 'updates': {'pin': 'original'}}]}
        records = {}
        for i, turn in enumerate(benchmark['test'], 1):
            plan = dict.fromkeys(runner.action.INITIAL, 'keep')
            plan['pin'] = 'set' if i == 1 else 'reset'
            values = {'pin': 'silver_circle_right'} if i == 1 else {}
            records[f'test-{i}-action'] = {'first': json.dumps(plan), 'second': json.dumps(values)}
            patch = {'pin': 'silver_circle_right'} if i == 1 else {'pin': 'keep'}
            records[f'test-{i}-generic'] = {'first': json.dumps(patch), 'second': json.dumps(patch)}
        scores = runner.score(benchmark, records)
        self.assertEqual(scores['action']['exact_turns'], 2)
        self.assertEqual(scores['generic']['exact_turns'], 1)
        self.assertEqual(scores['generic_noop']['exact_turns'], 1)
        self.assertEqual(scores['action']['newly_corrupted_unchanged_slots'], 0)
        self.assertEqual(scores['action_atomic']['exact_turns'], 2)

    def test_atomic_ablation_rejects_whole_failed_turn(self):
        benchmark = {'test': [{'request': 'Use a library background and a green blazer.',
                               'updates': {'background': 'library', 'jacket': 'green'}}]}
        plan = dict.fromkeys(runner.action.INITIAL, 'keep')
        plan.update(background='set', jacket='set')
        records = {'test-1-action': {'first': json.dumps(plan), 'second': '{"background":"library","jacket":"unknown"}'},
                   'test-1-generic': {'first': '{}', 'second': '{}'}}
        scores = runner.score(benchmark, records)
        self.assertEqual(scores['action']['correct_slots'], 5)
        self.assertEqual(scores['action_atomic']['correct_slots'], 4)


if __name__ == '__main__':
    unittest.main()
