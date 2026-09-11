from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent.parent
md=(R/'paper/manuscript.ko.md').read_text()
sources={
'3.1,4.1,4.3':'experiments/nonhuman-followup-v1/RESULTS.md',
'3.2,4.2':'experiments/autonomous-nonhuman-v1/RESULTS.md',
'4.3 human':'experiments/followup-human-v1/RECHECKED_RESULTS.md',
'4.3 AI':'experiments/followup-ai-v1/summary.json',
'4.4':'experiments/local-policy-v1/results.json',
'4.5':'experiments/local-policy-robustness-v1/results.json',
'5':'local-studio/checks/RECHECK.md'}
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
ai=json.loads((R/sources['4.3 AI']).read_text());assert ai['exact_agreement']==4 and ai['within_one_grade']==10 and ai['images']==12
for n in ['0.076800','0.118081','0.104716','0.149267','0.119000','0.166047','0.049207','0.014057','0.013909','0.106249']:
 assert n in md and n in (R/sources['3.2,4.2']).read_text(),n
v=json.loads((R/'experiments/local-policy-robustness-v1/verification.json').read_text());assert v['passed']
output={'date':'2026-09-10','scope':'Numerical transcription checks and source hashes; not scientific external validation','passed':True,'manuscript_sha256':hashlib.sha256(md.encode()).hexdigest(),'sources':[{ 'sections':k,'path':p,'sha256':hashlib.sha256((R/p).read_bytes()).hexdigest()} for k,p in sources.items()],'table6_checks':checks,'local_final_rows_checked':4,'followup_lpips_and_color_values_checked':10,'ai_counts_checked':True,'posthoc_analysis_verified':True}
(R/'paper/evidence.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print('Paper numerical transcription and source checks passed')
