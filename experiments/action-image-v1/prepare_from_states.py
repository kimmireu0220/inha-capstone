"""Prepare a new image study from a verified state experiment, without generation.

Required explicit arguments prevent changing a frozen study's selected snapshots.
The destination must already contain its own image protocol.
"""
import argparse
import hashlib
import json
from pathlib import Path
from prepare import REPO, REFERENCES, save, sha, render_prompt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--modes', nargs=2, required=True)
    parser.add_argument('--turns', nargs='+', required=True)
    args = parser.parse_args()
    root, source = args.root.resolve(), args.source.resolve()
    assert (root / 'PROTOCOL.md').is_file()
    assert root.is_relative_to(REPO) and source.is_relative_to(REPO)
    verification = json.loads((source / 'verification.json').read_text())
    assert verification['passed'] and verification['advance_to_images']
    for name, digest in verification['sha256'].items():
        assert sha(source / name) == digest
    results = json.loads((source / 'results.json').read_text())['methods']
    modes = args.modes
    assert len(set(modes)) == 2, 'Two distinct methods are required'
    maps = {mode: {(r['dialogue'], r['turn']): r for r in results[mode]['rows']} for mode in modes}
    assert set(maps[modes[0]]) == set(maps[modes[1]])
    selected_turns = None if args.turns == ['all'] else {int(value) for value in args.turns}
    conditions, jobs, paired_snapshots = [], {}, []
    for hi, (key, row) in enumerate(maps[modes[0]].items()):
        history, turn = key
        if selected_turns is not None and turn not in selected_turns:
            continue
        assert row['expected'] == maps[modes[1]][key]['expected']
        prompts = {mode: render_prompt(maps[mode][key]['observed']) for mode in modes}
        paired_snapshots.append({'history': history, 'turn': turn, 'same_prompt': prompts[modes[0]] == prompts[modes[1]]})
        for pi, person in enumerate(['R01', 'R02']):
            order = modes if (hi + pi) % 2 else modes[::-1]
            for mode in order:
                prompt = prompts[mode]
                signature = hashlib.sha256((sha(REFERENCES / f'{person}.png') + '\n' + prompt).encode()).hexdigest()
                job = jobs.setdefault(signature, 'img-' + signature[:16])
                conditions.append({'id': f'{person}-{history}-t{turn}-{mode}', 'person': person, 'history': history,
                                   'turn': turn, 'mode': mode, 'job': job, 'signature': signature, 'prompt': prompt,
                                   'observed_state': maps[mode][key]['observed'], 'expected_state': row['expected']})
    files = [Path(__file__), Path(__file__).with_name('prepare.py'), root / 'PROTOCOL.md',
             source / 'results.json', source / 'verification.json', REPO / 'local-studio/request_state.py']
    files += [REFERENCES / f'{person}.png' for person in ['R01', 'R02']]
    result = {'generation_not_started': True, 'backend_pending_confirmation': True,
              'source': str(source.relative_to(REPO)), 'modes': modes, 'turns': args.turns,
              'condition_count': len(conditions), 'unique_prompt_reference_jobs': len(jobs),
              'different_prompt_snapshots': sum(not r['same_prompt'] for r in paired_snapshots),
              'paired_snapshots': paired_snapshots, 'inputs': {str(p.relative_to(REPO)): sha(p) for p in files},
              'conditions': conditions}
    output = root / 'prepared.json'
    if output.exists():
        assert json.loads(output.read_text()) == result, 'Frozen image preparation changed'
    else:
        save(output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ['conditions', 'inputs', 'paired_snapshots']}, indent=2))


if __name__ == '__main__':
    main()
