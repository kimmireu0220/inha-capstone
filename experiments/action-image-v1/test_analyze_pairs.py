import unittest
from analyze_pairs import compare


def row(mode, job='same', score=1, face=.8):
    return dict(person='R1', history='S1', turn=1, mode=mode, job=job,
                scores=[score] * 6, rgb_sha256=job, identity_similarity=face)


class PairTests(unittest.TestCase):
    def test_shared_is_not_an_independent_win(self):
        result = compare([row('base'), row('new')], ['base', 'new'])
        self.assertEqual(result['shared_input_pairs'], 1)
        self.assertEqual(result['different_input_goal_wins'], 0)

    def test_shared_score_mismatch_rejected(self):
        with self.assertRaises(AssertionError):
            compare([row('base'), row('new', score=0)], ['base', 'new'])

    def test_unknown_is_not_a_success(self):
        result = compare([row('base', score=None), row('new', job='new')], ['base', 'new'])
        self.assertEqual(result['different_input_goal_delta'], 6)
        self.assertEqual(result['pairs'][0]['unknown_counts'], [6, 0])

    def test_missing_face_stays_missing(self):
        result = compare([row('base', face=None), row('new', job='new')], ['base', 'new'])
        self.assertIsNone(result['different_input_mean_face_delta'])


if __name__ == '__main__':
    unittest.main()
