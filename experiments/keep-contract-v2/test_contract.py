import unittest
from contract import obligations, enforce


class ExplicitKeepTests(unittest.TestCase):
    def test_explicit_multi_field(self):
        self.assertEqual(set(obligations('Remove the necklace. Keep the navy sweater and the plant unchanged, but change the library to a red-brick studio.')), {'top', 'prop'})
        self.assertEqual(set(obligations('Restore the original shirt and necklace. Keep the lamp and office background unchanged.')), {'prop', 'background'})

    def test_abstain_ambiguous_and_unsupported(self):
        for request in ['Keep the necklace off.', 'Leave the pin out of the image.',
                        'Keep the jacket green.', 'Keep the pin hidden.',
                        'Keep the shirt but make it blue.',
                        'Keep the necklace unchanged? No, remove it.',
                        'Keep the pin hidden and the shirt unchanged.',
                        'Keep the shirt unchanged if the jacket is green.',
                        'Keep the pin.', 'Do not keep the pin unchanged.',
                        'Keep the original shirt unchanged.']:
            self.assertEqual(obligations(request), {}, request)

    def test_later_explicit_change(self):
        self.assertEqual(obligations('Keep the pin unchanged, then remove the pin.'), {})

    def test_prior_not_expected(self):
        updated, _ = enforce({'prop': 'none'}, 'Keep the plant unchanged.', {'prop': 'lamp'})
        self.assertEqual(updated['prop'], 'lamp')  # Cannot repair an already wrong prior.


if __name__ == '__main__':
    unittest.main()
