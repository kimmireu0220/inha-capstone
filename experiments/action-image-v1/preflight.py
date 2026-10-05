"""Before-image diagnostic: retained lapel pins can require a removed garment.

Flags describe potential visual incompatibility, not an exhaustive feasibility
proof. All planned conditions remain in the primary evaluation denominator.
"""
import json
from pathlib import Path
import sys
from goals import ORIGINAL
from evaluate import save, sha


def conflicts(person, state):
    no_lapelled_outerwear = state['jacket'] == 'none' or (
        state['jacket'] == 'original' and ORIGINAL[person][0] == 'No blazer or jacket')
    return ['lapel_pin_without_blazer'] if no_lapelled_outerwear and state['pin'] not in ('none', 'original') else []


def main():
    root = Path(sys.argv[1]).resolve()
    prepared = json.loads((root / 'prepared.json').read_text())
    assert not (root / 'calls.json').exists(), 'Preflight must be frozen before image generation'
    rows = [{'id': row['id'], 'target_flags': conflicts(row['person'], row['expected_state']),
             'predicted_flags': conflicts(row['person'], row['observed_state'])}
            for row in prepared['conditions']]
    result = {'before_generation': True, 'diagnostic_only': True, 'conditions_excluded': 0,
              'prepared_sha256': sha(root / 'prepared.json'), 'script_sha256': sha(Path(__file__)),
              'target_flagged_conditions': sum(bool(row['target_flags']) for row in rows),
              'predicted_flagged_conditions': sum(bool(row['predicted_flags']) for row in rows), 'rows': rows}
    output = root / 'feasibility-preflight.json'
    if output.exists():
        assert json.loads(output.read_text()) == result
    else:
        save(output, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
