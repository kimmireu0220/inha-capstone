import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parent
class Design(unittest.TestCase):
 def test_full_cross_product_and_no_answer_leak(self):
  d=json.loads((R/'prepared.json').read_text());rows=d['conditions']
  self.assertEqual(len(rows),18)
  self.assertEqual({(r['person'],r['history'],r['mode']) for r in rows},{(p,h,m) for p in ['R01','R02'] for h in ['S1','S2','S3'] for m in ['full_history','unchecked_state','checked_state']})
  self.assertTrue(all(r['turn']==4 for r in rows));self.assertEqual(len(d['lengths']),12)
  for h in ['S1','S2','S3']:
   raw=next(r for r in rows if r['history']==h and r['mode']=='full_history')['prompt']
   self.assertEqual(raw.count('Request '),4)
   self.assertNotIn('expected_state',raw)
 def test_renderer_is_shared(self):
  rows=json.loads((R/'prepared.json').read_text())['conditions']
  for r in rows:
   if r['mode']=='full_history':continue
   self.assertIn('Apply these final current requirements',r['prompt'])
   other=next(x for x in rows if x['history']==r['history'] and x['mode']==r['mode'] and x['person']!=r['person'])
   self.assertEqual(r['prompt'],other['prompt'])
if __name__=='__main__':unittest.main()
