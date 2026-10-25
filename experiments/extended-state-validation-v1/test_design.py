import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


class DesignTests(unittest.TestCase):
    def test_balanced_unique_labels_and_prior_benchmark_overlap(self):
        data = json.loads((ROOT/'benchmark.json').read_text())
        spec = importlib.util.spec_from_file_location('state_schema', ROOT.parents[1]/'local-studio/request_state.py')
        schema = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema)
        requests = []
        categories = {}
        for items in data['histories'].values():
            self.assertEqual(len(items), 8)
            self.assertEqual(set(items[0]['updates']), set(schema.INITIAL))
            self.assertEqual(len(set(i['category'] for i in items)), 8)
            for item in items:
                requests.append(item['request'])
                categories[item['category']] = categories.get(item['category'], 0)+1
                for k, v in item['updates'].items():
                    self.assertIn(v, schema.VALUES[k]+['original'])
        self.assertEqual(len(requests), 96)
        self.assertEqual(len(set(requests)), 96)
        self.assertEqual(set(categories.values()), {12})
        self.assertFalse(set(requests).intersection(r for r, _ in schema.EXAMPLES))
        old = set()
        def collect(value):
            if isinstance(value, dict):
                if isinstance(value.get('request'), str):
                    old.add(value['request'])
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
        for path in ROOT.parent.glob('*/benchmark.json'):
            if path.parent != ROOT:
                collect(json.loads(path.read_text()))
        self.assertFalse(set(requests).intersection(old))


if __name__ == '__main__':
    unittest.main()
