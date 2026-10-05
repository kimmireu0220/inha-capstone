import unittest
from contract import removals, enforce


class RequestContractTests(unittest.TestCase):
    def test_explicit_remove(self):
        self.assertEqual(set(removals('Remove the pin and necklace. Keep the plant unchanged.')), {'pin', 'necklace'})
        self.assertEqual(set(removals('Keep the plant unchanged, then remove the plant. Add a beige blazer.')), {'prop'})

    def test_later_override(self):
        self.assertEqual(removals('Remove the pin, then add a red pin.'), {})
        self.assertEqual(removals('Remove the pin. Keep the pin unchanged.'), {})

    def test_abstention(self):
        for text in ['Do not remove the pin.', 'If possible, remove the pin.',
                     'Remove the original pin.', 'Remove the shirt.',
                     'Remove the background and plant.', 'Remove the pin color.',
                     'Remove the pin unless it is silver.', 'Ignore "remove the pin".',
                     'Remove the pin and replace it with a necklace.']:
            self.assertEqual(removals(text), {}, text)

    def test_two_sided(self):
        state, rules = enforce({'pin': 'red_triangle_left', 'prop': 'none'},
                               'Remove the pin and keep the plant unchanged.',
                               {'pin': 'red_triangle_left', 'prop': 'plant'})
        self.assertEqual(state, {'pin': 'none', 'prop': 'plant'})
        self.assertEqual(rules['pin']['operation'], 'remove')


if __name__ == '__main__':
    unittest.main()
