import copy
import json
import unittest

import run


class ParaphraseTests(unittest.TestCase):
    def test_pairs_keep_original_targets(self):
        original = json.loads((run.ROOT.parent / 'isolated-contract-v1/benchmark.json').read_text())['histories']
        paired = run.benchmark()
        self.assertEqual(set(original), set(paired))
        for name in original:
            self.assertEqual(len(paired[name]), 4)
            for old, new in zip(original[name], paired[name], strict=True):
                self.assertEqual(old['updates'], new['updates'])
                self.assertNotEqual(old['request'], new['request'])

    def test_unsupported_clauses_do_not_overwrite(self):
        state = dict(run.source.base.INITIAL, jacket='gray', prop='plant')
        requests = ['Do not remove the plant.', 'Remove the plant if the jacket is gray.',
                    'Perhaps remove the plant.', '"Remove the plant" is a quotation.',
                    'Remove it.', 'Keep the jacket beige.', 'Keep the necklace off.',
                    'Keep the plant unchanged if the background is blue.',
                    'Never remove the plant.', 'Remove the plant, not the necklace.']
        for request in requests:
            with self.subTest(request=request):
                result, rules = run.source.contract.enforce(state, request, state)
                self.assertEqual(result, state)
                self.assertEqual(rules, {})

    def test_supported_clauses_correct_without_mutating_inputs(self):
        prior = dict(run.source.base.INITIAL, jacket='gray', prop='plant')
        candidate = dict(prior, jacket='navy')
        snapshot = copy.deepcopy((candidate, prior))
        result, rules = run.source.contract.enforce(
            candidate, 'Keep the gray blazer unchanged. Remove the plant.', prior)
        self.assertEqual(result, dict(prior, prop='none'))
        self.assertEqual(set(rules), {'jacket', 'prop'})
        self.assertEqual((candidate, prior), snapshot)

    def test_later_instruction_is_not_overridden(self):
        prior = dict(run.source.base.INITIAL, prop='plant')
        candidate = dict(prior, prop='lamp')
        result, rules = run.source.contract.enforce(
            candidate, 'Remove the plant. Replace the plant with a lamp.', prior)
        self.assertEqual(result, candidate)
        self.assertEqual(rules, {})


if __name__ == '__main__':
    unittest.main()
