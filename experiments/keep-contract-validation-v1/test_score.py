import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('p_score_test', Path(__file__).with_name('run.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class PScoreTests(unittest.TestCase):
    def test_oracle_patches_are_executable_without_scoring_leakage(self):
        benchmark = json.loads(Path(__file__).with_name('benchmark.json').read_text())['histories']
        records = {f'{name}-{i}': {'first': json.dumps(turn['updates']), 'second': json.dumps(turn['updates'])}
                   for name, turns in benchmark.items() for i, turn in enumerate(turns, 1)}
        for mode, data in runner.score(benchmark, records).items():
            self.assertEqual(data['exact_turns'], 32, mode)
            self.assertEqual(data['newly_corrupted_unchanged_slots'], 0, mode)

    def test_keep_guard_applied_to_both_reducers(self):
        benchmark = {'test': [{'request': 'Use an office background with a plant.', 'updates': {'background': 'office', 'prop': 'plant'}},
                              {'request': 'Keep the plant. Use a library background.', 'updates': {'background': 'library'}}]}
        records = {'test-1': {'first': '{"background":"office","prop":"plant"}', 'second': '{"background":"office","prop":"plant"}'},
                   'test-2': {'first': '{"background":"library","prop":"keep"}', 'second': '{"background":"library","prop":"none"}'}}
        scores = runner.score(benchmark, records)
        for name in ['baseline_restore', 'isolated_restore']:
            self.assertEqual(scores[name]['exact_turns'], 1)
            self.assertEqual(scores[name]['newly_corrupted_unchanged_slots'], 1)
            self.assertEqual(scores[name + '_keep']['exact_turns'], 2)
            self.assertEqual(scores[name + '_keep']['newly_corrupted_unchanged_slots'], 0)

    def test_later_replacement_not_overridden(self):
        benchmark = {'test': [{'request': 'Keep the plant, then replace the plant with a lamp.', 'updates': {'prop': 'lamp'}}]}
        records = {'test-1': {'first': '{"prop":"lamp"}', 'second': '{"prop":"lamp"}'}}
        for data in runner.score(benchmark, records).values():
            self.assertEqual(data['exact_turns'], 1)


if __name__ == '__main__':
    unittest.main()
