"""Check the contract-method manuscript against frozen text and image results.

This is transcription/provenance QA, not independent scientific validation.
The default checks the published paper; --source-dir permits draft checking.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(folder):
    manuscript = (folder / 'manuscript.ko.md').read_text()
    abstract = (folder / 'abstract.en.txt').read_text().strip()
    checked, sources = [], {}

    def source(relative):
        path = ROOT / relative
        sources[relative] = sha(path)
        return json.loads(path.read_text())

    def expect(value, text=manuscript):
        assert value in text, f'Missing manuscript value: {value}'
        checked.append(value)

    def row(cells):
        value = '| ' + ' | '.join(map(str, cells)) + ' |'
        assert value in manuscript.splitlines(), f'Missing exact table row: {value}'
        checked.append(value)

    # Development numbers remain distinguishable from frozen S/T validation.
    for name in ['keep-contract-validation-v1', 'keep-contract-v2']:
        development = source(f'experiments/{name}/results.json')
        verified = source(f'experiments/{name}/verification.json')
        assert development['complete'] and verified['passed']
        for filename, digest in verified['sha256'].items():
            assert sha(ROOT / 'experiments' / name / filename) == digest
        modes = (['baseline_restore', 'baseline_restore_keep']
                 if name == 'keep-contract-validation-v1'
                 else ['baseline_restore', 'keep_v1', 'keep_v2'])
        for mode in modes:
            result = development['methods'][mode]
            expect(f"{result['exact_turns']}/32")
        if name == 'keep-contract-v2':
            for mode in ['baseline_restore', 'keep_v2']:
                expect(f"{development['methods'][mode]['exact_final_dialogues']}/8")

    studies = [
        ('request-contract-v3', [('baseline_restore', '기준 방법'),
          ('keep_only', '유지 규칙만'), ('remove_only', '삭제 규칙만'),
          ('keep_remove', '유지·삭제 결합')]),
        ('isolated-contract-v1', [('baseline_restore', '기준 방법'),
          ('isolated_restore', '항목별 적용'), ('keep_remove', '유지·삭제'),
          ('isolated_keep_remove', '항목별 적용+유지·삭제')]),
    ]
    for name, methods in studies:
        data = source(f'experiments/{name}/results.json')
        verification = source(f'experiments/{name}/verification.json')
        assert data['complete'] and data['actual_model_calls'] == 64
        assert verification['passed']
        for filename, digest in verification['sha256'].items():
            assert sha(ROOT / 'experiments' / name / filename) == digest
        for mode, label in methods:
            result = data['methods'][mode]
            dialogues = {r['dialogue'] for r in result['rows']}
            assert len(dialogues) == 8 and result['turns'] == 32 and result['slots'] == 192
            row([label, f"{result['exact_turns']}/32", f"{result['correct_slots']}/192",
                 f"{result['exact_final_dialogues']}/8", result['newly_corrupted_unchanged_slots']])
        for mode in ['baseline_restore', 'keep_remove']:
            expect(f"{data['methods'][mode]['exact_turns']}/32", abstract)

    for name in ['keep-image-v1', 'contract-image-v3']:
        data = source(f'experiments/{name}/summary.json')
        verification = source(f'experiments/{name}/verification.json')
        pairs = source(f'experiments/{name}/paired-audit.json')
        assert verification['passed'] and verification['conditions'] == 128
        assert data['rater_type'] == 'AI' and data['descriptive_only']
        assert pairs['different_input_pairs'] == 4 and pairs['shared_input_pairs'] == 60
        for filename, digest in verification['sha256'].items():
            assert sha(ROOT / 'experiments' / name / filename) == digest
        for mode, result in data['by_mode'].items():
            assert result['conditions'] == 64 and result['goal_denominator'] == 384
            expect(f"{result['goals_satisfied']}/384")
            expect(f"{result['face_mean']:.6f}")
            if name == 'contract-image-v3':
                label = '기준 방법' if mode == 'baseline_restore' else '유지·삭제 결합'
                row([label, f"{result['goals_satisfied']}/384", result['unknown_goals'],
                     f"{result['all_six_satisfied']}/64", f"{result['face_mean']:.6f}"])

    review = source('experiments/contract-image-review-v1/summary.json')
    review_verification = source('experiments/contract-image-review-v1/verification.json')
    assert review['complete'] and review['post_hoc'] and review_verification['passed']
    review_root = ROOT / 'experiments/contract-image-review-v1'
    for filename, digest in review_verification['sha256'].items():
        assert sha(review_root / filename) == digest
    freeze = json.loads((review_root / 'frozen.json').read_text())
    for filename, digest in freeze['sha256'].items():
        assert sha(ROOT / filename) == digest
    for mode, result in review['by_mode'].items():
        label = '기준 방법' if mode == 'baseline_restore' else '유지·삭제 결합'
        row([label, f"{result['goals_satisfied']}/384", result['unknown_goals'],
             f"{result['all_six_satisfied']}/64"])
    primary_pairs = json.loads((ROOT / 'experiments/contract-image-v3/paired-audit.json').read_text())
    key = lambda p: (p['person'], p['history'], p['turn'])
    lookup = {key(p): p for p in primary_pairs['pairs']}
    for pair in review['pairs']['pairs']:
        if pair['same_input_job']:
            continue
        baseline = lookup[key(pair)]
        row([f"{pair['person']} {pair['history']} {pair['turn']}턴",
             *[f'{v}/6' for v in baseline['goal_counts']],
             *[f'{v}/6' for v in pair['goal_counts']]])
    agreement = review['unique_input_agreement']
    expect(f"{agreement['same_including_unknown']}/{agreement['decisions']}")
    expect(f"{agreement['same_when_both_known']}/{agreement['both_known']}")
    compound = source('experiments/compound-edit-v1/summary.json')
    compound_verified = source('experiments/compound-edit-v1/verification.json')
    assert compound['complete'] and compound_verified['passed']
    for filename, digest in compound_verified['sha256'].items():
        assert sha(ROOT / 'experiments/compound-edit-v1' / filename) == digest
    for level, label in [('single', '표정'), ('compound', '표정·포즈'), ('mixed', '속성 지시 혼합')]:
        row([label] + [f"{compound['groups'][mode][level]['exact_turns']}/16"
                       for mode in ['direct', 'review', 'guarded']])
    assert compound['post_hoc_remove_only_exact_turns'] == 48
    assert compound['post_hoc_operation_control'] == {
        'requests': 8, 'model_calls': 16, 'first_exact': 7, 'review_exact': 7, 'failed_ids': ['5']}
    expect('각각 7/8')
    expect('124/144')
    expect('144/144')
    expect('4/16', abstract)
    expect('16/16', abstract)
    assert sum(x['unknown'] for x in compound['image_rows']) == 2
    assert sum(x['parse_error'] is not None for x in compound['image_rows']) == 2
    provenance = json.loads((folder / 'figures/figure-provenance.json').read_text())
    assert provenance['script_sha256'] == sha(ROOT / 'paper/make_contract_figure.py')
    assert provenance['prepared_sha256'] == sha(ROOT / 'experiments/contract-image-v3/prepared.json')
    illustrated = []
    for figure in provenance['figures']:
        assert sha(folder / 'figures' / figure['figure']) == figure['sha256']
        for item in figure['sources']:
            assert not Path(item['source']).is_absolute()
            assert sha(ROOT / item['source']) == item['sha256']
            illustrated.append(item['condition'])
    assert len(illustrated) == len(set(illustrated)) == 8
    assert set(illustrated) == {f'{person}-S3-t{turn}-{mode}'
                               for person in ['R01', 'R02'] for turn in [3, 4]
                               for mode in ['baseline_restore', 'keep_remove']}
    for token in ['진행 중이며', '집계 후 이 절', '집계 후 반영', 'being evaluated']:
        assert token not in manuscript + abstract, f'Unfinished draft: {token}'
    for token in ['추가 확인이 필요', '아직 확인이 필요', '추가 검증이 필요']:
        assert token not in manuscript + abstract, f'Generic future-work wording: {token}'
    assert not re.search(r'\b[a-f0-9]{40}\b', manuscript), 'Keep model revision hashes in experiment records'
    return {'date': '2026-10-08', 'passed': True,
            'scope': 'Numeric transcription and provenance QA, not independent scientific validation',
            'manuscript_sha256': sha(folder / 'manuscript.ko.md'),
            'english_abstract_sha256': hashlib.sha256(abstract.encode()).hexdigest(),
            'checked_values': checked,
            'figure_provenance_sha256': sha(folder / 'figures/figure-provenance.json'),
            'sources': [{'name': path, 'path': path, 'sha256': digest}
                        for path, digest in sources.items()]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=ROOT / 'paper')
    args = parser.parse_args()
    result = audit(args.source_dir.resolve())
    (args.source_dir / 'evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Contract-paper audit passed: {len(result['checked_values'])} values/rows")
