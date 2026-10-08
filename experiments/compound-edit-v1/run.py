"""Frozen paired complexity probe; never modifies prior experiments."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
MODEL = 'mlx-community/Qwen3-4B-4bit'
REVISION = '4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25'
VALUES = {
    'jacket': ['original', 'none', 'navy', 'beige'],
    'shirt': ['original', 'white', 'gray'],
    'pin': ['original', 'none', 'silver'],
    'necklace': ['original', 'none', 'gold'],
    'background': ['original', 'blue', 'gray'],
    'prop': ['original', 'none', 'plant'],
    'body_direction': ['original', 'left', 'right', 'front'],
    'hand_pose': ['original', 'right_hand_raised', 'left_hand_raised', 'hands_down'],
    'expression': ['original', 'closed_mouth_smile', 'neutral', 'surprised'],
}
INITIAL = dict.fromkeys(VALUES, 'original')
ALIASES = {'jacket': 'jacket', 'shirt': 'shirt', 'pin': 'pin', 'necklace': 'necklace',
           'background': 'background', 'plant': 'prop', 'prop': 'prop',
           'body direction': 'body_direction', 'hand pose': 'hand_pose', 'expression': 'expression'}
SYSTEM = ('Extract a flat JSON patch for a portrait editor. Output only changed fields. '
          'Keep/unchanged means omit the field, never original. Restore means original. '
          'Remove means none only for jacket, pin, necklace, prop. '
          'Body left/right is from the person\'s perspective. '
          'Return only JSON, no explanation. Allowed fields and values: ' + json.dumps(VALUES))
EXAMPLES = [
    ('Make the shirt white and add a silver pin.', {'shirt': 'white', 'pin': 'silver'}),
    ('Restore the necklace to the original. Keep the jacket unchanged.', {'necklace': 'original'}),
]


def save(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def benchmark():
    result = {}
    expressions = [('closed_mouth_smile', 'neutral'), ('surprised', 'closed_mouth_smile'),
                   ('neutral', 'surprised'), ('closed_mouth_smile', 'surprised')]
    phrasing = {'closed_mouth_smile': 'a closed-mouth smile', 'neutral': 'a neutral expression',
                'surprised': 'a surprised expression'}
    for n, (first, second) in enumerate(expressions, 1):
        side = 'left' if n % 2 else 'right'
        other = 'right' if side == 'left' else 'left'
        hand = f'{other}_hand_raised'
        for level in ['single', 'compound', 'mixed']:
            requests = [f'Change the expression to {phrasing[first]}.',
                        f'Change the expression to {phrasing[second]}.',
                        'Restore the expression to the original.',
                        f'Change the expression to {phrasing[first]}.']
            updates = [{'expression': first}, {'expression': second},
                       {'expression': 'original'}, {'expression': first}]
            if level != 'single':
                extra = [f'Turn the body to the {side} and raise the {other} hand.',
                         'Face forward and lower both hands.',
                         'Keep the body direction and hand pose unchanged.',
                         f'Turn the body to the {other}. Keep the hand pose unchanged.']
                changes = [{'body_direction': side, 'hand_pose': hand},
                           {'body_direction': 'front', 'hand_pose': 'hands_down'}, {},
                           {'body_direction': other}]
                for i in range(4):
                    requests[i] += ' ' + extra[i]
                    updates[i].update(changes[i])
            if level == 'mixed':
                extra = ['Set the jacket to navy and the background to blue. Add a plant.',
                         'Keep the jacket and background unchanged. Remove the plant.',
                         'Restore the jacket to the original. Keep the background unchanged. Remove the necklace.',
                         'Keep the jacket and necklace unchanged. Restore the background to the original.']
                changes = [{'jacket': 'navy', 'background': 'blue', 'prop': 'plant'},
                           {'prop': 'none'}, {'jacket': 'original', 'necklace': 'none'},
                           {'background': 'original'}]
                for i in range(4):
                    requests[i] += ' ' + extra[i]
                    updates[i].update(changes[i])
            result[f'C{n}-{level}'] = [dict(request=r, updates=u) for r, u in zip(requests, updates)]
    return result


def parse(raw):
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError('duplicate key')
            obj[k] = v
        return obj
    obj = json.loads(raw[raw.find('{'):raw.rfind('}') + 1], object_pairs_hook=unique)
    if not isinstance(obj, dict) or any(k not in VALUES or v not in VALUES[k] for k, v in obj.items()):
        raise ValueError('invalid schema')
    return obj


def guard(state, prior, request):
    state, events = dict(state), []
    for clause in request.split('.'):
        clause = clause.strip().lower()
        match = re.fullmatch(r'(keep|remove|restore) (.+?)( unchanged| to the original)?', clause)
        if not match:
            continue
        action, body, suffix = match.groups()
        if action == 'keep' and suffix != ' unchanged':
            continue
        if action == 'restore' and suffix != ' to the original':
            continue
        if action == 'remove' and suffix:
            continue
        names = [re.sub(r'^the ', '', x.strip()) for x in body.split(' and ')]
        if any(name not in ALIASES for name in names):
            continue
        for name in names:
            field = ALIASES[name]
            # Avoid overriding a subsequent instruction for the same field.
            remaining = request.lower().split(clause, 1)[-1]
            if any(alias in remaining for alias, key in ALIASES.items() if key == field):
                continue
            if action == 'remove' and 'none' not in VALUES[field]:
                continue
            value = prior[field] if action == 'keep' else ('none' if action == 'remove' else 'original')
            state[field] = value
            events.append(dict(field=field, action=action, evidence=clause))
    return state, events


def score(data, records):
    results = {}
    for mode in ['direct', 'review', 'guarded']:
        rows = []
        for dialogue, turns in data.items():
            state, gold = dict(INITIAL), dict(INITIAL)
            for i, turn in enumerate(turns, 1):
                prior, old_gold = dict(state), dict(gold)
                record = records[f'{dialogue}-{i}']
                assert record['request'] == turn['request']
                candidates = [record['first']] if mode == 'direct' else [record['second'], record['first']]
                errors, selected = [], None
                for raw in candidates:
                    try:
                        state.update(parse(raw))
                        selected = raw
                        break
                    except (ValueError, TypeError) as error:
                        errors.append(str(error))
                events = []
                if mode == 'guarded':
                    state, events = guard(state, prior, turn['request'])
                gold.update(turn['updates'])
                changed = [k for k in gold if gold[k] != old_gold[k]]
                rows.append(dict(dialogue=dialogue, level=dialogue.split('-')[1], turn=i,
                    observed=dict(state), expected=dict(gold), exact=state == gold,
                    correct_slots=sum(state[k] == gold[k] for k in gold),
                    changed_correct=sum(state[k] == gold[k] for k in changed), changed=len(changed),
                    pose_expression_correct=sum(state[k] == gold[k] for k in ['body_direction', 'hand_pose', 'expression']),
                    corruption=[k for k in gold if prior[k] == old_gold[k] == gold[k] and state[k] != gold[k]],
                    events=events, parse_errors=errors, selected=selected))
        groups = {}
        for level in ['single', 'compound', 'mixed']:
            subset = [r for r in rows if r['level'] == level]
            groups[level] = dict(turns=len(subset), exact_turns=sum(r['exact'] for r in subset),
                correct_slots=sum(r['correct_slots'] for r in subset), slots=len(subset) * 9,
                changed_correct=sum(r['changed_correct'] for r in subset), changed=sum(r['changed'] for r in subset),
                pose_expression_correct=sum(r['pose_expression_correct'] for r in subset),
                pose_expression_total=len(subset) * 3,
                exact_final_dialogues=sum(r['exact'] for r in subset if r['turn'] == 4),
                new_corruptions=sum(len(r['corruption']) for r in subset))
        results[mode] = dict(groups=groups, rows=rows)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    data = benchmark()
    bp = ROOT / 'benchmark.json'
    if bp.exists():
        assert json.loads(bp.read_text()) == data
    else:
        save(bp, data)
    files = [ROOT / name for name in ['run.py', 'benchmark.json', 'PROTOCOL.md', 'test_run.py']]
    files.append(REPO / 'local-studio/request_state.py')
    frozen = dict(model=MODEL, revision=REVISION,
        sha256={str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    fp = ROOT / 'frozen.json'
    if fp.exists():
        assert json.loads(fp.read_text()) == frozen, 'Frozen inputs changed'
    else:
        save(fp, frozen)
    if args.prepare:
        print('Frozen: 12 dialogues, 48 turns, 96 planned model calls')
        return
    from huggingface_hub import snapshot_download
    from mlx_lm import load
    sys.path.insert(0, str(REPO / 'local-studio'))
    from request_state import StateExtractor
    extractor = StateExtractor.__new__(StateExtractor)
    extractor.model, extractor.tokenizer = load(snapshot_download(MODEL, revision=REVISION, local_files_only=True))
    path = ROOT / 'transcripts.json'
    records = json.loads(path.read_text()) if path.exists() else {}
    for name, turns in data.items():
        for i, turn in enumerate(turns, 1):
            key = f'{name}-{i}'
            if key in records:
                assert records[key]['request'] == turn['request']
                continue
            start = time.monotonic()
            first = extractor.ask(SYSTEM, turn['request'], max_tokens=320, examples=EXAMPLES)
            user = turn['request'] + '\nProposed patch: ' + first + '\nReview against the request. Correct errors and return only a flat JSON patch.'
            second = extractor.ask(SYSTEM, user, max_tokens=320, examples=EXAMPLES)
            records[key] = dict(request=turn['request'], first=first, second_user=user,
                                second=second, seconds=time.monotonic() - start)
            save(path, records)
            print('SAVED', key, flush=True)
    result = dict(complete=True, actual_model_calls=len(records) * 2, methods=score(data, records))
    save(ROOT / 'results.json', result)
    print(json.dumps({k: v['groups'] for k, v in result['methods'].items()}, indent=2))


if __name__ == '__main__':
    main()
