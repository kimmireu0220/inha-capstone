"""Check the contract-method manuscript against frozen text and image results.

This is transcription/provenance QA, not independent scientific validation.
The default checks the published paper; --source-dir permits draft checking.
"""
import argparse
import hashlib
import json
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

    studies = [
        ('request-contract-v3', [('baseline_restore', '공통 기준'),
          ('keep_only', '유지 보호만'), ('remove_only', '삭제 실행만'),
          ('keep_remove', '유지·삭제 결합')]),
        ('isolated-contract-v1', [('baseline_restore', '공통 기준'),
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
                label = '공통 기준' if mode == 'baseline_restore' else '유지·삭제 결합'
                row([label, f"{result['goals_satisfied']}/384", result['unknown_goals'],
                     f"{result['all_six_satisfied']}/64", f"{result['face_mean']:.6f}"])

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
    for token in ['진행 중이며', '집계 후 이 절', 'being evaluated']:
        assert token not in manuscript + abstract, f'Unfinished draft: {token}'
    return {'date': '2026-10-06', 'passed': True,
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
