"""Check comparison pairing and gold-state validity before reading outcomes."""
import unittest
import run

class DesignTests(unittest.TestCase):
    def test_paired_goals_and_valid_states(self):
        histories=run.benchmark()
        self.assertEqual(len(histories),12)
        self.assertEqual(sum(map(len,histories.values())),48)
        for config in run.CONFIGS:
            reference=None
            for form in run.FORMS:
                state=dict(run.plain.INITIAL)
                states=[]
                for item in histories[config['name']+'__'+form]:
                    for field,value in item['updates'].items():
                        self.assertIn(field,run.plain.VALUES)
                        self.assertIn(value,run.plain.VALUES[field]+['original'])
                    state.update(item['updates'])
                    states.append(dict(state))
                if reference is None:reference=states
                self.assertEqual(states,reference)
                self.assertEqual(states[2][config['field']],'none')

    def test_inference_manifest(self):
        import json,hashlib
        frozen=json.loads((run.ROOT/'frozen.json').read_text())
        self.assertEqual(frozen['histories'],run.benchmark())
        for path,digest in frozen['sha256'].items():
            self.assertEqual(hashlib.sha256((run.REPO/path).read_bytes()).hexdigest(),digest,path)

    def test_repeated_requests_are_identified(self):
        from collections import Counter
        counts=Counter(item['request'] for requests in run.benchmark().values() for item in requests)
        self.assertEqual(len(counts),32)
        self.assertEqual(sum(n>1 for n in counts.values()),8)
        self.assertTrue(all(n in [1,3] for n in counts.values()))

if __name__=='__main__':unittest.main()
