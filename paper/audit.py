"""Verify published claims against frozen results and source photographs.

Checks numeric transcription and provenance; experimental validity is discussed
in the manuscript. Run with the bundled document Python runtime.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    'experiments/extended-state-validation-v1/summary.json',
    'experiments/extended-state-validation-v1/verification.json',
    'experiments/extended-state-validation-v1/frozen.json',
    'paper/initial-portrait-verification.json',
    'experiments/prompt-state-image-v1/summary.json',
    'experiments/prompt-state-image-v1/verification.json',
    'experiments/prompt-state-image-v1/prompt-lengths.json',
    'experiments/prompt-state-image-v1/face-results.json',
    'experiments/prompt-state-image-v1/ai-ratings.json',
    'experiments/prompt-state-image-v1/ai-ratings-7b.json',
    'experiments/prompt-state-image-v1/secondary-frozen.json',
    'paper/figures/prompt-state-image-provenance.json',
    'experiments/clause-normalization-v1/invariant-audit.json',
    'experiments/clause-normalization-v1/plain-patch-comparison.json',
    'experiments/instruction-transfer-v1/results.json',
    'experiments/instruction-transfer-v1/summary.json',
    'experiments/instruction-transfer-v1/verification.json',
    'experiments/operation-scope-validation-v1/verification.json',
    'experiments/operation-scope-validation-v1/summary.json',
    'experiments/operation-scope-validation-v1/results-qwen3.json',
    'experiments/operation-scope-validation-v1/results-llama32.json',
    'experiments/instruction-eligibility-validation-v1/verification.json',
    'experiments/instruction-eligibility-validation-v1/summary.json',
    'experiments/instruction-eligibility-validation-v1/results-qwen3.json',
    'experiments/instruction-eligibility-validation-v1/results-llama32.json',
    'experiments/single-extraction-validation-v1/verification.json',
    'experiments/single-extraction-validation-v1/summary.json',
    'experiments/single-extraction-validation-v1/results-qwen3.json',
    'experiments/single-extraction-validation-v1/results-llama32.json',
    'experiments/operation-scope-v2/verification.json',
    'experiments/instruction-eligibility-v1/verification.json',
    'experiments/instruction-eligibility-v1/invariant-audit.json',
    'paper/implementation-verification.json',
    'experiments/clause-factorial-v1/results.json',
    'experiments/clause-factorial-v1/summary.json',
    'experiments/clause-factorial-v1/verification.json',
    'experiments/prompt-synthesis-expanded-v1/prompt-audit.json',
    'experiments/prompt-synthesis-expanded-v1/plan.json',
    'experiments/paraphrase-contract-v1/results.json',
    'experiments/paraphrase-contract-v1/verification.json',
    'experiments/clause-normalization-v1/results.json',
    'experiments/clause-normalization-v1/verification.json',
    'experiments/clause-normalization-v1/development-replay.json',
    'experiments/keep-contract-validation-v1/results.json',
    'experiments/keep-contract-validation-v1/verification.json',
    'experiments/keep-contract-v2/results.json',
    'experiments/keep-contract-v2/verification.json',
    'experiments/request-contract-v3/results.json',
    'experiments/request-contract-v3/verification.json',
    'experiments/isolated-contract-v1/results.json',
    'experiments/isolated-contract-v1/verification.json',
    'experiments/keep-image-v1/summary.json',
    'experiments/keep-image-v1/verification.json',
    'experiments/keep-image-v1/paired-audit.json',
    'experiments/contract-image-v3/summary.json',
    'experiments/contract-image-v3/verification.json',
    'experiments/contract-image-v3/paired-audit.json',
    'experiments/contract-image-review-v1/summary.json',
    'experiments/contract-image-review-v1/verification.json',
    'experiments/compound-edit-v1/summary.json',
    'experiments/compound-edit-v1/verification.json',
)


HASH_FIELDS = ('sha256', 'source_sha256', 'sources_sha256',
               'frozen_inputs_verified', 'input_sha256')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_dependency_hashes(record, source_path, root=ROOT):
    """Check dependency digests stored relative to the repository or record."""
    for key in HASH_FIELDS:
        mapping = record.get(key, {})
        if not isinstance(mapping, dict):
            continue
        for filename, digest in mapping.items():
            if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
                continue
            candidates = (root / filename, source_path.parent / filename)
            assert any(p.is_file() and sha(p) == digest for p in candidates), (source_path, filename)


def audit(folder):
    manuscript = (folder / 'manuscript.ko.md').read_text()
    abstract = (folder / 'abstract.en.txt').read_text().strip()
    checked, sources, data = [], {}, {}
    manuscript_lines = set(manuscript.splitlines())

    def source(name):
        if name not in data:
            path = ROOT / name
            sources[name] = sha(path)
            data[name] = json.loads(path.read_text())
        return data[name]

    def expect(value, text=manuscript):
        assert value in text, f'Missing claim: {value}'
        checked.append(value)

    def row(cells):
        expected = '| ' + ' | '.join(map(str, cells)) + ' |'
        assert expected in manuscript_lines, f'Missing table row: {expected}'
        checked.append(expected)

    # Retain the evidence inventory and validate its frozen dependency hashes.
    for name in SOURCE_FILES:
        record = source(name)
        verify_dependency_hashes(record, ROOT / name)
        if 'passed' in record:
            assert record.get('passed'), name

    references = manuscript.split('## 참고문헌\n', 1)[1]
    assert re.findall(r'^\[(\d+)\]', references, re.M) == [str(n) for n in range(1, 13)]
    assert 'Meta, “Llama 3.2 Model Card,”' in references
    repository = 'https://github.com/kimmireu0220/inha-capstone'
    assert repository in manuscript.split('### 4.3 재현 자료\n', 1)[1]
    assert repository not in references
    cited = {int(number) for group in re.findall(r'\[([0-9,]+)\]', manuscript.split('## 참고문헌\n', 1)[0]) for number in group.split(',')}
    assert cited == set(range(1, 13)), cited
    citation_order = list(dict.fromkeys(int(number) for group in re.findall(r'\[([0-9,]+)\]', manuscript.split('## 참고문헌\n', 1)[0]) for number in group.split(',')))
    assert citation_order == list(range(1, 13)), citation_order
    body = manuscript.split('## 참고문헌\n', 1)[0]
    for phrase in ['턴', '원응답', '검증 대화 S', '추가 검증 T', '근거로 삼지 않았다',
                   '아직 확인이 필요', '추가 확인이 필요', '추가 검증이 필요', '합산하지 않']:
        assert phrase not in body, phrase
    assert not re.search(r'\bturns?\b', abstract, re.I)
    assert not re.search(r'\b[a-f0-9]{40}\b', manuscript)
    blocks = re.findall(r'(?m)^\|[^\n]+\|(?:\n\|[^\n]+\|)+', manuscript)
    assert len(blocks) == 6
    assert len(re.findall(r'^!\[', manuscript, re.M)) == 3
    for phrase in ['집계 후 반영', 'being evaluated']:
        assert phrase not in manuscript + abstract

    initial = source('paper/initial-portrait-verification.json')
    assert initial['people'] == initial['paired_endpoints'] == 6
    assert initial['sequential_outputs'] == 60 and initial['total_measured_outputs'] == 66
    assert initial['max_metric_replay_error'] < 1e-6
    assert sha(ROOT/'scripts/summarize_initial_portrait.py') == initial['verifier_sha256']
    for name, digest in initial['checked_images'].items():
        assert sha(ROOT/name) == digest
    expect('순차 편집의 위치 보정 LPIPS 평균은 ' + ', '.join(
        f"{stage}단계 {initial['stage_registered_means'][stage]['lpips']:.6f}"
        for stage in ['1', '5', '10']))
    expect('원본 기반 재생성은 위치 보정 MAE, SSIM, LPIPS 모두 6/6쌍에서')

    final = {m: source(f'experiments/single-extraction-validation-v1/results-{m}.json')['methods']
             for m in ['qwen3','llama32']}
    for model in final:
        selected = final[model]['single_extraction_checked']
        assert selected['correct_slots'] == 72 and selected['exact_final_dialogues'] == 3
        assert final[model]['json_first_only']['exact_turns'] == 3
        assert selected['exact_turns'] == 12
    expect('기본 검증 요청 12개에서도 첫 응답 단순 적용은 두 모델 모두 3/12, 제안 방법은 모두 12/12')

    extended = source('experiments/extended-state-validation-v1/summary.json')
    assert extended['complete'] and extended['requests'] == 96
    assert extended['dialogues'] == 12 and extended['completed_responses'] == 384
    assert extended['production_pipeline_replays'] == 192
    metrics = extended['metrics']
    for key, label in [('json_first_only', '첫 응답만 적용'),
                       ('json_review_then_first', '재검토 응답 우선'),
                       ('eligible_normalization', '추출·재검토+검사'),
                       ('single_extraction_checked', '한 번 추출+검사')]:
        row([label, metrics['qwen3'][key]['required_model_calls_per_request']] +
            [f"{metrics[m][key]['exact_turns']}/96" for m in ['qwen3', 'llama32']])
    for category, label in [('setup', '초기 설정'), ('replacement', '두 항목 변경'),
                            ('removal_keep', '삭제·유지'), ('restoration_keep', '복원·유지'),
                            ('negation', '부정 지시'), ('quotation', '인용문'),
                            ('conditional', '조건문'), ('direct_priority', '인용문 뒤의 직접 지시')]:
        row([label] + [f"{extended['by_category'][m][key][category]['correct']}/12"
                       for m, key in [('qwen3', 'json_first_only'), ('qwen3', 'single_extraction_checked'),
                                      ('llama32', 'json_first_only'), ('llama32', 'single_extraction_checked')]])
    for model in metrics:
        selected = metrics[model]['single_extraction_checked']
        for key in ['json_first_only', 'single_extraction_checked']:
            expect(f"{metrics[model][key]['exact_turns']}/96", abstract)
    comparisons = [extended['paired_comparisons'][m]['json_first_only'] for m in ['qwen3', 'llama32']]
    expect('정확도 차이는 Qwen3 ' + f"{comparisons[0]['difference_percentage_points']:.2f}%p, " +
           f"Llama {comparisons[1]['difference_percentage_points']:.2f}%p")
    expect('대화 단위 95% 구간은 각각 ' + '와 '.join(
        f'{low:.2f}–{high:.2f}%p' for low, high in
        [c['bootstrap_95_percentage_points'] for c in comparisons]))
    expect('Holm 보정 p값은 각각 ' +
           f"{comparisons[0]['holm_p_two_models']:.6f}과 {comparisons[1]['holm_p_two_models']:.6f}")
    expect('항목별 일치는 Qwen3 ' +
           f"{metrics['qwen3']['single_extraction_checked']['correct_slots']}/576, Llama " +
           f"{metrics['llama32']['single_extraction_checked']['correct_slots']}/576")
    expect('최종 상태 일치는 각각 ' +
           f"{metrics['qwen3']['single_extraction_checked']['exact_final_dialogues']}/12와 " +
           f"{metrics['llama32']['single_extraction_checked']['exact_final_dialogues']}/12")

    # The method example is an observed response and state transition, not an
    # invented illustration. Keep its request, prior, error and correction linked.
    example_records = source('experiments/extended-state-validation-v1/transcripts-qwen3.json')
    example_methods = source('experiments/extended-state-validation-v1/results-qwen3.json')['methods']
    example = example_records['F2-D3-3']
    expect(example['request'])
    assert json.loads(example['first']) == {'jacket': 'original', 'background': 'keep'}
    checked_rows = example_methods['single_extraction_checked']['rows']
    prior = next(r for r in checked_rows if r['dialogue'] == 'F2-D3' and r['turn'] == 2)['observed']
    result = next(r for r in checked_rows if r['dialogue'] == 'F2-D3' and r['turn'] == 3)
    plain = next(r for r in example_methods['json_first_only']['rows']
                 if r['dialogue'] == 'F2-D3' and r['turn'] == 3)
    assert prior['jacket'] == 'beige' and prior['background'] == 'garden'
    assert result['observed'] == prior == result['expected'] and result['exact']
    assert result['trace']['ignored_instructions']['jacket']['reason'] == 'quoted_text'
    assert plain['observed'] == {**prior, 'jacket': 'original'} and not plain['exact']
    expect('모델은 재킷을 ‘원본’, 배경을 ‘유지’로 추출하였다')
    expect('직전 값인 베이지색을 보존한다')
    expect('배경은 직접적인 유지 지시에 따라 정원으로 남는다')

    ablation = source('experiments/request-contract-v3/results.json')['methods']
    for key, label in [('baseline_restore','기준 방법'), ('keep_only','유지 규칙만'),
                       ('remove_only','삭제 규칙만'), ('keep_remove','유지·삭제 결합')]:
        d = ablation[key]
        row([label, f"{d['exact_turns']}/32", f"{d['correct_slots']}/192",
             f"{d['exact_final_dialogues']}/8", d['newly_corrupted_unchanged_slots']])
    clauses = source('experiments/clause-normalization-v1/results.json')['methods']
    n = clauses['normalized_atomic']['turns']
    expect('구절을 분리한 비교에서는 Qwen3의 일치 건수가 ' +
           f"{clauses['baseline_restore']['exact_turns']}/{n}에서 " +
           f"{clauses['normalized_atomic']['exact_turns']}/{n}으로 증가")
    restored = {}
    for model in ['qwen3', 'llama32']:
        d = source(f'experiments/operation-scope-validation-v1/results-{model}.json')['methods']
        n = d['expanded_normalization']['turns']
        restored[model] = f"{d['baseline_restore']['exact_turns']}/{n}에서 {d['expanded_normalization']['exact_turns']}/{n}"
    expect('복원 표현을 확장한 뒤 별도의 요청 32개에 적용한 결과는 ' +
           f"Qwen3 {restored['qwen3']}, Llama {restored['llama32']}")
    eligibility = {m: source(f'experiments/instruction-eligibility-validation-v1/results-{m}.json')['methods']
                   for m in ['qwen3', 'llama32']}
    d = eligibility['qwen3']; n = d['eligible_normalization']['turns']
    expect('실행 대상 검사 검증에서 Qwen3는 조건문·인용문을 실제 명령으로 적용하는 오류가 줄어 ' +
           f"{d['baseline_restore']['exact_turns']}/{n}에서 {d['eligible_normalization']['exact_turns']}/{n}으로 증가")
    d = eligibility['llama32']
    assert d['baseline_restore']['exact_turns'] == d['eligible_normalization']['exact_turns'] == 0
    expect(f"같은 검증의 Llama는 검사 전후 모두 0/{d['eligible_normalization']['turns']}")
    transfer = source('experiments/instruction-transfer-v1/summary.json')
    assert transfer['groups']['normalized_atomic']['unseen']['target_exact'] == 0
    expect('기존 규칙에 없는 복원 표현은 0/8')
    checks = source('experiments/instruction-eligibility-v1/invariant-audit.json')
    assert checks['passed'] and checks['cases'] == 1323; expect('1323')
    implementation = source('paper/implementation-verification.json')
    assert implementation['passed'] and implementation['replayed_requests'] == 24

    compound = source('experiments/compound-edit-v1/summary.json')
    for level in ['single', 'compound']:
        assert all(compound['groups'][key][level]['exact_turns'] == 16
                   for key in ['direct', 'review', 'guarded'])
    expect('표정만 지정한 조건과 표정·포즈 조건이 각각 모든 방법에서 16/16')
    mixed = {key: compound['groups'][key]['mixed'] for key in ['direct', 'review', 'guarded']}
    assert mixed['direct']['exact_turns'] == mixed['review']['exact_turns']
    expect('속성 지시를 섞은 조건은 최초 추출과 재검토가 각각 ' +
           f"{mixed['direct']['exact_turns']}/16, 규칙 보정은 {mixed['guarded']['exact_turns']}/16")
    expect('항목별 일치는 각각 ' + ', '.join(
        f"{mixed[key]['correct_slots']}/{mixed[key]['slots']}" for key in ['direct', 'review', 'guarded']))
    assert compound['post_hoc_remove_only_exact_turns'] == 48
    assert compound['post_hoc_operation_control']['first_exact'] == compound['post_hoc_operation_control']['review_exact'] == 7
    expect('삭제 규칙만 적용한 사후 재계산도 요청 48개가 모두 일치')
    expect('대조 요청 8개에서는 최초 추출과 재검토가 각각 7/8')

    for study, label in [('contract-image-v3','3B'),('contract-image-review-v1','7B')]:
        d = source(f'experiments/{study}/summary.json')['by_mode']
        expect(f"{label} 기준 {d['baseline_restore']['goals_satisfied']}/384와 결합 {d['keep_remove']['goals_satisfied']}/384")
        if label == '3B':
            expect(f"판단 불가는 3B에서 각각 {d['baseline_restore']['unknown_goals']}개와 {d['keep_remove']['unknown_goals']}개")
            expect('얼굴 코사인 평균은 기준 ' + f"{d['baseline_restore']['face_mean']:.6f}, 결합 {d['keep_remove']['face_mean']:.6f}")
        else:
            assert d['baseline_restore']['unknown_goals'] == d['keep_remove']['unknown_goals'] == 0
            expect('7B에서 모두 0개')

    prompt = source('experiments/prompt-state-image-v1/summary.json')
    assert prompt['complete'] and prompt['conditions'] == prompt['actual_image_calls'] == 18
    assert prompt['completed_image_evaluation_responses'] == 36
    length = source('experiments/prompt-state-image-v1/prompt-lengths.json')
    for key, label in [('full_history','전체 요청 이력'),('unchecked_state','검사 없이 저장한 조건'),('checked_state','검사 후 저장한 조건')]:
        d = length['final_request_means'][key]
        row([label]+[f"{d[x]:.2f}" for x in ['characters','words','tokens']])
        a,b = prompt['by_mode'][key],prompt['secondary_by_mode'][key]
        row([label,f"{a['goals_satisfied']}/36",a['unknown'],f"{b['goals_satisfied']}/36",b['unknown']])
        row([label,f"{a['identity_mean']:.6f}"]+[f"{a['aligned_means'][x]:.6f}" for x in ['mae','ssim','lpips']])
    reduction = 100*(1-length['final_request_means']['checked_state']['tokens']/length['final_request_means']['full_history']['tokens'])
    expect(f'{reduction:.2f}%'); expect('122.67', abstract)
    agreement = prompt['evaluator_agreement']
    expect(f"{agreement['equal_scores']}/108"); expect(f"{agreement['equal_both_scored']}/{agreement['both_scored']}")
    assert sum(r['parse_error'] is not None for r in prompt['rows']) == 5

    diagram = source('paper/figures/instruction-pipeline-provenance.json')
    verify_dependency_hashes(diagram, ROOT/'paper/figures/instruction-pipeline-provenance.json')
    assert sha(ROOT/diagram['script']) == diagram['script_sha256']
    for name, digest in diagram['outputs'].items():
        assert sha(ROOT/name) == digest, name

    provenance = source('paper/figures/figure-provenance.json')
    for figure in provenance['figures']:
        assert sha(folder/'figures'/figure['figure']) == figure['sha256']
        for item in figure['sources']:
            assert sha(ROOT/item['source']) == item['sha256']
    illustration = source('paper/figures/prompt-state-image-provenance.json')
    assert sha(ROOT/illustration['figure']) == illustration['figure_sha256']
    for item in illustration['sources']:
        assert sha(ROOT/item['source']) == item['sha256']
    return {'date':'2026-10-28','passed':True,
            'scope':'Numeric transcription and provenance QA, not independent scientific validation',
            'manuscript_sha256':sha(folder/'manuscript.ko.md'),
            'english_abstract_sha256':hashlib.sha256(abstract.encode()).hexdigest(),
            'checked_values':checked,
            'figure_provenance_sha256':sha(folder/'figures/figure-provenance.json'),
            'sources':[{'name':n,'path':n,'sha256':h} for n,h in sources.items()]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,default=ROOT/'paper')
    args = parser.parse_args()
    folder = args.source_dir.resolve()
    result = audit(folder)
    (folder/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(f"Paper audit passed: {len(result['checked_values'])} claims/rows")
