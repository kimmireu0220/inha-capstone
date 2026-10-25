import unittest
from report import paired_statistics, holm


class StatisticsTests(unittest.TestCase):
    def test_zero_difference(self):
        d = paired_statistics([.5]*4, [.5]*4, draws=100)
        self.assertEqual(d['permutation_p'], 1)
        self.assertEqual(d['bootstrap_95_percentage_points'], [0, 0])

    def test_uniform_improvement_exact_sign_distribution(self):
        d = paired_statistics([1]*4, [0]*4, draws=100)
        self.assertEqual(d['permutation_p'], 2/16)
        self.assertEqual(d['difference_percentage_points'], 100)
        self.assertEqual(d['bootstrap_95_percentage_points'], [100, 100])

    def test_holm_step_down_is_monotone(self):
        self.assertEqual(holm(dict(a=.01, b=.04)), dict(a=.02, b=.04))
        self.assertEqual(holm(dict(a=.03, b=.04)), dict(a=.06, b=.06))


if __name__ == '__main__':
    unittest.main()
