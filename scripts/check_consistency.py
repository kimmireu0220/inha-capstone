"""Read-only checks for the current paper, evaluation setup and deck manifest.

Run paper/audit.py first to verify exact numeric table transcription. This check
does not regenerate experimental results or claim to inspect the live deck.
"""
from pathlib import Path
import hashlib
import json
import re
import zipfile
from pypdf import PdfReader
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    evidence = load('paper/evidence.json')
    assert evidence['passed']
    assert digest(ROOT / 'paper/manuscript.ko.md') == evidence['manuscript_sha256']
    abstract = (ROOT / 'paper/abstract.en.txt').read_text().strip()
    assert hashlib.sha256(abstract.encode()).hexdigest() == evidence['english_abstract_sha256']
    for source in evidence['sources']:
        assert digest(ROOT / source['path']) == source['sha256'], source['path']

    render = load('paper/render-verification.json')
    for filename, key in [('manuscript.ko.md', 'manuscript_sha256'),
                          ('manuscript.inha.docx', 'docx_sha256'),
                          ('manuscript.inha.pdf', 'pdf_sha256')]:
        assert digest(ROOT / 'paper' / filename) == render[key], filename
    assert render['all_pages_visually_reviewed']
    assert render['pages'] == len(PdfReader(ROOT / 'paper/manuscript.inha.pdf').pages)
    assert render['body_columns'] == 2
    assert render['reviewed_pages'] == list(range(1, render['pages'] + 1))
    assert digest(ROOT / 'paper/figures/figure-provenance.json') == evidence['figure_provenance_sha256']

    automatic = load('experiments/state-tracking-v2/summary.json')
    control = load('experiments/state-format-control-v1/summary.json')
    assert automatic['rater_type'] == control['rater_type'] == 'AI'
    for summary, base in [(automatic, ROOT / 'experiments/state-tracking-v2'),
                          (control, ROOT / 'experiments')]:
        for name, expected in summary['source_sha256'].items():
            assert digest(base / name) == expected, name
    deck = load('artifacts/slides-verification.json')
    assert deck['slides'] == len(deck['slide_ids']) == 10
    assert deck['visual_check']['reviewed_slides'] == list(range(1, 11))
    assert not deck['visual_check']['visible_overlap_or_clipping_found']
    assert deck['editable_evidence'] == {'tables': 3, 'images': 8, 'notes': 10}
    for group in ['source_sha256', 'script_sha256']:
        for name, expected in deck[group].items():
            assert digest(ROOT / name) == expected, name
    assert deck['source_sha256']['paper/manuscript.ko.md'] == evidence['manuscript_sha256']

    current = [ROOT / name for name in ['CURRENT_STATUS.md', 'RESEARCH_INDEX.md',
               'paper/README.md', 'paper/manuscript.ko.md', 'paper/manuscript.inha.md',
               'paper/abstract.en.txt', 'artifacts/README.md', 'RESEARCH_DESIGN.md',
               'local-studio/README.md', 'scripts/GOOGLE_SLIDES_API.md',
               'artifacts/실험_프롬프트와_상세수치.md']]
    for folder in ['state-tracking-v1', 'state-tracking-v2', 'state-format-control-v1']:
        current.extend((ROOT / 'experiments' / folder).glob('*.md'))
        assert not (ROOT / 'experiments' / folder / 'human-ratings.csv').exists()
    for study in ['paraphrase-contract-v1', 'clause-normalization-v1', 'clause-factorial-v1']:
        current.extend((ROOT / 'experiments' / study).glob('*.md'))
        folder = ROOT / 'experiments' / study
        verified = json.loads((folder / 'verification.json').read_text())
        assert verified['passed']
        assert digest(folder / 'report.py') == verified['verifier_sha256']
        for name, expected in verified['sha256'].items():
            assert digest(folder / name) == expected, f'{study}/{name}'
        frozen = json.loads((folder / 'frozen.json').read_text())
        for name, expected in frozen['sha256'].items():
            assert digest(ROOT / name) == expected, name
    development = load('experiments/clause-normalization-v1/development-replay.json')
    assert development['posthoc_development'] and development['additional_model_calls'] == 0
    for name, expected in development['sources_sha256'].items():
        assert digest(ROOT / name) == expected, name
    invariants = load('experiments/clause-normalization-v1/invariant-audit.json')
    assert invariants['passed'] and invariants['actual_model_calls'] == 0 and not invariants['failures']
    assert digest(ROOT / 'scripts/audit_clause_invariants.py') == invariants['verifier_sha256']
    for name, expected in invariants['source_sha256'].items():
        assert digest(ROOT / name) == expected, name
    plain = load('experiments/clause-normalization-v1/plain-patch-comparison.json')
    assert plain['posthoc_analysis'] and plain['additional_model_calls'] == 0
    assert digest(ROOT / 'scripts/compare_plain_patch.py') == plain['verifier_sha256']
    assert digest(ROOT / 'local-studio/request_state.py') == plain['reducer_schema_sha256']
    for name, expected in plain['source_sha256'].items():
        assert digest(ROOT / name) == expected, name
    forbidden = re.compile(r'independent_human|human-ratings\.csv|독립 인간 평가|사람용 양식')
    for path in current:
        contents = path.read_text()
        assert not forbidden.search(contents), str(path.relative_to(ROOT))
        for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^\s)]+)\)', contents):
            if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                continue
            local = unquote(target.split('#')[0])
            assert (path.parent / local).exists(), f'{path.relative_to(ROOT)} -> {local}'
    with zipfile.ZipFile(ROOT / 'paper/manuscript.inha.docx') as archive:
        assert not forbidden.search(archive.read('word/document.xml').decode())
    compound = ROOT / 'experiments/compound-edit-v1'
    compound_verified = json.loads((compound / 'verification.json').read_text())
    assert compound_verified['passed'] and compound_verified['turns'] == 48
    for name, expected in compound_verified['sha256'].items():
        assert digest(compound / name) == expected, name
    for name, expected in json.loads((compound / 'frozen.json').read_text())['sha256'].items():
        assert digest(ROOT / name) == expected, name
    for manifest in ['image-evaluation-frozen.json', 'operation-control-frozen.json']:
        for name, expected in json.loads((compound / manifest).read_text())['sha256'].items():
            assert digest(compound / name) == expected, name
    plan = json.loads((compound / 'image-plan.json').read_text())
    assert digest(compound / 'image_protocol.md') == plan['protocol_sha256']
    for item in plan['conditions']:
        assert digest(ROOT / item['reference']) == item['reference_sha256']
    verified_studies = ['coverage-repair-v1', 'coverage-validation-v1',
                        'action-plan-v2', 'action-plan-validation-v1',
                        'restore-contract-validation-v1', 'slot-isolation-validation-v1',
                        'keep-contract-validation-v1', 'keep-contract-v2', 'request-contract-v3',
                        'isolated-contract-v1']
    for study in verified_studies:
        folder = ROOT / 'experiments' / study
        verification = json.loads((folder / 'verification.json').read_text())
        assert verification['passed'], study
        for name, expected in verification['sha256'].items():
            assert digest(folder / name) == expected, f'{study}/{name}'
        manifest = 'method-freeze.json' if (folder / 'method-freeze.json').exists() else 'frozen.json'
        for name, expected in json.loads((folder / manifest).read_text()).items():
            if name != 'model_revision':
                assert digest(ROOT / name) == expected, name
    transfer = ROOT / 'experiments/instruction-transfer-v1'
    transfer_verification = json.loads((transfer / 'verification.json').read_text())
    assert transfer_verification['passed']
    assert transfer_verification['requests'] == 48 and transfer_verification['actual_model_calls'] == 96
    for name, expected in transfer_verification['sha256'].items():
        assert digest(transfer / name) == expected, name
    for name, expected in json.loads((transfer / 'frozen.json').read_text())['sha256'].items():
        assert digest(ROOT / name) == expected, name
    for study, calls, requests in [('operation-scope-validation-v1', 128, 32),
                                   ('instruction-eligibility-validation-v1', 64, 16),
                                   ('single-extraction-validation-v1', 48, 12)]:
        folder = ROOT / 'experiments' / study
        verification = json.loads((folder / 'verification.json').read_text())
        assert verification['passed']
        assert verification['actual_model_calls'] == calls and verification['requests_per_model'] == requests
        for name, expected in verification['sha256'].items():
            assert digest(folder / name) == expected, name
        for name, expected in json.loads((folder / 'frozen.json').read_text())['sha256'].items():
            assert digest(ROOT / name) == expected, name
    implementation = load('paper/implementation-verification.json')
    assert implementation['passed'] and implementation['replayed_requests'] == 24
    assert implementation['actual_model_calls'] == 0
    for name, expected in implementation['source_sha256'].items():
        assert digest(ROOT / name) == expected, name
    # Preserve the rejected first candidate and the explicitly post-hoc replay.
    for name, expected in load('experiments/action-plan-v1/frozen.json').items():
        if name != 'model_revision':
            assert digest(ROOT / name) == expected, name
    restore = load('experiments/restore-contract-v1/results.json')
    assert restore['posthoc_development'] and restore['additional_model_calls'] == 0
    for name, expected in restore['sha256'].items():
        assert digest(ROOT / name) == expected, name
    isolation = load('experiments/slot-isolation-v1/results.json')
    assert isolation['posthoc_development'] and isolation['additional_model_calls'] == 0
    for name, expected in isolation['sha256'].items():
        assert digest(ROOT / name) == expected, name
    keep = load('experiments/keep-contract-v1/results.json')
    assert keep['posthoc_development'] and keep['additional_model_calls'] == 0
    for name, expected in keep['sha256'].items():
        assert digest(ROOT / name) == expected, name
    input_audit = load('experiments/slot-isolation-validation-v1/image-input-audit.json')
    assert input_audit['different_prompt_snapshots'] == 0 and input_audit['new_images_generated'] == 0
    for name, expected in input_audit['source_sha256'].items():
        assert digest(ROOT / 'experiments/slot-isolation-validation-v1' / name) == expected, name
    prepared = load('experiments/action-image-v1/prepared.json')
    for name, expected in prepared['inputs'].items():
        assert digest(ROOT / name) == expected, name
    assert len(prepared['conditions']) == prepared['condition_count'] == 48
    assert len({row['job'] for row in prepared['conditions']}) == prepared['unique_prompt_reference_jobs']
    for study, jobs in [('keep-image-v1', 68), ('contract-image-v3', 66)]:
        native = ROOT / 'experiments' / study
        verified = json.loads((native / 'verification.json').read_text())
        assert verified['passed'] and verified['conditions'] == 128 and verified['unique_jobs'] == jobs
        for name, expected in verified['sha256'].items():
            assert digest(native / name) == expected, name
        assert digest(ROOT / 'experiments/action-image-v1/verify_native.py') == verified['verifier_sha256']
    review = ROOT / 'experiments/contract-image-review-v1'
    for name, expected in json.loads((review / 'frozen.json').read_text())['sha256'].items():
        assert digest(ROOT / name) == expected, name
    review_status = 'pending'
    if (review / 'verification.json').exists():
        reviewed = json.loads((review / 'verification.json').read_text())
        assert reviewed['passed'] and reviewed['conditions'] == 128
        assert reviewed['unique_evaluation_inputs'] == 68 and reviewed['post_hoc']
        for name, expected in reviewed['sha256'].items():
            assert digest(review / name) == expected, name
        report = json.loads((review / 'report-verification.json').read_text())
        for filename, key in [('summary.json', 'summary_sha256'),
                              ('RESULTS.md', 'report_sha256'),
                              ('report_text.py', 'script_sha256')]:
            assert digest(review / filename) == report[key], filename
        review_status = 'complete'
    print(f'Consistency passed: {len(evidence["sources"])} evidence sources, '
          f'{len(current)} current documents, paper artifact hashes, aligned 10-slide manifest, '
          f'AI evaluation setup and {len(verified_studies) + 7} verified text studies; '
          f'rejected candidate, post-hoc development and prepared image inputs preserved; 7B review {review_status}')


if __name__ == '__main__':
    check()
