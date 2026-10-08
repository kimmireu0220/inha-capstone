import unittest
import run


class Checks(unittest.TestCase):
    def test_shape_and_matched_expression(self):
        data = run.benchmark()
        self.assertEqual(len(data), 12)
        for n in range(1, 5):
            expected = [t['updates']['expression'] for t in data[f'C{n}-single']]
            for level in ['compound', 'mixed']:
                self.assertEqual([t['updates']['expression'] for t in data[f'C{n}-{level}']], expected)
        for turns in data.values():
            self.assertEqual(len(turns), 4)
            for turn in turns:
                run.parse(__import__('json').dumps(turn['updates']))

    def test_rules(self):
        prior = dict(run.INITIAL, expression='neutral', hand_pose='hands_down')
        state, rules = run.guard(run.INITIAL, prior, 'Keep the expression and hand pose unchanged. Remove the necklace.')
        self.assertEqual(state['expression'], 'neutral')
        self.assertEqual(state['hand_pose'], 'hands_down')
        self.assertEqual(state['necklace'], 'none')
        self.assertEqual(len(rules), 3)
        state, rules = run.guard(run.INITIAL, prior, 'Keep the expression unchanged. Change the expression to surprised.')
        self.assertEqual(rules, [])

    def test_abstention(self):
        for request in ['If needed, remove the necklace.', 'Remove it.', 'Remove the expression.', 'Keep the necklace off.']:
            self.assertEqual(run.guard(run.INITIAL, run.INITIAL, request)[1], [])

    def test_schema(self):
        for raw in ['{"expression":"bad"}', '{"expression":"neutral","expression":"surprised"}', '[]']:
            with self.assertRaises(ValueError):
                run.parse(raw)


if __name__ == '__main__':
    unittest.main()
