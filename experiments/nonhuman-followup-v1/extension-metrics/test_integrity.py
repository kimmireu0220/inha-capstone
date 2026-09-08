"""Check final counts, immutable raw records, exact formula reuse and costs."""
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('extension_analysis',ROOT/'analyze.py')
calc=importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)


class Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=calc.read(ROOT/'results.json')
        cls.m=calc.read(ROOT/'manifest.json')
        cls.g=calc.read(calc.GEN/'progress.json')
        cls.old=calc.read(calc.BASE/'results.json')
        cls.rows=cls.d['rows']
        cls.summary=cls.d['summary']

    def test_sources_and_raw_images_immutable(self):
        self.assertEqual(calc.sha(ROOT/'manifest.json'),self.d['manifest_sha256'])
        for path,digest in {**self.m['source_hashes'],**self.m['image_hashes']}.items():
            self.assertEqual(calc.sha(path),digest,path)

    def test_terminal_collection_is_not_full_design_completion(self):
        self.assertTrue(self.d['analysis_complete'])
        self.assertTrue(self.d['collection_complete'])
        self.assertFalse(self.d['full_design_complete'])
        self.assertTrue(self.g['collection_complete'])
        self.assertFalse(self.g['full_design_complete'])
        self.assertEqual((self.m['new_calls'],self.m['new_failed_calls'],self.m['new_attempted_calls']),(25,1,26))
        self.assertEqual(self.m['planned_new_calls'],27)

    def test_25_first_outputs_and_one_failure_have_exact_inventory(self):
        calls=list((calc.GEN/'generated').glob('*.call.json'))
        self.assertEqual(len(calls),25)
        self.assertEqual({p.name.removesuffix('.call.json') for p in calls},{p.stem for p in (calc.GEN/'generated').glob('*.png')})
        output_hashes=set()
        for path in calls:
            r=calc.read(path)
            self.assertEqual(r['attempt'],1)
            self.assertEqual(r['id'],calc.request_key(r['input'],r['prompt']))
            self.assertEqual(r['output_sha256'],calc.sha(r['output']))
            self.assertEqual(r['input_sha256'],calc.sha(r['input']))
            output_hashes.add(r['output_sha256'])
        self.assertEqual(output_hashes,{self.rows[k]['sha256'] for k in self.m['new_output_ids']})
        failure=calc.read(next((calc.GEN/'failures').glob('*.json')))
        self.assertEqual(failure['stage'],9)
        self.assertFalse(Path(failure['output']).exists())
        self.assertFalse(Path(failure['output']).with_suffix('.call.json').exists())

    def test_metric_union_and_old_rows_unchanged(self):
        self.assertEqual(len(self.rows),113)
        self.assertEqual(len(self.m['auxiliary_reused_ids']),3)
        self.assertEqual(set(self.rows),set(self.old['rows'])|set(self.m['new_output_ids'])|set(self.m['auxiliary_reused_ids']))
        for key,row in self.old['rows'].items(): self.assertEqual(self.rows[key],row)

    def test_exact_imported_formula_and_weights(self):
        self.assertEqual(self.m['formula_sha256'],calc.sha(calc.BASE/'analyze.py'))
        self.assertEqual(calc.mm.measure.__module__,'frozen_pure_metrics')
        old_manifest=calc.read(calc.BASE/'manifest.json')
        self.assertEqual(self.m['lpips_state_dict_sha256'],old_manifest['lpips_state_dict_sha256'])
        self.assertEqual(calc.read(ROOT/'metric-cache.json')['lpips_state_dict_sha256'],old_manifest['lpips_state_dict_sha256'])
        self.assertEqual(calc.mm.SIGMAS,(1,3,6))
        self.assertEqual(calc.mm.RADIUS,64)

    def test_fixed_mae_ssim_and_ncc_reproduced_on_new_p04_image(self):
        key=next(k for k in self.m['new_output_ids'] if 'skin' in self.rows[k])
        r=self.rows[key]
        ref,output=calc.mm.image(r['reference']),calc.mm.image(r['paths'][0])
        for s in (1,3,6): self.assertEqual(calc.mm.locate(output,ref,r['roi'],s),r['locations'][str(s)])
        for mode in ('fixed','1','3','6'):
            loc=(0,0) if mode=='fixed' else (r['locations'][mode]['dx'],r['locations'][mode]['dy'])
            a,b=calc.mm.crop(ref,r['roi']),calc.mm.crop(output,r['roi'],loc)
            self.assertEqual(float(calc.mm.np.mean(calc.mm.np.abs(a-b))),r['face'][mode]['mae'])
            self.assertEqual(calc.mm.ssim(a,b),r['face'][mode]['ssim'])

    def test_20_branches_with_only_198_observed_deliverables(self):
        self.assertEqual(len(self.summary),20)
        self.assertEqual(len(self.d['trajectories']),198)
        self.assertEqual(sum(s['full_ten_stage_complete'] for s in self.summary.values()),19)
        self.assertEqual(len({(r['branch'],r['stage']) for r in self.d['trajectories']}),198)
        self.assertEqual([r['stage'] for r in self.d['trajectories'] if r['branch']=='P05-once-triggered'],list(range(1,9)))

    def test_missing_p05_endpoint_is_not_imputed(self):
        s=self.summary['P05-once-triggered']
        self.assertIsNone(s['final_id'])
        self.assertIsNone(s['logical_calls'])
        self.assertEqual(s['planned_logical_calls'],11)
        self.assertEqual((s['observed_successful_calls'],s['observed_attempted_calls']),(9,10))
        self.assertEqual(s['last_observed_stage'],8)
        for v in s['face'].values():
            self.assertIsNone(v['mean'])
            self.assertIsNone(v['final'])
            self.assertIsInstance(v['observed_mean']['lpips'],float)

    def test_cost_ledgers_and_reset_counts(self):
        expected={'P04-fixed3':13,'P04-triggered':18,'P04-once-triggered':11,'P06-once-triggered':11,'P04-always-original':10}
        for name,cost in expected.items():
            ledger=self.d['call_ledgers'][name]
            self.assertEqual(len(ledger['calls']),cost)
            self.assertEqual(ledger['logical_calls_verified'],cost)
        for name,ledger in self.d['call_ledgers'].items():
            for entry in ledger['calls']:
                self.assertIn(entry['call'],self.d['call_audit'])
                self.assertEqual(entry['stage'],self.d['call_audit'][entry['call']]['stage'])
        partial=self.d['call_ledgers']['P05-once-triggered']
        self.assertEqual(len(partial['calls']),9)
        self.assertEqual(len(partial['failed_call_records']),1)

    def test_end_only_uses_first_nine_plus_rebase_tenth(self):
        for person,direct in self.d['direct_one_shot'].items():
            name=person+'-end-only'
            end=[r for r in self.d['trajectories'] if r['branch']==name]
            base=[r for r in self.d['trajectories'] if r['branch']==person]
            self.assertEqual([r['id'] for r in end[:9]],[r['id'] for r in base[:9]])
            self.assertEqual(end[-1]['id'],direct['final_id'])
            self.assertEqual(self.summary[name]['logical_calls'],11)
            self.assertEqual(direct['logical_calls'],1)
            self.assertIsNone(direct['mean_over_ten_stages'])
            ledger=self.d['call_ledgers'][name]['calls']
            self.assertEqual(len([r for r in ledger if r['stage']==10]),2)
            for mode in ('fixed','1','3','6'):
                expected=sum(self.rows[r['id']]['face'][mode]['lpips'] for r in end)/10
                self.assertAlmostEqual(self.summary[name]['face'][mode]['mean']['lpips'],expected,places=12)

    def test_original_nine_summaries_and_all_source_metrics_reproduced(self):
        for name,s in self.old['summary'].items():
            for mode in ('fixed','1','3','6'):
                for endpoint in ('mean','final'):
                    self.assertEqual(self.summary[name]['face'][mode][endpoint],s['face'][mode][endpoint])
        for branch in self.g['branches']:
            for r in branch['rows']:
                key=calc.row_key(branch['reference'],r['output'])
                for k in ('mae','ssim','lpips'):
                    self.assertLess(abs(self.rows[key]['face']['fixed'][k]-r['metrics'][k]),1e-6)

    def test_shared_outputs_not_independent_runs(self):
        self.assertEqual(self.d['direct_one_shot']['P03-r1']['final_id'],self.d['direct_one_shot']['P03-r2']['final_id'])
        key=self.summary['P04-triggered']['final_id']
        self.assertEqual(self.summary['P04-end-only']['final_id'],key)
        self.assertEqual(self.summary['P04-always-original']['final_id'],key)
        self.assertNotIn(None,self.d['shared_final_outputs'])
        self.assertNotIn('null',self.d['shared_final_outputs'])

    def test_recurrence_observed_after_exactly_one_edit(self):
        for person,stage in [('P04',4),('P05',3),('P06',3)]:
            r=self.d['first_reset_recurrence'][person+'-once-triggered']
            self.assertTrue(r['reset_below_frozen_threshold'])
            self.assertEqual(r['first_later_raw_alarm_stage'],stage)
            self.assertEqual(r['edits_after_reset_until_first_alarm'],1)
        for name,r in self.d['first_reset_recurrence'].items():
            if name.endswith('-end-only'):
                self.assertEqual(r['status'],'no_later_stage')
                self.assertIsNone(r['first_later_raw_alarm_stage'])

    def test_recurrence_no_later_stage_and_no_alarm_are_null(self):
        rows=[{'stage':3,'final_fixed_lpips':.03,'raw_fixed_lpips':.08}]
        r=calc.first_recurrence(rows,3)
        self.assertEqual(r['status'],'no_later_stage')
        self.assertIsNone(r['first_later_raw_alarm_stage'])
        rows.append({'stage':4,'final_fixed_lpips':.04,'raw_fixed_lpips':.04})
        r=calc.first_recurrence(rows,3)
        self.assertEqual(r['status'],'not_observed_in_remaining_stages')
        self.assertIsNone(r['edits_after_reset_until_first_alarm'])

    def test_skin_regions_and_metric_ranges(self):
        for key in self.m['new_output_ids']:
            row=self.rows[key]
            for values in row['face'].values():
                self.assertTrue(0<=values['mae']<=1)
                self.assertTrue(-1<=values['ssim']<=1)
                self.assertTrue(values['lpips']>=0)
            if 'skin' in row:
                self.assertEqual(set(row['skin']['fixed']['regions']),set(calc.mm.REGIONS))

    def test_no_ratings_or_aligned_threshold(self):
        self.assertEqual(self.m['threshold_applied_only_to_fixed_lpips'],.0555075)
        self.assertEqual(self.d['human_evaluation'],'not_read_or_collected')
        self.assertEqual(self.d['independent_agent_evaluation'],'not_read_or_collected')
        self.assertFalse(any('/reviews/' in p or '/agent-agreement/' in p for p in self.m['source_hashes']))


if __name__=='__main__': unittest.main(verbosity=2)
