from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
p=Path(__file__).resolve().parent
r=json.load(open(p.parent/'experiments/local-policy-robustness-v1/results.json'))
f,axes=plt.subplots(1,2,figsize=(9,3.1),sharey=True)
sets=[(['P04','P05','P06'],[.076800,.104716,.119000],[.118081,.149267,.166047],'A. Original generator (means of two runs)'),(['42','314'],[next(x for x in r['rows'] if x['arm']=='batch' and x['seed']==s)['modes']['fixed']['face']['lpips'] for s in [42,314]],[next(x for x in r['rows'] if x['arm']=='sequential' and x['seed']==s and x['stage']==3)['modes']['fixed']['face']['lpips'] for s in [42,314]],'B. FLUX.2 Klein 4B (P04, individual seeds)')]
for ax,(labels,b,s,title) in zip(axes,sets):
 x=np.arange(len(labels));ax.bar(x-.17,b,.34,label='Batch',color='#326ba0');ax.bar(x+.17,s,.34,label='Sequential',color='#bd753e');ax.set_xticks(x,labels);ax.set_title(title,fontsize=10);ax.set_ylim(0,.19);ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
axes[0].set_ylabel('Fixed-face LPIPS (lower = closer)');axes[1].legend(frameon=False,fontsize=9);f.tight_layout();f.savefig(p/'figures/policy-comparison.png',dpi=220);f.savefig(p/'figures/policy-comparison.pdf');plt.close(f)
