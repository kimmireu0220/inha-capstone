import json
import unittest
import run

class DesignTests(unittest.TestCase):
    def test_new_distinct_requests(self):
        h=json.loads((run.ROOT/'benchmark.json').read_text())['histories']
        self.assertEqual(len(h),3)
        texts=[r['request'] for rows in h.values() for r in rows]
        self.assertEqual(len(texts),12);self.assertEqual(len(set(texts)),12)
        previous=[]
        for study,name in [('instruction-transfer-v1','frozen.json'),('operation-scope-validation-v1','benchmark.json'),('instruction-eligibility-validation-v1','benchmark.json')]:
            old=json.loads((run.ROOT.parent/study/name).read_text())['histories']
            previous += [r['request'] for rows in old.values() for r in rows]
        self.assertFalse(set(texts)&set(previous))
        for rows in h.values():
            for r in rows:
                for field,value in r['updates'].items():self.assertIn(value,run.parent.parent.plain.VALUES[field]+['original'])

if __name__=='__main__':unittest.main()
