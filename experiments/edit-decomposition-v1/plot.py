"""Scientific metric trajectories; lines describe two paths, not confidence intervals."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
COLORS = {'batch': '#3676c6', 'sequential': '#c86526', 'no_change': '#507a64'}
LABELS = {'batch': 'Batch: 1 call', 'sequential': 'Sequential: 3 calls', 'no_change': 'No-change: 3 calls'}


def main():
    rows = json.loads((ROOT / 'results.json').read_text())['rows']
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.hashsalt': 'edit-decomposition-v1'})
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.2), sharex=True, sharey='col')
    for row_index, mode in enumerate(('fixed', '3')):
        for col, metric in enumerate(('mae', 'ssim', 'lpips')):
            ax = axes[row_index, col]
            for arm, color in COLORS.items():
                values = []
                for rep in (1, 2):
                    selected = sorted([r for r in rows if r['arm'] == arm and r['repeat'] == rep],
                                      key=lambda r: r['stage'])
                    x = [0] + [r['stage'] for r in selected]
                    y = [1 if metric == 'ssim' else 0] + [r['original']['face'][mode][metric] for r in selected]
                    values.append(y)
                    ax.plot(x, y, color=color, alpha=.38, linewidth=1, linestyle='--', marker='.', markersize=5)
                ax.plot(x, np.mean(values, axis=0), color=color, linewidth=2, marker='o', markersize=5,
                        label=LABELS[arm])
            if row_index == 0:
                ax.set_title({'mae': 'MAE (lower = closer)', 'ssim': 'SSIM (higher = closer)',
                              'lpips': 'LPIPS (lower = closer)'}[metric], pad=10)
            else:
                ax.set_xlabel('Generation calls (0 = original)')
            if col == 0:
                ax.set_ylabel('Fixed ROI' if mode == 'fixed' else 'NCC-aligned ROI, sigma = 3')
            ax.set_xticks([0, 1, 2, 3])
            ax.grid(alpha=.15)
    axes[0, 0].legend(loc='upper left', fontsize=8, frameon=False)
    fig.suptitle('Distance from the original face region\nOne synthetic portrait; two paths per condition', y=.98, fontsize=15)
    fig.text(.5, .015, 'Solid = mean; dashed = individual paths. Batch ends after one call. These are image distances, not severity ratings.',
             ha='center', fontsize=9)
    fig.tight_layout(rect=[0, .035, 1, .91])
    for ext in ('png', 'svg', 'pdf'):
        fig.savefig(ROOT / f'trajectories.{ext}', dpi=180, metadata={'Creator': 'edit-decomposition-v1'})
    plt.close(fig)


if __name__ == '__main__':
    main()
