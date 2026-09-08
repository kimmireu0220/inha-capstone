"""Scientific plots from recorded scores, not generated/edit-modified portraits."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
def read(n):return json.loads((ROOT/n).read_text())
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
signal=read('joined-reviews/signal-transfer.json')['groups']
fig,axes=plt.subplots(1,2,figsize=(10,4.3),sharex=True,sharey=True,layout='constrained')
for ax,reviewer in zip(axes,'ab'):
    for group,label,color,marker in [('sequential_final_7','Sequential finals (7 paths)','#ba422f','o'),('original_based_final_unique_6','Original-based finals (6 unique)','#225ec4','s')]:
        rows=signal[group]['observations'];ax.scatter([x['fixed']['lpips'] for x in rows],[x['grades'][reviewer] for x in rows],label=label,c=color,marker=marker,s=48,alpha=.85,edgecolors='white',linewidths=.6,zorder=3)
    ax.axvline(.0555075,color='#444444',ls='--',lw=1,label='Frozen LPIPS alarm')
    ax.axhline(1.5,color='#bbbbbb',ls=':',lw=1)
    ax.set(title=f'Independent AI session {reviewer.upper()}',xlabel='Fixed face-ROI LPIPS (larger = more difference)',xlim=(0,.61),ylim=(-.3,3.3))
    ax.set_yticks(range(4),['None','Mild','Clear','Severe']);ax.grid(axis='y',alpha=.15)
axes[0].set_ylabel('Observed artificial facial patterns')
handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3,frameon=False,fontsize=8)
fig.savefig(OUT/'final-signal-vs-artificiality.png',dpi=180);fig.savefig(OUT/'final-signal-vs-artificiality.svg');plt.close(fig)
data=read('extension-metrics/results.json')
fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
policies=[('P04','Sequential, 10 calls','#8a8a8a','-'),('P04-once-triggered','One early reset, 11 calls','#ba422f','-'),('P04-triggered','Reset on alarm, 18 calls','#8a48a6','--'),('P04-always-original','Always original, 10 calls','#225ec4',':')]
for ax,mode,title in zip(axes,['fixed','3'],['Fixed face ROI','Translation-aligned face ROI']):
    for name,label,color,ls in policies:
        rows=[t for t in data['trajectories'] if t['branch']==name]
        # Trajectory records retain final image IDs, so plotted values are exact registry lookups.
        y=[data['rows'][r['id']]['face'][mode]['lpips'] for r in rows]
        ax.plot([r['stage'] for r in rows],y,label=label,color=color,ls=ls,lw=2,marker='.' if name=='P04-always-original' else None)
    if mode=='fixed':ax.axhline(.0555075,color='#444',lw=.8,ls='--')
    ax.set(title=title,xlabel='Editing stage',ylabel='LPIPS (larger = more difference)',xticks=range(1,11),ylim=(0,.60));ax.grid(alpha=.15)
handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=2,frameon=False,fontsize=9)
fig.savefig(OUT/'p04-policy-trajectories.png',dpi=180);fig.savefig(OUT/'p04-policy-trajectories.svg');plt.close(fig)
print(str(OUT))
