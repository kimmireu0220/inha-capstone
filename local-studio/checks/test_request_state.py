"""Reducer checks cover deletion persistence, negation, and atomic rejection."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from request_state import INITIAL, apply_operations, patch_operations, render_prompt


class StateTests(unittest.TestCase):
    def test_removal_persists_across_unrelated_turn(self):
        state = dict(INITIAL, jacket='navy', top='white_crewneck', pin='silver_circle_right')
        state = apply_operations(state, [{'field': 'pin', 'op': 'remove',
            'evidence': 'Remove the pin'}], 'Remove the pin')
        state = apply_operations(state, [{'field': 'background', 'op': 'set',
            'value': 'library', 'evidence': 'library'}], 'Use a library')
        self.assertEqual(state['pin'], 'none')
        self.assertNotIn('silver', render_prompt(state))

    def test_keep_and_readdition(self):
        state = dict(INITIAL, necklace='gold_round', pin='none')
        result = apply_operations(state, [
            {'field': 'necklace', 'op': 'keep', 'evidence': 'Do not remove the necklace'},
            {'field': 'pin', 'op': 'set', 'value': 'gold_square_right', 'evidence': 'gold square pin'}],
            'Do not remove the necklace; add a gold square pin')
        self.assertEqual(result['necklace'], 'gold_round')
        self.assertEqual(result['pin'], 'gold_square_right')

    def test_invalid_transaction_is_atomic(self):
        state = dict(INITIAL)
        with self.assertRaises(ValueError):
            apply_operations(state, [
                {'field': 'jacket', 'op': 'set', 'value': 'gray', 'evidence': 'gray'},
                {'field': 'top', 'op': 'set', 'value': 'invented', 'evidence': 'shirt'}],
                'gray jacket and shirt')
        self.assertEqual(state, INITIAL)

    def test_grounding_and_duplicate_validation(self):
        with self.assertRaises(ValueError):
            apply_operations(INITIAL, [{'field': 'pin', 'op': 'remove',
                'evidence': 'not in request'}], 'Remove the pin')
        with self.assertRaises(ValueError):
            apply_operations(INITIAL, [
                {'field': 'pin', 'op': 'remove', 'evidence': 'pin'},
                {'field': 'pin', 'op': 'keep', 'evidence': 'pin'}], 'pin')

    def test_reset_uses_original(self):
        result = apply_operations(dict(INITIAL, jacket='green'), [
            {'field': 'jacket', 'op': 'reset', 'evidence': 'original jacket'}],
            'Restore the original jacket')
        self.assertEqual(result['jacket'], 'original')

    def test_unmentioned_keep_has_no_effect(self):
        operations = patch_operations({'necklace': 'none', 'prop': 'keep'}, 'Remove the necklace')
        self.assertEqual([row['field'] for row in operations], ['necklace'])

    def test_wrong_supported_color_is_rejected(self):
        with self.assertRaises(ValueError):
            patch_operations({'background': 'blue_studio'}, 'Use a red-brick studio')
        self.assertEqual(patch_operations({'background': 'brick_studio'},
            'Use a red-brick studio')[0]['value'], 'brick_studio')


if __name__ == '__main__':
    unittest.main()
