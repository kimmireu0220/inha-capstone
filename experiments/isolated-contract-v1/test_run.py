import json
import unittest
import run


class ContractTests(unittest.TestCase):
    def test_all_modes_apply_simple_correct_patch(self):
        request = 'Wear a navy blazer.'
        benchmark = {'X': [dict(request=request, updates={'jacket': 'navy'})]}
        record = {'X-1': dict(request=request, first='{"jacket":"navy"}', second='{"jacket":"navy"}')}
        self.assertTrue(all(r['exact_turns'] == 1 for r in run.score(benchmark, record).values()))

    def test_isolation_retains_valid_changes(self):
        request = 'Wear a navy blazer.'
        benchmark = {'X': [dict(request=request, updates={'jacket': 'navy'})]}
        raw = '{"jacket":"navy","unknown":"bad"}'
        record = {'X-1': dict(request=request, first=raw, second=raw)}
        result = run.score(benchmark, record)
        self.assertEqual(result['baseline_restore']['exact_turns'], 0)
        self.assertEqual(result['isolated_keep_remove']['exact_turns'], 1)

    def test_annotation_does_not_change_observed_state(self):
        request = 'Wear a navy blazer.'
        record = {'X-1': dict(request=request, first='{}', second='{}')}
        a = run.score({'X': [dict(request=request, updates={'jacket': 'navy'})]}, record)
        b = run.score({'X': [dict(request=request, updates={'jacket': 'green'})]}, record)
        for mode in a:
            self.assertEqual(a[mode]['rows'][0]['observed'], b[mode]['rows'][0]['observed'])

    def test_benchmark_shape_and_values(self):
        benchmark = json.loads((run.ROOT / 'benchmark.json').read_text())['histories']
        self.assertEqual(len(benchmark), 8)
        self.assertTrue(all(len(turns) == 4 for turns in benchmark.values()))
        for turns in benchmark.values():
            for turn in turns:
                self.assertTrue(set(turn['updates']) <= set(run.base.INITIAL))


if __name__ == '__main__':
    unittest.main()
