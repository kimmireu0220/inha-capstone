"""Read-only checks for the current paper, evaluation setup and deck manifest.

Run paper/audit.py first to verify exact numeric table transcription. This check
does not regenerate experimental results or claim to inspect the live deck.
"""
from pathlib import Path
import hashlib
import json
import re
import zipfile
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
    assert render['all_pages_visually_reviewed'] and render['pages'] == 6
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
    assert deck['slides'] == deck['main_slides'] + deck['appendix_slides'] == 40
    alignment = deck['paper_alignment']
    modes = ['agent', 'tracked', 'structured']
    for field, source in [('primary_goals', 'primary_ai'), ('secondary_goals', 'secondary_ai')]:
        assert alignment[field] == [control[source]['by_mode'][mode]['achieved'] for mode in modes]
    assert alignment['arcface'] == [round(control['primary_ai']['by_mode'][mode]['identity_mean'], 6)
                                    for mode in modes]
    assert alignment['goal_denominator_per_method'] == 288
    assert alignment['independent_people'] == control['independent_people'] == automatic['independent_people'] == 6

    current = [ROOT / name for name in ['CURRENT_STATUS.md', 'RESEARCH_INDEX.md',
               'paper/README.md', 'paper/manuscript.ko.md', 'paper/manuscript.inha.md',
               'paper/abstract.en.txt', 'artifacts/README.md']]
    for folder in ['state-tracking-v1', 'state-tracking-v2', 'state-format-control-v1']:
        current.extend((ROOT / 'experiments' / folder).glob('*.md'))
        assert not (ROOT / 'experiments' / folder / 'human-ratings.csv').exists()
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
          f'{len(current)} current documents, paper artifact hashes, historical 40-slide manifest (live update pending), '
          f'AI evaluation setup and {len(verified_studies)} verified text studies; '
          f'rejected candidate, post-hoc development and prepared image inputs preserved; 7B review {review_status}')


if __name__ == '__main__':
    check()
