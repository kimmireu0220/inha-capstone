import unittest
import method


class ClauseTests(unittest.TestCase):
    def test_restore_does_not_consume_following_preservation(self):
        prior = dict(method.source.base.INITIAL, jacket='gray', background='library', top='navy_sweater')
        request = 'Return the shirt to the original photo, leaving the gray blazer and library as they are.'
        state, trace = method.update(prior, request, ['{"top":"original"}'] * 2)
        self.assertEqual(state, dict(prior, top='original'))
        self.assertIn('Keep the gray blazer and library unchanged', trace['normalized_request'])

    def test_bring_back_is_validated_as_restoration(self):
        prior = dict(method.source.base.INITIAL, top='navy_sweater')
        state, _ = method.update(prior, 'Bring back the original shirt.', ['{"top":"original"}']*2)
        self.assertEqual(state['top'], 'original')

    def test_negative_change_is_explicit_preservation(self):
        prior = dict(method.source.base.INITIAL, prop='plant')
        state, _ = method.update(prior, 'Do not alter the plant.', ['{"prop":"none"}']*2)
        self.assertEqual(state, prior)

    def test_unsafe_expressions_are_not_normalized(self):
        for text in ['Do not remove the plant.', 'Never bring back the original shirt.',
                     'If needed, preserve the plant.', 'Perhaps preserve the pin.',
                     '"Preserve the plant" is a quotation.', 'Keep the necklace off.',
                     'Preserve the plant unless the background changes.']:
            with self.subTest(text=text):
                self.assertEqual(method.normalize(text), (text, []))

    def test_later_mentions_prevent_earlier_override(self):
        prior = dict(method.source.base.INITIAL, prop='plant')
        raws = ['{"prop":"none"}']*2
        state, _ = method.update(prior, 'Preserve the plant. Remove the plant.', raws)
        self.assertEqual(state['prop'], 'none')

    def test_original_input_is_not_mutated(self):
        prior = dict(method.source.base.INITIAL, prop='plant')
        saved = dict(prior)
        method.update(prior, 'Preserve the plant.', ['{"prop":"none"}']*2)
        self.assertEqual(prior, saved)


if __name__ == '__main__':
    unittest.main()
