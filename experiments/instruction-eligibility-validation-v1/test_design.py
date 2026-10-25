import json
import unittest
import run

class DesignTests(unittest.TestCase):
    def test_new_requests_and_reference_schema(self):
        h=json.loads((run.ROOT/'benchmark.json').read_text())['histories']
        self.assertEqual(len(h),4)
        texts=[r['request'] for rows in h.values() for r in rows]
        self.assertEqual(len(texts),16);self.assertEqual(len(set(texts)),16)
        previous=[]
        for study,name in [('operation-scope-validation-v1','benchmark.json'),('instruction-transfer-v1','frozen.json')]:
            old=json.loads((run.ROOT.parent/study/name).read_text())['histories']
            previous += [r['request'] for rows in old.values() for r in rows]
        self.assertFalse(set(texts)&set(previous))
        for rows in h.values():
            for r in rows:
                for field,value in r['updates'].items():self.assertIn(value,run.parent.plain.VALUES[field]+['original'])
        self.assertEqual(h['E3'][1]['updates'],dict(necklace='none'))
        self.assertEqual(h['E3'][3]['updates'],dict(pin='none'))

if __name__=='__main__':unittest.main()
