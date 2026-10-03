"""Mask three methods; link identical images to their existing AI ratings.

Run only after the source primary evaluation and the 48-condition control end.
pending-ratings.json contains labels needing new judgments, never prior scores.
"""
import json
import random
import hashlib
from PIL import Image, ImageDraw
from prepare import ROOT, SOURCE, save, sha


def main():
    source_calls = json.loads((SOURCE / 'calls.json').read_text())['calls']
    control_calls = json.loads((ROOT / 'calls.json').read_text())['calls']
    source_map = json.loads((SOURCE / 'blinding-map.json').read_text())
    source_ratings = json.loads((SOURCE / 'ai-ratings.json').read_text())
    assert len(source_calls) == 96 and len(control_calls) == 48
    assert len(source_map) == 48 and set(source_ratings['ratings']) == set(source_map)
    groups = {}
    for root, calls in [(SOURCE, source_calls), (ROOT, control_calls)]:
        for row in calls:
            key = f"{row['person']}-{row['history']}-{row['seed']}"
            path = root / row['folder'] / 'output.png'
            assert sha(path) == row['output_sha256']
            groups.setdefault(key, {})[row['mode']] = (path, row)
    assert len(groups) == 48
    folder = ROOT / 'blind'
    folder.mkdir(exist_ok=True)
    mapping, linked, pending = {}, {}, {}
    for key, conditions in sorted(groups.items()):
        assert set(conditions) == {'agent', 'tracked', 'structured'}
        modes = sorted(conditions)
        random.Random(int(hashlib.sha256(('control-mask-20261003-' + key).encode()).hexdigest(), 16)).shuffle(modes)
        mapping[key] = dict(zip('ABC', modes))
        source = SOURCE / 'references' / (key.split('-')[0] + '.png')
        panels = [('ORIGINAL', source)] + [(label, conditions[mode][0]) for label, mode in mapping[key].items()]
        canvas = Image.new('RGB', (2048, 806), 'white')
        draw = ImageDraw.Draw(canvas)
        for index, (label, path) in enumerate(panels):
            with Image.open(path) as image:
                image = image.convert('RGB')
                image.thumbnail((512, 768))
            canvas.paste(image, (index * 512 + (512 - image.width) // 2, 38 + (768 - image.height) // 2))
            draw.text((index * 512 + 12, 12), f'{key} / {label}', fill='black')
        for boundary in (512, 1024, 1536):
            draw.line((boundary, 0, boundary, 805), fill='#555555', width=2)
        canvas.save(folder / (key + '.png'))
        for label, mode in mapping[key].items():
            digest = conditions[mode][1]['output_sha256']
            # Match within the same person/history/seed, never by scores.
            matches = [old_label for old_label, old_mode in source_map[key].items()
                       if conditions[old_mode][1]['output_sha256'] == digest]
            rating_key = key + '/' + label
            if matches:
                old_label = sorted(matches)[0]
                linked[rating_key] = {'source_comparison': key, 'source_label': old_label,
                                     'output_sha256': digest}
            else:
                pending[rating_key] = {'history': key.split('-')[1], 'output_sha256': digest}
    frozen = ROOT / 'blinding-map.json'
    if frozen.exists():
        assert json.loads(frozen.read_text()) == mapping
    else:
        save(frozen, mapping)
    save(ROOT / 'linked-ratings.json', linked)
    save(ROOT / 'pending-ratings.json', pending)
    print(f'{len(groups)} three-method panels; {len(linked)} linked ratings, {len(pending)} new ratings needed')


if __name__ == '__main__':
    main()
