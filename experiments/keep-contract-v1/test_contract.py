import unittest
from contract import obligations, enforce


class KeepTests(unittest.TestCase):
    def test_keep_shared_nouns(self):
        self.assertEqual(set(obligations('Remove the pin. Restore the original blazer and keep the shirt and plant unchanged.')), {'top', 'prop'})

    def test_action_scope(self):
        self.assertEqual(set(obligations('Keep the triangular pin while changing the gray blazer to beige.')), {'pin'})
        self.assertEqual(set(obligations('Keep the necklace but replace the blazer with green.')), {'necklace'})

    def test_later_mention_abstains(self):
        self.assertEqual(obligations('Keep the pin, then remove the pin.'), {})

    def test_unsafe_abstains(self):
        for request in ['Do not keep the pin.', 'If possible, keep the pin.', 'Keep the original pin.',
                        'Ignore "keep the pin". Remove the pin.', 'Never keep the necklace.']:
            self.assertEqual(obligations(request), {}, request)

    def test_prior_not_gold(self):
        prior = {'prop': 'plant', 'pin': 'none'}
        output, rules = enforce({'prop': 'none', 'pin': 'original'}, 'Keep the plant.', prior)
        self.assertEqual(output, {'prop': 'plant', 'pin': 'original'})
        self.assertEqual(set(rules), {'prop'})


if __name__ == '__main__':
    unittest.main()
