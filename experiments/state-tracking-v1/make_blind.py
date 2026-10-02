"""Prepare method-masked pairs and an empty independent-human rating form."""
import csv
import hashlib
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent


def main(root=None):
    global ROOT
    if root is not None:
        ROOT = Path(root)
    calls = json.loads((ROOT / 'calls.json').read_text())['calls']
    groups = {}
    for call in calls:
        key = f"{call['person']}-{call['history']}-{call['seed']}"
        groups.setdefault(key, {})[call['mode']] = call
    folder = ROOT / 'blind'
    folder.mkdir(exist_ok=True)
    map_path = ROOT / 'blinding-map.json'
    mapping = json.loads(map_path.read_text()) if map_path.exists() else {}
    for key, pair in sorted(groups.items()):
        if set(pair) != {'agent', 'tracked'}:
            continue
        if key not in mapping:
            modes = ['agent', 'tracked']
            rng = random.Random(int(hashlib.sha256(('mask-20261003-' + key).encode()).hexdigest(), 16))
            rng.shuffle(modes)
            mapping[key] = dict(zip('AB', modes))
        source = ROOT / 'references' / f'{key.split("-")[0]}.png'
        panels = [('ORIGINAL', source)] + [(letter, ROOT / pair[mapping[key][letter]]['folder'] / 'output.png')
                                          for letter in 'AB']
        canvas = Image.new('RGB', (1536, 806), 'white')
        draw = ImageDraw.Draw(canvas)
        for index, (letter, path) in enumerate(panels):
            with Image.open(path) as photo:
                image = photo.convert('RGB')
                image.thumbnail((512, 768))
            canvas.paste(image, (index * 512 + (512 - image.width) // 2,
                                38 + (768 - image.height) // 2))
            draw.text((index * 512 + 12, 12), f'{key} / {letter}', fill='black')
        canvas.save(folder / f'{key}.png')
    map_path.write_text(json.dumps(mapping, indent=2) + '\n')
    form = ROOT / 'human-ratings.csv'
    # Preserve any ratings already entered by a human.
    existing = {}
    if form.exists():
        with form.open(newline='') as handle:
            existing = {(r['comparison'], r['label']): r for r in csv.DictReader(handle)}
    columns = ['comparison', 'label', 'goal_1', 'goal_2', 'goal_3', 'goal_4',
               'goal_5', 'goal_6', 'note', 'rater_id']
    with form.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for key in sorted(mapping):
            for label in 'AB':
                writer.writerow(existing.get((key, label), {'comparison': key, 'label': label}))
    print(f'Prepared {len(mapping)} masked pairs. Human form contains no automated scores.')


if __name__ == '__main__':
    main()
