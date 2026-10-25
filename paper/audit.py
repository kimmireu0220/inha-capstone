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
    references = manuscript.split('## 참고문헌\n', 1)[1]
    assert re.findall(r'^\[(\d+)\]', references, re.M) == [str(n) for n in range(1, 11)]
    assert 'Meta, “Llama 3.2 Model Card,”' in references
    repository = 'https://github.com/kimmireu0220/inha-capstone'
    reproduction = manuscript.split('### 4.3 재현 자료\n', 1)[1].split('### 4.4', 1)[0]
    assert repository in reproduction and repository not in references
    body = manuscript.split('## 참고문헌\n', 1)[0]
    for phrase in ['턴', '원응답', '자기 이전 상태를 누적', '최종 정답 대화']:
        assert phrase not in body, f'Reader-facing wording: {phrase}'
    assert not re.search(r'\bturns?\b', abstract, re.I)

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

    initial = source('paper/initial-portrait-verification.json')
    assert initial['people'] == initial['paired_endpoints'] == 6
    assert initial['stages_per_person'] == 10 and initial['new_image_calls'] == 0
    assert initial['max_metric_replay_error'] < 1e-6
    assert initial['sequential_outputs'] == 60 and initial['total_measured_outputs'] == 66
    for stage in ['1','5','10']:
        expect(f"{initial['stage_registered_means'][stage]['lpips']:.6f}")
    assert sha(ROOT / 'scripts/summarize_initial_portrait.py') == initial['verifier_sha256']
    for path, digest in {**initial['source_sha256'], **initial['checked_images']}.items():
        assert sha(ROOT / path) == digest, path
    for item in initial['rows']:
        row([item['person'], f"{item['sequential']['face']['3']['lpips']:.6f}", f"{item['original_based']['face']['3']['lpips']:.6f}"])
    expect('6/6쌍')

    prompt_study = ROOT / 'experiments/prompt-state-image-v1'
    prompts = source('experiments/prompt-state-image-v1/summary.json')
    prompt_verified = source('experiments/prompt-state-image-v1/verification.json')
    assert prompts['complete'] and prompts['conditions'] == 18
    assert prompts['people'] == 2 and prompts['dialogues'] == 3
    assert prompts['actual_image_calls'] == 18 and prompts['completed_image_evaluation_responses'] == 36
    assert prompts['actual_new_state_extraction_calls'] == 0
    assert prompt_verified['passed']
    for name, digest in prompt_verified['source_sha256'].items():
        assert sha(prompt_study / name) == digest, name
    for name, digest in prompt_verified['frozen_inputs_verified'].items():
        assert sha(ROOT / name) == digest, name
    length = source('experiments/prompt-state-image-v1/prompt-lengths.json')
    faces = source('experiments/prompt-state-image-v1/face-results.json')
    source('experiments/prompt-state-image-v1/ai-ratings.json')
    source('experiments/prompt-state-image-v1/ai-ratings-7b.json')
    source('experiments/prompt-state-image-v1/secondary-frozen.json')
    assert len(faces['rows']) == 18 and all(r['face_count'] == 1 for r in faces['rows'])
    labels = {'full_history': '전체 요청 이력', 'unchecked_state': '검사 전 현재 조건', 'checked_state': '지시 검사 후 현재 조건'}
    for key, label in labels.items():
        l = length['final_request_means'][key]
        row([label] + [f"{l[v]:.2f}" for v in ['characters', 'words', 'tokens']])
        a, b = prompts['by_mode'][key], prompts['secondary_by_mode'][key]
        row([label, f"{a['goals_satisfied']}/36", a['unknown'], f"{b['goals_satisfied']}/36", b['unknown']])
        row([label, f"{a['identity_mean']:.6f}"] + [f"{a['aligned_means'][v]:.6f}" for v in ['mae','ssim','lpips']])
    reduction = 100 * (1-length['final_request_means']['checked_state']['tokens']/length['final_request_means']['full_history']['tokens'])
    expect(f'{reduction:.2f}%')
    expect('122.67', abstract)
    illustration = source('paper/figures/prompt-state-image-provenance.json')
    assert sha(ROOT / illustration['figure']) == illustration['figure_sha256']
    assert sha(prompt_study / 'figure.py') == illustration['script_sha256']
    for item in illustration['sources']:
        assert sha(ROOT / item['source']) == item['sha256']

    invariants = source('experiments/clause-normalization-v1/invariant-audit.json')
    assert invariants['passed'] and invariants['actual_model_calls'] == 0
    assert not invariants['failures']
    assert sum(group['cases'] for group in invariants['groups'].values()) == 963
    assert all(group['cases'] == group['passed'] for group in invariants['groups'].values())
    assert sha(ROOT / 'scripts/audit_clause_invariants.py') == invariants['verifier_sha256']
    for name, digest in invariants['source_sha256'].items():
        assert sha(ROOT / name) == digest
    expect('963')

    plain = source('experiments/clause-normalization-v1/plain-patch-comparison.json')
    assert plain['posthoc_analysis'] and plain['additional_model_calls'] == 0
    assert sha(ROOT / 'scripts/compare_plain_patch.py') == plain['verifier_sha256']
    assert sha(ROOT / 'local-studio/request_state.py') == plain['reducer_schema_sha256']
    for name, digest in plain['source_sha256'].items():
        assert sha(ROOT / name) == digest
    for study, denominator in [('clause-normalization-v1', 16), ('clause-factorial-v1', 36)]:
        for data in plain['studies'][study].values():
            expect(f"{data['exact_turns']}/{denominator}")

    transfer = source('experiments/instruction-transfer-v1/results.json')
    transfer_summary = source('experiments/instruction-transfer-v1/summary.json')
    transfer_verified = source('experiments/instruction-transfer-v1/verification.json')
    assert transfer['complete'] and transfer['actual_model_calls'] == 96
    assert transfer_verified['passed'] and transfer_verified['requests'] == 48
    assert transfer_summary['distinct_request_texts'] == 32
    assert transfer_summary['goal_configurations'] == 4
    for name, digest in transfer_verified['sha256'].items():
        assert sha(ROOT / 'experiments/instruction-transfer-v1' / name) == digest
    for name, digest in json.loads((ROOT / 'experiments/instruction-transfer-v1/frozen.json').read_text())['sha256'].items():
        assert sha(ROOT / name) == digest
    for data in transfer['methods'].values():
        expect(f"{data['exact_turns']}/48")
    normalized_transfer = transfer['methods']['normalized_atomic']
    expect(f"{normalized_transfer['correct_slots']}/288")
    expect(f"{normalized_transfer['exact_final_dialogues']}/12")
    expect(f"기준이 맞았던 요청을 새로 틀린 경우는 {normalized_transfer['new_errors_vs_baseline']}개였다.")
    expect(f"{transfer['methods']['normalized_atomic']['exact_turns']}/48")
    for group, label in [('recombined', '기존 어휘의 새 조합'),
                         ('unseen', '규칙에 없는 표현'), ('revision', '앞 지시의 수정')]:
        row([label] + [f"{transfer_summary['groups'][mode][group]['target_exact']}/8"
                       for mode in ['baseline_restore', 'keep_remove', 'normalized_atomic', 'json_review_then_first']])

    new_studies = [('operation-scope-validation-v1', 128),
                   ('instruction-eligibility-validation-v1', 64),
                   ('single-extraction-validation-v1', 48)]
    new_results = {}
    for study, calls in new_studies:
        verified = source(f'experiments/{study}/verification.json')
        summary = source(f'experiments/{study}/summary.json')
        assert verified['passed'] and summary['complete']
        assert verified['actual_model_calls'] == summary['actual_model_calls'] == calls
        for name, digest in verified['sha256'].items():
            assert sha(ROOT / 'experiments' / study / name) == digest, (study, name)
        for name, digest in json.loads((ROOT / 'experiments' / study / 'frozen.json').read_text())['sha256'].items():
            assert sha(ROOT / name) == digest, name
        new_results[study] = {model: source(f'experiments/{study}/results-{model}.json')['methods']
                              for model in ['qwen3', 'llama32']}
    for method, label in [('baseline_restore', '기준 방법'), ('keep_remove', '기존 유지·삭제'),
                          ('normalized_atomic', '기존 정규화'), ('isolated_keep_remove', '항목별 적용'),
                          ('normalized_isolated', '기존 정규화+항목별 적용'),
                          ('expanded_normalization', '개선 정규화'), ('json_first_only', 'JSON 최초 응답'),
                          ('json_review_then_first', 'JSON 재검토 우선')]:
        row([label] + [f"{new_results['operation-scope-validation-v1'][m][method]['exact_turns']}/32"
                       for m in ['qwen3', 'llama32']])
    for method, label in [('baseline_restore', '기준 방법'), ('expanded_normalization', '복원 표현 개선'),
                          ('eligible_normalization', '실행 대상 검사 결합')]:
        row([label] + [f"{new_results['instruction-eligibility-validation-v1'][m][method]['exact_turns']}/16"
                       for m in ['qwen3', 'llama32']])
    for method, label in [('baseline_restore', '기준 방법'), ('json_first_only', 'JSON 최초 응답'),
                          ('json_review_then_first', 'JSON 재검토 우선'),
                          ('eligible_normalization', '추출·재검토+지시 검사'),
                          ('single_extraction_checked', '한 번 추출+지시 검사')]:
        data = new_results['single-extraction-validation-v1']
        row([label, data['qwen3'][method]['required_model_calls_per_request']] +
            [f"{data[m][method]['exact_turns']}/12" for m in ['qwen3', 'llama32']])
    for model in ['qwen3', 'llama32']:
        final = new_results['single-extraction-validation-v1'][model]['single_extraction_checked']
        assert final['required_model_calls_per_request'] == 1
        expect(f"{final['correct_slots']}/72")
        expect(f"{final['exact_final_dialogues']}/3")
        expect(f"{final['exact_turns']}/12", abstract)
    for study in ['operation-scope-v2', 'instruction-eligibility-v1']:
        verified = source(f'experiments/{study}/verification.json')
        assert verified['passed'] and verified['additional_model_calls'] == 0
        for name, digest in verified['sha256'].items():
            assert sha(ROOT / 'experiments' / study / name) == digest, name
    final_checks = source('experiments/instruction-eligibility-v1/invariant-audit.json')
    assert final_checks['passed'] and final_checks['cases'] == 1323
    expect('1323')
    implementation = source('paper/implementation-verification.json')
    assert implementation['passed'] and implementation['actual_model_calls'] == 0
    assert implementation['replayed_requests'] == 24 and implementation['one_extraction_per_request']
    for name, digest in implementation['source_sha256'].items():
        assert sha(ROOT / name) == digest, name

    structural = source('experiments/clause-factorial-v1/results.json')
    structural_summary = source('experiments/clause-factorial-v1/summary.json')
    structural_verified = source('experiments/clause-factorial-v1/verification.json')
    assert structural['complete'] and structural['actual_model_calls'] == 72
    assert structural_verified['passed']
    for name, digest in structural_verified['sha256'].items():
        assert sha(ROOT / 'experiments/clause-factorial-v1' / name) == digest
    for data in structural['methods'].values():
        expect(f"{data['exact_turns']}/36")
    for form, label in [('separated', '표준 분리 구절'), ('leaving', 'leaving 연결'),
                        ('preserving', 'preserving 연결'), ('bring_back', 'bring back과 부정형 유지')]:
        row([label] + [f"{structural_summary['forms'][mode][form]['exact_target_requests']}/3"
                       for mode in ['baseline_restore', 'keep_remove', 'normalized_atomic']])
    assert structural_summary['distinct_request_texts'] == 18
    assert structural_summary['target_configurations'] == 3
    for data in structural['methods'].values():
        assert sum(r['exact'] for r in data['rows'] if r['turn'] == 1) == 12
    for forms in structural_summary['forms'].values():
        assert all(data['exact_target_requests'] == data['exact_followups'] for data in forms.values())

    prompt_audit = source('experiments/prompt-synthesis-expanded-v1/prompt-audit.json')
    prompt_plan = source('experiments/prompt-synthesis-expanded-v1/plan.json')
    assert sha(ROOT / 'experiments/prompt-synthesis-expanded-v1/prompt-audit.json') == prompt_plan['prompt_audit_sha256']
    assert prompt_audit['histories']['H3']['agent']['superseded_conditions_still_mentioned'] == 3

    paraphrase = source('experiments/paraphrase-contract-v1/results.json')
    paraphrase_verification = source('experiments/paraphrase-contract-v1/verification.json')
    assert paraphrase['complete'] and paraphrase['actual_model_calls'] == 64
    assert paraphrase_verification['passed']
    for filename, digest in paraphrase_verification['sha256'].items():
        assert sha(ROOT / 'experiments/paraphrase-contract-v1' / filename) == digest
    expect(f"{paraphrase['methods']['keep_remove']['exact_turns']}/32")

    normalized = source('experiments/clause-normalization-v1/results.json')
    normalized_verification = source('experiments/clause-normalization-v1/verification.json')
    assert normalized['complete'] and normalized['actual_model_calls'] == 32
    assert normalized_verification['passed']
    for filename, digest in normalized_verification['sha256'].items():
        assert sha(ROOT / 'experiments/clause-normalization-v1' / filename) == digest
    for mode, label in [('baseline_restore', '기준 방법'), ('keep_remove', '기존 유지·삭제'),
                        ('normalized_atomic', '구절 정규화'), ('isolated_keep_remove', '항목별 적용'),
                        ('normalized_isolated', '정규화+항목별 적용')]:
        result = normalized['methods'][mode]
        row([label, f"{result['exact_turns']}/16", f"{result['correct_slots']}/96",
             f"{result['exact_final_dialogues']}/4", result['new_errors_vs_baseline']])
    development = source('experiments/clause-normalization-v1/development-replay.json')
    assert development['posthoc_development'] and development['additional_model_calls'] == 0
    for name, digest in development['sources_sha256'].items():
        assert sha(ROOT / name) == digest
    for mode in ['normalized_atomic', 'isolated_keep_remove', 'normalized_isolated']:
        expect(f"{development['studies']['paraphrase-contract-v1'][mode]['exact_turns']}/32")

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
        row([f"{pair['person']} 요청 {pair['turn']}",
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
    expect('4/16')
    expect('16/16')
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
    for token in ['추가 확인이 필요', '아직 확인이 필요', '추가 검증이 필요',
                  '근거로 삼지 않았다', '검증 대화 S', '추가 검증 T', '실험 C',
                  '합산하지 않', '해석하지 않', '해석하기 어렵', '판단하기 어렵']:
        assert token not in manuscript + abstract, f'Generic future-work wording: {token}'
    assert not re.search(r'\b[a-f0-9]{40}\b', manuscript), 'Keep model revision hashes in experiment records'
    return {'date': '2026-10-25', 'passed': True,
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
