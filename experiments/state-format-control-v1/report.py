"""Join source and control judgments without treating reused images as replicates."""
import importlib.util
import json
from prepare import ROOT, SOURCE, save, sha


def read(root, name):
    return json.loads((root / name).read_text())


def main():
    spec = importlib.util.spec_from_file_location('source_report', SOURCE / 'report.py')
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    verification = read(ROOT, 'verification.json')
    assert verification.get('complete') is True and verification.get('outputs') == 48
    assert verification.get('frozen_inputs_prompts_and_output_hashes_verified') is True
    mapping = read(ROOT, 'blinding-map.json')
    linked = read(ROOT, 'linked-ratings.json')
    pending = read(ROOT, 'pending-ratings.json')
    expected_keys = {key + '/' + label for key in mapping for label in 'ABC'}
    assert len(mapping) == 48 and len(expected_keys) == 144
    assert not (set(linked) & set(pending)) and set(linked) | set(pending) == expected_keys
    primary = read(ROOT, 'ai-ratings.json') if pending else {'ratings': {}}
    secondary = read(ROOT, 'second-ai-ratings.json')
    assert set(primary['ratings']) == set(secondary['ratings']) == set(pending)
    if pending:
        assert primary['rater_type'] == secondary['rater_type'] == 'AI'
        assert primary['method_masked'] is True and secondary['method_masked'] is True
    old_primary = read(SOURCE, 'ai-ratings.json')
    old_secondary = read(SOURCE, 'second-ai-ratings.json')
    assert secondary['model'] == old_secondary['model'] and secondary['revision'] == old_secondary['revision']
    measurements = read(SOURCE, 'face-results.json')['rows'] + read(ROOT, 'face-results.json')['rows']
    metrics = {(r['person'], r['history'], r['seed'], r['mode']): r for r in measurements}
    assert len(metrics) == len(measurements) == 144
    rows, second_rows = [], []
    agreement = {'same': 0, 'comparable': 0, 'unavailable': 0}
    for comparison, assignments in mapping.items():
        assert set(assignments.values()) == {'agent', 'tracked', 'structured'}
        person, history, seed = comparison.split('-')
        for label, mode in assignments.items():
            key = comparison + '/' + label
            metric = metrics[(person, history, int(seed), mode)]
            if key in linked:
                link = linked[key]
                assert metric['output_sha256'] == link['output_sha256']
                original_key, original_label = link['source_comparison'], link['source_label']
                scores = old_primary['ratings'][original_key]['scores'][original_label]
                other = old_secondary['ratings'][original_key + '/' + original_label]['scores']
            else:
                assert metric['output_sha256'] == pending[key]['output_sha256']
                scores, other = primary['ratings'][key]['scores'], secondary['ratings'][key]['scores']
            scores, other = shared.validate_scores(scores), shared.validate_scores(other)
            rows.append({**metric, 'scores': scores, 'rating_reused': key in linked})
            second_rows.append({**metric, 'scores': other, 'rating_reused': key in linked})
            for left, right in zip(scores, other):
                if left is None or right is None:
                    agreement['unavailable'] += 1
                else:
                    agreement['comparable'] += 1
                    agreement['same'] += left == right
    modes = ['agent', 'tracked', 'structured']
    people = sorted({row['person'] for row in rows})
    histories = sorted({row['history'] for row in rows})
    transcripts = [read(ROOT / 'prompts', h + '-transcript.json') for h in histories]
    control = [r for r in rows if r['mode'] == 'structured']
    control_hashes = {}
    pixel_hashes = {}
    for row in control:
        control_hashes.setdefault(row['output_sha256'], []).append(
            f"{row['person']}-{row['history']}-{row['seed']}")
        pixel_hashes.setdefault(row['rgb_pixel_sha256'], []).append(
            f"{row['person']}-{row['history']}-{row['seed']}")
    summary = {'complete': True, 'conditions': 144, 'independent_people': 6,
               'new_control_conditions': 48, 'control_reused_images': sum(r['reused'] for r in control),
               'control_new_images': sum(not r['reused'] for r in control),
               'control_unique_output_hashes': len(control_hashes),
               'all_unique_output_hashes': len({r['output_sha256'] for r in rows}),
               'duplicate_control_output_groups': [keys for keys in control_hashes.values() if len(keys) > 1],
               'control_unique_rgb_pixels': len(pixel_hashes),
               'duplicate_control_pixel_groups': [keys for keys in pixel_hashes.values() if len(keys) > 1],
               'uniqueness_note': 'Counts distinguish identical output file bytes, not independent people or trials.',
               'pixel_uniqueness_note': 'RGB pixel hashes include dimensions and ignore PNG metadata. Repeated content is not an independent replicate.',
               'independent_human_rating_complete': False,
               'design_note': 'Post-hoc diagnostic on reused histories; not a new held-out generalization test.',
               'control_prompt_cost': {'model_calls': sum(r['model_calls'] for r in transcripts),
                                       'seconds': sum(r['seconds'] for r in transcripts)},
               'control_generation_seconds': sum(r['seconds'] for r in control),
               'state_extraction': read(ROOT, 'state-scores.json')}
    for name, values in [('primary_ai', rows), ('secondary_ai', second_rows)]:
        summary[name] = {'by_mode': {m: shared.summarize([r for r in values if r['mode'] == m]) for m in modes},
            'by_person': {p: {m: shared.summarize([r for r in values if r['person'] == p and r['mode'] == m])
                              for m in modes} for p in people},
            'by_history': {h: {m: shared.summarize([r for r in values if r['history'] == h and r['mode'] == m])
                               for m in modes} for h in histories}}
    summary['descriptive_ai_agreement_including_reuse'] = agreement
    sources = [(ROOT, name) for name in ['blinding-map.json', 'linked-ratings.json', 'pending-ratings.json',
               'second-ai-ratings.json', 'face-results.json', 'verification.json', 'plan.json', 'state-scores.json']]
    sources += [(SOURCE, name) for name in ['ai-ratings.json', 'second-ai-ratings.json', 'face-results.json']]
    sources += [(ROOT / 'prompts', h + '-transcript.json') for h in histories]
    if pending:
        sources.append((ROOT, 'ai-ratings.json'))
    summary['source_sha256'] = {str((root / name).relative_to(ROOT.parent)): sha(root / name) for root, name in sources}
    save(ROOT / 'joined-results.json', {'rows': rows})
    save(ROOT / 'summary.json', summary)
    print(json.dumps(summary['primary_ai']['by_mode'], indent=2))


if __name__ == '__main__':
    main()
