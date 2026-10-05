import unittest
from run import transitions, MODEL, REVISION, VERSIONS


class ReviewTests(unittest.TestCase):
    def test_unknown_transitions_are_not_confirmed_successes(self):
        result = transitions({'pairs': [
            {'same_input_job': False, 'scores': [[None, 0, 1, 0], [1, 1, 0, None]]},
            {'same_input_job': True, 'scores': [[1], [1]]}]})
        self.assertEqual(result, {'unknown->1': 1, '0->1': 1, '1->0': 1, '0->unknown': 1})

    def test_fixed_model_and_environment(self):
        self.assertEqual(MODEL, 'mlx-community/Qwen2.5-VL-7B-Instruct-4bit')
        self.assertEqual(len(REVISION), 40)
        self.assertEqual(VERSIONS['mlx-vlm'], '0.7.4')


if __name__ == '__main__':
    unittest.main()
