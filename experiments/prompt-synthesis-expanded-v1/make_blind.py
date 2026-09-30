"""Create blinded three-way sheets for completed comparison sets during generation."""
import json
import random
from pathlib import Path

from analyze import make_sheet, save

ROOT = Path(__file__).resolve().parent
MODES = ['history', 'state', 'agent']


def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    calls = json.loads((ROOT / 'calls.json').read_text())['calls']
    map_path = ROOT / 'blinding-map.json'
    if map_path.exists():
        mapping = json.loads(map_path.read_text())
    else:
        rng = random.Random(18291)
        mapping = {}
        for person in plan['people_order']:
            for history in plan['history_order']:
                for seed in plan['seeds']:
                    modes = list(MODES)
                    rng.shuffle(modes)
                    mapping[f'{person}-{history}-{seed}'] = dict(zip('ABC', modes))
        save(map_path, mapping)
    made = 0
    for key, labels in mapping.items():
        person, history, seed_text = key.split('-')
        seed = int(seed_text)
        options = {c['mode']: ROOT / c['folder'] / 'output.png' for c in calls
            if (c['person'], c['history'], c['seed']) == (person, history, seed)}
        if set(options) != set(MODES):
            continue
        sheet = ROOT / 'blind' / f'{key}.png'
        if not sheet.exists():
            make_sheet(person, history, seed, options, labels)
            made += 1
    print(f'Created {made} new sheets; {len(list((ROOT / "blind").glob("*.png")))} total')


if __name__ == '__main__':
    main()
