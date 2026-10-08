"""Compose all S different-input pairs as scientific comparison figures.

No cropping, retouching, score-based selection, or replacement of source images.
"""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    prepared = json.loads((root / 'prepared.json').read_text())
    calls = {r['job']: r for r in json.loads((root / 'calls.json').read_text())['calls']}
    groups = {}
    modes = ['baseline_restore', 'keep_remove']
    for r in prepared['conditions']:
        groups.setdefault((r['person'], r['history'], r['turn']), {})[r['mode']] = r
    different = {k: v for k, v in groups.items() if v[modes[0]]['job'] != v[modes[1]]['job']}
    assert len(different) == 4
    manifests = []
    for person in sorted({k[0] for k in different}):
        keys = sorted(k for k in different if k[0] == person)
        assert len(keys) == 2
        fig, axes = plt.subplots(1, 4, figsize=(12, 5), facecolor='white')
        sources = []
        for j, key in enumerate(keys):
            for i, mode in enumerate(modes):
                row = different[key][mode]
                path = root / calls[row['job']]['folder'] / 'output.png'
                assert sha(path) == calls[row['job']]['sha256']['output.png']
                axes[j * 2 + i].imshow(plt.imread(path))
                axes[j * 2 + i].set_title(f'Turn {key[2]}\n' + ('Baseline' if i == 0 else 'Keep + remove'), fontsize=13)
                axes[j * 2 + i].axis('off')
                sources.append({'condition': row['id'],
                                'source': str(path.relative_to(Path(__file__).resolve().parents[1])),
                                'sha256': sha(path)})
        fig.subplots_adjust(left=.01, right=.99, top=.87, bottom=.02, wspace=.03)
        target = out / f'contract-{person}.png'
        fig.savefig(target, dpi=200, facecolor='white', bbox_inches='tight', pad_inches=.05)
        plt.close(fig)
        manifests.append({'figure': target.name, 'sources': sources, 'sha256': sha(target)})
    (out / 'figure-provenance.json').write_text(json.dumps({'selection': 'all four different-input S pairs',
        'prepared_sha256': sha(root / 'prepared.json'), 'script_sha256': sha(Path(__file__)),
        'figures': manifests}, ensure_ascii=False, indent=2) + '\n')
    print([r['figure'] for r in manifests])


if __name__ == '__main__':
    main()
