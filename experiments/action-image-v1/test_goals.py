import unittest
from goals import FIELDS, goals, prompt


class GoalsTest(unittest.TestCase):
    def test_original_and_absent_are_visually_equivalent_for_pin(self):
        state = dict.fromkeys(FIELDS, 'original')
        before = goals('R01', state)
        state['pin'] = 'none'
        self.assertEqual(goals('R01', state), before)

    def test_original_top_depends_on_reference(self):
        state = dict.fromkeys(FIELDS, 'original')
        self.assertNotEqual(goals('R01', state)[1], goals('R02', state)[1])

    def test_goal_contains_target_not_method(self):
        state = dict.fromkeys(FIELDS, 'original')
        state['pin'] = 'blue_circle_left'
        text = prompt(goals('R02', state))
        self.assertIn('blue circular pin', text)
        self.assertNotIn('generic', text)
        self.assertNotIn('action', text)


if __name__ == '__main__':
    unittest.main()
