"""Join completed AI ratings with masked methods and face measurements."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
MODES = ['agent', 'tracked']
CANCELLED = {'U1': [0, 2, 3], 'U2': [3], 'U3': [2], 'U4': [3]}


def mean(values):
    return sum(values) / len(values) if values else None


def validate_scores(scores):
    assert isinstance(scores, list) and len(scores) == 6, 'Exactly six scores required'
    assert all(v is None or type(v) is int and v in (0, 1) for v in scores), 'Invalid score'
    return scores


def summarize(rows):
    values = [r['identity_similarity'] for r in rows if r['identity_similarity'] is not None]
    return {'images': len(rows), 'achieved': sum(sum(v == 1 for v in r['scores']) for r in rows),
        'target_total': 6 * len(rows), 'uncertain': sum(sum(v is None for v in r['scores']) for r in rows),
        'identity_mean': mean(values), 'single_face': sum(r['face_count'] == 1 for r in rows),
        'cancelled_achieved': sum(sum(r['scores'][i] == 1 for i in CANCELLED[r['history']]) for r in rows),
        'cancelled_total': sum(len(CANCELLED[r['history']]) for r in rows)}


def main():
    verification = json.loads((ROOT / 'verification.json').read_text())
    assert verification['complete'] is True and verification['outputs'] == 96
    assert verification['frozen_inputs_prompts_and_output_hashes_verified'] is True
    notes = json.loads((ROOT / 'run_notes.json').read_text())
    ratings = json.loads((ROOT / 'ai-ratings.json').read_text())
    assert ratings['rater_type'] == 'AI' and ratings['method_masked'] is True
    mapping = json.loads((ROOT / 'blinding-map.json').read_text())
    assert len(mapping) == 48 and set(ratings['ratings']) == set(mapping)
    measurements = json.loads((ROOT / 'face-results.json').read_text())['rows']
    metrics = {(r['person'], r['history'], r['seed'], r['mode']): r for r in measurements}
    assert len(measurements) == len(metrics) == 96
    rows = []
    for key, values in ratings['ratings'].items():
        person, history, seed = key.split('-')
        assert set(values['scores']) == {'A', 'B'}
        for letter in 'AB':
            scores = validate_scores(values['scores'][letter])
            mode = mapping[key][letter]
            row = metrics[(person, history, int(seed), mode)]
            rows.append({**row, 'scores': scores, 'blind_label': letter, 'note': values.get('note', '')})
    by_mode = {mode: summarize([r for r in rows if r['mode'] == mode]) for mode in MODES}
    people = sorted({r['person'] for r in rows})
    histories = sorted({r['history'] for r in rows})
    by_person = {p: {m: summarize([r for r in rows if r['person'] == p and r['mode'] == m])
                     for m in MODES} for p in people}
    by_history = {h: {m: summarize([r for r in rows if r['history'] == h and r['mode'] == m])
                      for m in MODES} for h in histories}
    differences = {p: {'goals': by_person[p]['tracked']['achieved'] - by_person[p]['agent']['achieved'],
        'identity': by_person[p]['tracked']['identity_mean'] - by_person[p]['agent']['identity_mean']}
        for p in people}
    prompt_cost = {}
    for mode in MODES:
        transcripts = [json.loads((ROOT / 'prompts' / f'{h}-transcript.json').read_text())[mode]
                       for h in histories]
        prompt_cost[mode] = {'model_calls': sum(r['model_calls'] for r in transcripts),
            'seconds': sum(r['seconds'] for r in transcripts),
            'final_characters': {h: len((ROOT / 'prompts' / f'{h}-{mode}.txt').read_text()) for h in histories}}
    summary = {'complete': True, 'outputs': 96, 'pairs': 48, 'independent_people': 6,
        'rater_type': 'AI', 'independent_human_rating_complete': False,
        'primary_ai_version_note': ratings.get('rater_version_note'),
        'primary_ai_corrections_before_unmasking': ratings.get('corrections_before_unmasking', []),
        'by_mode': by_mode, 'by_person': by_person, 'by_history': by_history,
        'tracked_minus_agent_by_person': differences, 'prompt_cost': prompt_cost,
        'state_extraction': json.loads((ROOT / 'state-scores.json').read_text())}
    secondary = json.loads((ROOT / 'second-ai-ratings.json').read_text())
    assert secondary['rater_type'] == 'AI' and secondary['method_masked'] is True
    assert set(secondary['ratings']) == {key + '/' + label for key in mapping for label in 'AB'}
    agreement, comparable, unavailable = 0, 0, 0
    agreement_by_goal = [{'slot': slot, 'same': 0, 'comparable': 0,
                          'primary_only_success': 0, 'secondary_only_success': 0,
                          'unavailable': 0}
                         for slot in ['jacket', 'top', 'pin', 'necklace', 'background', 'prop']]
    secondary_rows = []
    for row in rows:
        key = f"{row['person']}-{row['history']}-{row['seed']}/{row['blind_label']}"
        scores = validate_scores(secondary['ratings'][key]['scores'])
        for goal, primary, other in zip(agreement_by_goal, row['scores'], scores):
            if primary is None or other is None:
                unavailable += 1
                goal['unavailable'] += 1
            else:
                comparable += 1
                agreement += primary == other
                goal['comparable'] += 1
                goal['same'] += primary == other
                goal['primary_only_success'] += primary == 1 and other == 0
                goal['secondary_only_success'] += primary == 0 and other == 1
        secondary_rows.append({**row, 'scores': scores})
    summary['second_ai'] = {'model': secondary['model'], 'revision': secondary['revision'],
        'by_mode': {mode: summarize([r for r in secondary_rows if r['mode'] == mode]) for mode in MODES},
        'by_person': {p: {m: summarize([r for r in secondary_rows if r['person'] == p and r['mode'] == m])
                         for m in MODES} for p in people},
        'agreement': {'same': agreement, 'comparable': comparable, 'unavailable': unavailable,
                      'by_goal': agreement_by_goal,
                      'scope': 'Descriptive AI agreement, not independent human validation'},
        'parse_failures': sum(r['parse_error'] is not None for r in secondary['ratings'].values()),
        'diagnostic': notes.get('secondary_ai_diagnostic')}
    summary['cost_scope'] = notes['preparation_interruption']['cost_scope']
    state = summary['state_extraction']
    state['joint_correct_turns'] = sum(r['correct_slots'] == 6 for r in state['turns'])
    state['total_turns'] = len(state['turns'])
    state['joint_correct_final_dialogues'] = sum(r['correct_slots'] == 6 for r in state['turns'] if r['turn'] == 8)
    state['total_dialogues'] = len(histories)
    inputs = ['ai-ratings.json', 'second-ai-ratings.json', 'face-results.json',
              'state-scores.json', 'blinding-map.json', 'plan.json', 'verification.json', 'run_notes.json']
    inputs += [f'prompts/{h}-transcript.json' for h in histories]
    summary['source_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in inputs}
    (ROOT / 'joined-results.json').write_text(json.dumps({'rows': rows}, indent=2) + '\n')
    (ROOT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({'by_mode': by_mode, 'person_differences': differences}, indent=2))


if __name__ == '__main__':
    main()
