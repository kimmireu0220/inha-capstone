"""Post-run integrity regressions; original pre-inference tests remain frozen."""
import json
from pathlib import Path
import unittest
import run

ROOT = Path(__file__).resolve().parent


class EvidenceTests(unittest.TestCase):
    def test_gold_removal_persists(self):
        data = json.loads((ROOT / 'benchmark.json').read_text())
        for n in range(1, 5):
            gold = dict(run.INITIAL)
            for i, turn in enumerate(data[f'C{n}-mixed'], 1):
                gold.update(turn['updates'])
                if i >= 2:
                    self.assertEqual(gold['prop'], 'none')
                if i >= 3:
                    self.assertEqual(gold['necklace'], 'none')
                if i == 4:
                    self.assertEqual(gold['background'], 'original')
                    self.assertEqual(gold['jacket'], 'original')

    def test_recompute(self):
        data = json.loads((ROOT / 'benchmark.json').read_text())
        records = json.loads((ROOT / 'transcripts.json').read_text())
        expected = json.loads((ROOT / 'results.json').read_text())
        self.assertEqual(run.score(data, records), expected['methods'])
        self.assertEqual(len(records), 48)

    def test_invalid_response_falls_back_without_gold(self):
        data = {'C1-mixed': [{'request': 'Remove the plant.', 'updates': {'prop': 'none'}}]}
        records = {'C1-mixed-1': {'request': 'Remove the plant.', 'first': '{"prop":"plant"}',
                                 'second': '{"prop":"not_allowed"}'}}
        scores = run.score(data, records)
        self.assertEqual(scores['review']['rows'][0]['observed']['prop'], 'plant')
        self.assertEqual(scores['guarded']['rows'][0]['observed']['prop'], 'none')
        self.assertFalse(scores['review']['rows'][0]['exact'])
        self.assertTrue(scores['guarded']['rows'][0]['exact'])

    def test_failed_image_judgments_retained(self):
        ratings = json.loads((ROOT / 'image-ratings.json').read_text())['ratings']
        self.assertEqual(len(ratings), 6)
        for person in ['R01', 'R02']:
            self.assertEqual(ratings[person + '-single']['scores'], [None])
            self.assertIsNotNone(ratings[person + '-single']['parse_error'])
            self.assertTrue(ratings[person + '-single']['raw'])


if __name__ == '__main__':
    unittest.main()
