"""Post-hoc descriptive paired audit; never modifies frozen ratings or outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(rows, modes):
    grouped = {}
    for row in rows:
        key = (row['person'], row['history'], row['turn'])
        assert row['mode'] not in grouped.setdefault(key, {})
        grouped[key][row['mode']] = row
    pairs = []
    for key, group in sorted(grouped.items()):
        assert set(group) == set(modes)
        a, b = [group[mode] for mode in modes]
        same = a['job'] == b['job']
        if same:
            assert a['scores'] == b['scores']
            assert a['rgb_sha256'] == b['rgb_sha256']
            assert a['identity_similarity'] == b['identity_similarity']
        faces = [a['identity_similarity'], b['identity_similarity']]
        delta = None if None in faces else faces[1] - faces[0]
        pairs.append({'person': key[0], 'history': key[1], 'turn': key[2],
                      'same_input_job': same, 'jobs': [a['job'], b['job']],
                      'goal_counts': [sum(x == 1 for x in row['scores']) for row in [a, b]],
                      'unknown_counts': [sum(x is None for x in row['scores']) for row in [a, b]],
                      'scores': [a['scores'], b['scores']], 'face_delta': delta})
    changed = [p for p in pairs if not p['same_input_job']]
    deltas = [p['goal_counts'][1] - p['goal_counts'][0] for p in changed]
    face_deltas = [p['face_delta'] for p in changed if p['face_delta'] is not None]
    return {'pairs': pairs, 'total_pairs': len(pairs), 'different_input_pairs': len(changed),
            'shared_input_pairs': len(pairs) - len(changed),
            'different_input_goal_delta': sum(deltas),
            'different_input_goal_wins': sum(d > 0 for d in deltas),
            'different_input_goal_ties': sum(d == 0 for d in deltas),
            'different_input_goal_losses': sum(d < 0 for d in deltas),
            'different_input_mean_face_delta': statistics.mean(face_deltas) if face_deltas else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--baseline', default='baseline_restore')
    args = parser.parse_args()
    root = args.root.resolve()
    data = json.loads((root / 'summary.json').read_text())
    for name, digest in data['input_sha256'].items():
        assert sha(root / name) == digest, name
    modes = [args.baseline] + [m for m in data['by_mode'] if m != args.baseline]
    assert len(modes) == 2
    result = compare(data['rows'], modes)
    result.update({'modes': modes, 'post_hoc_descriptive_audit': True,
                   'no_independent_sample_test': True,
                   'summary_sha256': sha(root / 'summary.json'), 'script_sha256': sha(Path(__file__))})
    (root / 'paired-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'pairs'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
