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
    assert render['all_pages_visually_reviewed'] and render['pages'] == 7

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
    for study in ['coverage-repair-v1', 'coverage-validation-v1']:
        folder = ROOT / 'experiments' / study
        verification = json.loads((folder / 'verification.json').read_text())
        assert verification['passed'], study
        for name, expected in verification['sha256'].items():
            assert digest(folder / name) == expected, f'{study}/{name}'
        manifest = 'method-freeze.json' if (folder / 'method-freeze.json').exists() else 'frozen.json'
        for name, expected in json.loads((folder / manifest).read_text()).items():
            if name != 'model_revision':
                assert digest(ROOT / name) == expected, name
    print(f'Consistency passed: {len(evidence["sources"])} evidence sources, '
          f'{len(current)} current documents, paper artifact hashes, 40-slide manifest, '
          'AI evaluation setup and two request-repair studies')


if __name__ == '__main__':
    check()
