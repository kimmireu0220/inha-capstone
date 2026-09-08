"""Read-only regression tests for the saved experiment and diagnostics."""
import hashlib
import json
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent
P=ROOT.parent
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=read(ROOT/'results.json')
        cls.alignment=read(P/'alignment-diagnostic/results.json')
        cls.progress=read(P/'progress.json')
        cls.audit=read(P/'audit.json')

    def test_sources_unchanged(self):
        for path,digest in self.data['source_hashes'].items(): self.assertEqual(sha(path),digest,path)

    def test_all_source_images_unchanged(self):
        for path,row in self.audit['records'].items(): self.assertEqual(sha(path),row['sha256'],path)

    def test_all_29_outputs_included(self):
        self.assertEqual(len(self.data['rows']),29)
        self.assertEqual(set(self.data['rows']),set(self.audit['records']))

    def test_original_threshold_unchanged(self):
        config=read(P.parent/'trigger-validation-v1/config.json')
        self.assertEqual(config['thresholds'],dict(mae=.0288375,ssim=.842874,lpips=.0555075))

    def test_policy_counts_unchanged(self):
        for name,count in [('sequential',0),('fixed3',3),('triggered',8)]:
            rows=self.progress['policies'][name]
            self.assertEqual(len(rows),10)
            self.assertEqual(sum(r['rebased'] for r in rows),count)

    def test_no_missing_or_extra_generated_images(self):
        pngs={p.stem for p in (P/'generated').glob('*.png')}
        records={p.name.removesuffix('.call.json') for p in (P/'generated').glob('*.call.json')}
        self.assertEqual(pngs,records)
        self.assertEqual(len(pngs),18)

    def test_primary_registration_matches_previous(self):
        for path,row in self.data['rows'].items():
            for key in ['dx','dy']: self.assertEqual(row['locations']['3'][key],self.alignment['rows'][path][key])

    def test_all_regions_inside_images(self):
        for path,row in self.data['rows'].items():
            with Image.open(path) as im:
                w,h=im.size
            for loc in row['locations'].values():
                for x0,y0,x1,y1 in self.data['regions'].values():
                    self.assertTrue(0<=x0+loc['dx']<x1+loc['dx']<=w)
                    self.assertTrue(0<=y0+loc['dy']<y1+loc['dy']<=h)

    def test_metric_ranges(self):
        for row in self.data['rows'].values():
            for m in [row['fixed'],*row['aligned'].values()]:
                self.assertTrue(0<=m['mae']<=1)
                self.assertTrue(-1<=m['ssim']<=1)
                self.assertTrue(0<=m['highpass_mae']<=2)

    def test_control_count(self): self.assertEqual(len(self.data['controls']),11)

    def test_known_translation_and_background_invariance(self):
        for c in self.data['controls']:
            if c['name'] in ['identity','distant_surround_replacement'] or c['name'].startswith('translation_'):
                self.assertEqual(c['aligned']['mae'],0)
                self.assertEqual(c['aligned']['ssim'],1)
                self.assertLess(c['aligned']['highpass_mae'],1e-7)

    def test_added_wave_response_monotonic(self):
        waves=[c for c in self.data['controls'] if c['name'].startswith('added_skin_wave_')]
        for key in ['mae','highpass_mae']:
            values=[c['aligned'][key] for c in waves]
            self.assertTrue(values[0]<values[1]<values[2])

    def test_mean_uses_ten_stages_not_unique_images(self):
        for policy,stages in self.progress['policies'].items():
            for sig in ['1','3','6']:
                for metric in ['mae','ssim','highpass_mae']:
                    expected=sum(self.data['rows'][s['final']['path']]['aligned'][sig][metric] for s in stages)/10
                    self.assertAlmostEqual(expected,self.data['summary'][policy][sig]['mean'][metric],places=12)

    def test_no_fabricated_ratings(self):
        self.assertEqual(self.data['human_evaluation'],'not_collected')
        self.assertEqual(self.data['independent_agent_evaluation'],'not_collected')
        self.assertTrue(self.data['diagnostic_only'])

if __name__=='__main__': unittest.main(verbosity=2)
