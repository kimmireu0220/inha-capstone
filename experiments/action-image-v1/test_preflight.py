import unittest
from goals import FIELDS
from preflight import conflicts


class ConflictTest(unittest.TestCase):
    def test_lapel_dependency(self):
        state = dict.fromkeys(FIELDS, 'original')
        self.assertEqual(conflicts('R01', state), [])
        state['pin'] = 'blue_circle_left'
        self.assertEqual(conflicts('R01', state), ['lapel_pin_without_blazer'])
        state['jacket'] = 'green'
        self.assertEqual(conflicts('R01', state), [])
        state['jacket'] = 'none'
        self.assertEqual(conflicts('R01', state), ['lapel_pin_without_blazer'])


if __name__ == '__main__':
    unittest.main()
