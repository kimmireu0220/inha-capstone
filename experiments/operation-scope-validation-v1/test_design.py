import json
import unittest
import run

class DesignTests(unittest.TestCase):
    def test_distinct_requests_and_schema(self):
        data=json.loads((run.ROOT/'benchmark.json').read_text())
        histories=data['histories']
        self.assertEqual(len(histories),8)
        texts=[r['request'] for rows in histories.values() for r in rows]
        self.assertEqual(len(texts),32);self.assertEqual(len(set(texts)),32)
        previous=run.ROOT.parent/'instruction-transfer-v1/frozen.json'
        old=json.loads(previous.read_text())['histories']
        self.assertFalse(set(texts)&{r['request'] for rows in old.values() for r in rows})
        for rows in histories.values():
            self.assertEqual(len(rows),4)
            for item in rows:
                for field,value in item['updates'].items():
                    self.assertIn(value,run.plain.VALUES[field]+['original'])
        self.assertEqual(histories['G1'][1]['updates'],{})
        self.assertEqual(histories['G1'][2]['updates'],{})
        self.assertEqual(histories['G2'][1]['updates'],{})
        self.assertEqual(histories['G2'][2]['updates'],{})

if __name__=='__main__':unittest.main()
