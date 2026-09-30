"""Join one blinded visual rater with the method map and summarize by person."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODES = ['history', 'state', 'agent']
HISTORIES = ['H1', 'H2', 'H3']


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def mean(values):
    return sum(values) / len(values) if values else None


def main():
    ratings = json.loads((ROOT / 'blind-ratings.json').read_text())
    mapping = json.loads((ROOT / 'blinding-map.json').read_text())
    measurements = json.loads((ROOT / 'results.json').read_text())['rows']
    plan = json.loads((ROOT / 'plan.json').read_text())
    assert ratings['rated_before_opening_blinding_map_or_similarity_results'] is True
    assert set(ratings['ratings']) == set(mapping) and len(mapping) == 36
    measurements_by_key = {(r['person'], r['history'], r['seed'], r['mode']): r
        for r in measurements}
    joined = []
    for group, labeled in ratings['ratings'].items():
        person, history, seed_text = group.split('-')
        seed = int(seed_text)
        assert set(labeled['scores']) == set('ABC')
        for letter in 'ABC':
            scores = labeled['scores'][letter]
            assert len(scores) == 6 and all(v in (0, 1, None) for v in scores)
            mode = mapping[group][letter]
            measurement = measurements_by_key[(person, history, seed, mode)]
            joined.append({'person': person, 'history': history, 'seed': seed,
                'mode': mode, 'blind_label': letter, 'scores': scores,
                'achieved': sum(v == 1 for v in scores),
                'judged': sum(v is not None for v in scores),
                'identity_similarity': measurement['identity_similarity'],
                'face_count': measurement['face_count'],
                'note': labeled.get('note', '')})
    assert len(joined) == 108
    save(ROOT / 'joined-results.json', {'rows': joined})

    by_mode = {}
    for mode in MODES:
        subset = [r for r in joined if r['mode'] == mode]
        by_mode[mode] = {'images': len(subset),
            'achieved': sum(r['achieved'] for r in subset),
            'judged': sum(r['judged'] for r in subset),
            'target_total': 6 * len(subset),
            'identity_mean': mean([r['identity_similarity'] for r in subset
                if r['identity_similarity'] is not None]),
            'face_detected': sum(r['face_count'] == 1 for r in subset)}
    by_history = {}
    for history in HISTORIES:
        by_history[history] = {}
        for mode in MODES:
            subset = [r for r in joined if r['history'] == history and r['mode'] == mode]
            by_history[history][mode] = {
                'achieved': sum(r['achieved'] for r in subset),
                'judged': sum(r['judged'] for r in subset),
                'target_total': 6 * len(subset),
                'identity_mean': mean([r['identity_similarity'] for r in subset
                    if r['identity_similarity'] is not None])}
    by_person = {}
    for person in plan['people_order']:
        by_person[person] = {}
        for mode in MODES:
            subset = [r for r in joined if r['person'] == person and r['mode'] == mode]
            by_person[person][mode] = {
                'achieved': sum(r['achieved'] for r in subset),
                'judged': sum(r['judged'] for r in subset),
                'target_total': 6 * len(subset),
                'identity_mean': mean([r['identity_similarity'] for r in subset
                    if r['identity_similarity'] is not None])}
    paired = {}
    for first, second in [('agent', 'history'), ('agent', 'state'),
                          ('state', 'history')]:
        diffs = [by_person[p][first]['achieved'] - by_person[p][second]['achieved']
            for p in plan['people_order']]
        face_diffs = [(by_person[p][first]['identity_mean']
            - by_person[p][second]['identity_mean'])
            for p in plan['people_order']]
        paired[f'{first}_minus_{second}'] = {'person_goal_differences': diffs,
            'goal_positive': sum(x > 0 for x in diffs),
            'goal_tied': sum(x == 0 for x in diffs),
            'goal_negative': sum(x < 0 for x in diffs),
            'person_face_differences': face_diffs,
            'face_positive': sum(x > 0 for x in face_diffs),
            'face_negative': sum(x < 0 for x in face_diffs)}
    sensitivity = {}
    for mode in MODES:
        subset = [r for r in joined if r['mode'] == mode and
            (r['person'], r['history'], r['seed']) != ('R01', 'H2', 42)]
        sensitivity[mode] = {'images': len(subset),
            'achieved': sum(r['achieved'] for r in subset),
            'judged': sum(r['judged'] for r in subset),
            'target_total': 6 * len(subset)}
    save(ROOT / 'summary.json', {'independent_people': 6,
        'repeated_observations_per_person': 18, 'outputs': 108,
        'by_mode': by_mode, 'by_history': by_history, 'by_person': by_person,
        'paired': paired, 'excluding_unblinded_set': sensitivity})
    print(json.dumps({'by_mode': by_mode, 'paired': paired},
        ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
