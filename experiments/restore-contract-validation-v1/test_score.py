import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('restore_validation_score_test', Path(__file__).with_name('run.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RestoreScoreTests(unittest.TestCase):
    def test_same_contract_on_both_methods_without_gold_leakage(self):
        requests = ['Add a silver circular pin on the viewer-right lapel.', 'Restore the original pin.']
        benchmark = {'test': [{'request': requests[0], 'updates': {'pin': 'silver_circle_right'}},
                              {'request': requests[1], 'updates': {'pin': 'original'}}]}
        records = {}
        for i in [1, 2]:
            plan = dict.fromkeys(runner.action.INITIAL, 'keep')
            if i == 1:
                plan['pin'] = 'set'
            patch = {'pin': 'silver_circle_right'} if i == 1 else {'pin': 'keep'}
            records[f'test-{i}-generic'] = {'first': json.dumps(patch), 'second': json.dumps(patch)}
            records[f'test-{i}-action'] = {'first': json.dumps(plan),
                                          'second': json.dumps({'pin': 'silver_circle_right'} if i == 1 else {})}
        scores = runner.score(benchmark, records)
        for name in ['generic_noop', 'action']:
            self.assertEqual(scores[name]['exact_turns'], 1)
            self.assertEqual(scores[name + '_restore']['exact_turns'], 2)
        benchmark['test'][1]['updates'] = {'pin': 'none'}
        altered = runner.score(benchmark, records)
        for name in ['generic_noop_restore', 'action_restore']:
            self.assertEqual(scores[name]['rows'][1]['observed'], altered[name]['rows'][1]['observed'])
            self.assertFalse(altered[name]['rows'][1]['exact'])

    def test_negated_restore_not_forced(self):
        benchmark = {'test': [{'request': 'Do not restore the original pin.', 'updates': {}}]}
        keep = json.dumps(dict.fromkeys(runner.action.INITIAL, 'keep'))
        records = {'test-1-generic': {'first': '{}', 'second': '{}'},
                   'test-1-action': {'first': keep, 'second': '{}'}}
        scores = runner.score(benchmark, records)
        self.assertEqual(scores['action_restore']['exact_turns'], 1)
        self.assertEqual(runner.contract.obligations(benchmark['test'][0]['request']), {})


if __name__ == '__main__':
    unittest.main()
