import unittest
from evaluate import parse


class ParseTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse('{"scores":[1,0,null,1,0,1]}'), ([1, 0, None, 1, 0, 1], None))

    def test_invalid_not_passed(self):
        for raw in ['{"scores":[true,1,1,1,1,1]}', '{"scores":[1,1]}', 'broken']:
            values, error = parse(raw)
            self.assertEqual(values, [None] * 6)
            self.assertIsNotNone(error)


if __name__ == '__main__':
    unittest.main()
