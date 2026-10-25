import unittest
from audit_clause_invariants import audit, cases


class InvariantAuditTests(unittest.TestCase):
    def test_all_reference_cases_preserve_correct_outputs(self):
        result = audit()
        self.assertTrue(result['passed'], result['failures'][:2])
        self.assertEqual(result['actual_model_calls'], 0)
        self.assertEqual(sum(group['cases'] for group in result['groups'].values()), 963)
        self.assertEqual(len(result['failures']), 0)

    def test_reference_constructor_does_not_share_patch_with_prior(self):
        for case in cases():
            self.assertEqual(set(case['prior']), {'jacket', 'top', 'pin', 'necklace', 'background', 'prop'})
            self.assertIsNot(case['prior'], case['patch'])


if __name__ == '__main__':
    unittest.main()
