"""Draw the implemented request-state update for the paper at print size."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

ROOT = Path(__file__).resolve().parent


def main():
    fig, ax = plt.subplots(figsize=(6.6, 2.5))
    fig.subplots_adjust(left=0.015, right=0.985, top=0.98, bottom=0.02)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    centers = {'request': (.14, .77), 'model': (.50, .77), 'patch': (.86, .77),
               'before': (.14, .28), 'update': (.50, .28), 'after': (.86, .28)}
    labels = {'request': 'New request', 'model': 'Qwen3 4B\nExtract changes',
              'patch': 'JSON patch', 'before': 'Previous state\n6 slots',
              'update': 'Validate and apply\nCode', 'after': 'Updated state\n6 slots'}
    for name, (x, y) in centers.items():
        ax.add_patch(Rectangle((x - .13, y - .15), .26, .30,
                               facecolor='#f5f5f5', edgecolor='#333333', linewidth=.8))
        ax.text(x, y, labels[name], ha='center', va='center', fontsize=10,
                fontfamily='DejaVu Sans', linespacing=1.5)
    for start, end in [('request', 'model'), ('model', 'patch'),
                       ('before', 'update'), ('update', 'after')]:
        x1, y1 = centers[start]
        x2, y2 = centers[end]
        ax.add_patch(FancyArrowPatch((x1 + .13, y1), (x2 - .13, y2),
                     arrowstyle='-|>', mutation_scale=10, linewidth=.9, color='#333333'))
    ax.add_patch(FancyArrowPatch((.86, .62), (.50, .43),
                 connectionstyle='arc3,rad=0',
                 arrowstyle='-|>', mutation_scale=10, linewidth=.9, color='#333333'))
    folder = ROOT / 'figures'
    folder.mkdir(exist_ok=True)
    for extension in ['png', 'svg']:
        fig.savefig(folder / f'state-update.{extension}', dpi=300, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
