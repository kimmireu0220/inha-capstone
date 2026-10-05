import unittest
from method import update


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.state = dict.fromkeys(['jacket', 'top', 'pin', 'necklace', 'background', 'prop'], 'original')

    def test_unmentioned_invalid_field_does_not_cancel_valid_change(self):
        request = 'Use a library background.'
        raws = ['{"background":"library","jacket":"navy"}']
        isolated, errors, _ = update(self.state, request, raws)
        self.assertEqual(isolated['background'], 'library')
        self.assertEqual(isolated['jacket'], 'original')
        self.assertIn('jacket', errors)
        self.assertEqual(update(self.state, request, raws, atomic=True)[0], self.state)

    def test_omitted_field_not_resurrected(self):
        self.assertEqual(update(self.state, 'Use a library background.', ['{"background":"library"}', '{}'])[0], self.state)

    def test_invalid_json_falls_back_but_clarification_does_not(self):
        self.assertEqual(update(self.state, 'Use a library background.', ['{"background":"library"}', 'broken'])[0]['background'], 'library')
        self.assertEqual(update(self.state, 'Use a library background.', ['{"background":"library"}', '{"clarification":"ambiguous"}'])[0], self.state)

    def test_duplicate_keys_rejected(self):
        self.assertEqual(update(self.state, 'Use a library background.', ['{"background":"library","background":"office"}'])[0], self.state)


if __name__ == '__main__':
    unittest.main()
