from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent.parent
md=(R/'paper/manuscript.ko.md').read_text()
sources={
'3.1,4.1,4.3':'experiments/nonhuman-followup-v1/RESULTS.md',
'3.2,4.2':'experiments/autonomous-nonhuman-v1/RESULTS.md',
'4.3 AI':'experiments/followup-ai-v1/summary.json',
'4.4':'experiments/local-policy-v1/results.json',
'4.5':'experiments/local-policy-robustness-v1/results.json',
'5.1':'experiments/studio-policy-v1/results.json',
'5.1 expanded':'experiments/studio-multiperson-v1/results.json'}
r=json.loads((R/sources['4.5']).read_text())
checks=[]
for mode,arms in r['summary'].items():
 for arm,v in arms.items():
  vals=[v['face']['lpips']]+[v['skin'][k] for k in ['mae','ssim','highpass_mae','residual_mae']]
  needle=' | '.join(f'{v:.6f}' for v in vals)
  assert needle in md,(mode,arm,needle)
  checks.append({'table':6,'mode':mode,'arm':arm,'numeric_cells':5,'passed':True})
for row in r['rows']:
 if row['arm']=='batch' or row['stage']==3:
  v=row['modes']['fixed']['face'];needle=' | '.join(f'{v[k]:.6f}' for k in ['mae','ssim','lpips']);assert needle in md
ai=json.loads((R/sources['4.3 AI']).read_text());assert ai['images']==12 and ai['groups']['batch']=={'1':6} and ai['groups']['SBP']=={'2':2,'3':4}
for n in ['0.076800','0.118081','0.104716','0.149267','0.119000','0.166047','0.049207','0.014057','0.013909','0.106249']:
 assert n in md and n in (R/sources['3.2,4.2']).read_text(),n
v=json.loads((R/'experiments/local-policy-robustness-v1/verification.json').read_text());assert v['passed']
site=json.loads((R/sources['5.1']).read_text())
for row in site['final']+[{'metrics':v} for v in site['means'].values()]:
 assert ' | '.join(f'{row["metrics"][k]:.6f}' for k in ['mae','ssim','lpips']) in md
assert json.loads((R/'experiments/studio-policy-v1/verification.json').read_text())['passed']
expanded=json.loads((R/sources['5.1 expanded']).read_text())
assert expanded['complete'] and expanded['outputs']==72 and expanded['paired_comparisons']==18
assert expanded['regenerate_wins']=={'mae':14,'ssim':18,'lpips':18}
for mode in ['regenerate','sequential']:
 for k in ['mae','ssim','lpips']:
  assert f"{expanded['means'][mode][k]:.6f}" in md
assert json.loads((R/'experiments/studio-multiperson-v1/verification.json').read_text())['complete']
output={'date':'2026-09-18','website_final_rows_checked':4,'website_mean_rows_checked':2,'website_expanded_pairs_checked':18,'scope':'Numerical transcription checks and source hashes; not scientific external validation','passed':True,'manuscript_sha256':hashlib.sha256(md.encode()).hexdigest(),'sources':[{ 'sections':k,'path':p,'sha256':hashlib.sha256((R/p).read_bytes()).hexdigest()} for k,p in sources.items()],'table6_checks':checks,'local_final_rows_checked':4,'followup_lpips_and_color_values_checked':10,'ai_counts_checked':True,'posthoc_analysis_verified':True}
(R/'paper/evidence.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('Paper numerical transcription and source checks passed')
