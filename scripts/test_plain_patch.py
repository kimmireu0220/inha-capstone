import unittest
from compare_plain_patch import INITIAL, reduce_patch


class PlainPatchTests(unittest.TestCase):
    def test_updates_only_explicit_values_and_preserves_input(self):
        prior = dict(INITIAL, jacket='gray')
        result = reduce_patch(prior, ['{"jacket":"keep","pin":"none"}'])
        self.assertEqual(result, dict(prior, pin='none'))
        self.assertEqual(prior['pin'], 'original')

    def test_invalid_review_falls_back_to_initial(self):
        for raw in ['invalid', '{"prop":["plant"]}', '{"unknown":"none"}',
                    '{"prop":"plant","prop":"none"}', '{"top":"none"}']:
            with self.subTest(raw=raw):
                self.assertEqual(reduce_patch(INITIAL, [raw, '{"prop":"plant"}']), dict(INITIAL, prop='plant'))

    def test_no_valid_response_retains_previous_state(self):
        self.assertEqual(reduce_patch(INITIAL, ['{"clarification":"unclear"}', 'invalid']), INITIAL)


if __name__ == '__main__':
    unittest.main()
