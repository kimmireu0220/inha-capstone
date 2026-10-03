import unittest
from report import summarize, validate_scores


class ScoresTest(unittest.TestCase):
    def test_valid(self):
        scores = [1, 0, None, 1, 0, 1]
        self.assertEqual(validate_scores(scores), scores)

    def test_invalid(self):
        for scores in [[1] * 5, [1] * 7, [True] * 6, [1.0] * 6,
                       ['1'] * 6, [2] * 6, '111111']:
            with self.assertRaises(AssertionError):
                validate_scores(scores)

    def test_uncertain_not_success(self):
        row = {'history': 'U1', 'scores': [None, 1, 0, 1, 0, 1],
               'identity_similarity': None, 'face_count': 0}
        summary = summarize([row])
        self.assertEqual(summary['target_total'], 6)
        self.assertEqual(summary['achieved'], 3)
        self.assertEqual(summary['uncertain'], 1)
        self.assertEqual(summary['cancelled_total'], 3)
        self.assertEqual(summary['cancelled_achieved'], 1)
        self.assertIsNone(summary['identity_mean'])


if __name__ == '__main__':
    unittest.main()
