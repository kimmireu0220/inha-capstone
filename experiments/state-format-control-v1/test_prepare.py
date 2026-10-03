"""Validate the prespecified fallback without loading a model."""
import json
import unittest
from prepare import INITIAL, choose_state, parse_state


class StateValidationTest(unittest.TestCase):
    def test_complete_state(self):
        self.assertEqual(parse_state(json.dumps(INITIAL)), INITIAL)

    def test_duplicate_rejected(self):
        raw = json.dumps(INITIAL)[:-1] + ', "jacket": "none"}'
        with self.assertRaises(ValueError):
            parse_state(raw)

    def test_missing_extra_and_invalid_values(self):
        for state in [{}, {**INITIAL, 'extra': 'none'},
                      {**INITIAL, 'jacket': 'purple'}, {**INITIAL, 'jacket': []}]:
            with self.assertRaises(ValueError):
                parse_state(json.dumps(state))

    def test_second_valid_wins(self):
        second = {**INITIAL, 'jacket': 'none'}
        state, index, errors = choose_state([json.dumps(INITIAL), json.dumps(second)])
        self.assertEqual((state, index, errors), (second, 1, [None, None]))

    def test_first_valid_fallback(self):
        state, index, errors = choose_state([json.dumps(INITIAL), 'bad'])
        self.assertEqual((state, index), (INITIAL, 0))
        self.assertIsNotNone(errors[1])

    def test_both_invalid_fallback(self):
        state, index, errors = choose_state(['bad', '[]'])
        self.assertEqual(state, INITIAL)
        self.assertIsNone(index)
        self.assertTrue(all(errors))


if __name__ == '__main__':
    unittest.main()
