"""Constructed finite-schema reducer checks, not new model observations.

Reference updates are generated from the case construction, independently of
the normalizer. Historical frozen implementations remain unchanged.
"""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD_PATH = ROOT / 'experiments/clause-normalization-v1/method.py'
spec = importlib.util.spec_from_file_location('invariant_subject', METHOD_PATH)
method = importlib.util.module_from_spec(spec)
spec.loader.exec_module(method)

NOUNS = dict(jacket='blazer', top='shirt', pin='pin', necklace='necklace',
             background='background', prop='plant')
PRIORS = [
    dict(method.source.base.INITIAL),
    dict(jacket='gray', top='navy_sweater', pin='blue_circle_left',
         necklace='gold_round', background='library', prop='plant'),
    dict(jacket='none', top='ivory_crewneck', pin='none',
         necklace='none', background='garden', prop='none'),
]


def cases():
    for prior_index, prior in enumerate(PRIORS):
        for reset, keep in itertools.permutations(NOUNS, 2):
            for template in [
                'Return the {reset} to the original photo, leaving the {keep} unchanged.',
                'Restore the original {reset}, preserving the {keep}.',
                'Bring back the original {reset}. Do not alter the {keep}.',
                'Preserve the {keep}. Bring the {reset} back to the original photo.',
            ]:
                request = template.format(reset=NOUNS[reset], keep=NOUNS[keep])
                yield dict(group='one_restore_one_keep', prior_index=prior_index, prior=prior,
                           request=request, patch={reset: 'original'}, updates={reset: 'original'})
        for resets in itertools.combinations(NOUNS, 2):
            for keep in (field for field in NOUNS if field not in resets):
                names = ' and '.join('the '+NOUNS[k] for k in resets)
                for template in [
                    'Return {names} to the original photo, leaving the {keep} unchanged.',
                    'Bring {names} back to the original photo. Preserve the {keep}.',
                    'Do not change the {keep}. Restore {names} to the original.',
                ]:
                    request = template.format(names=names, keep=NOUNS[keep])
                    updates = dict.fromkeys(resets, 'original')
                    yield dict(group='two_restore_one_keep', prior_index=prior_index, prior=prior,
                               request=request, patch=updates, updates=updates)
        for field in ['jacket', 'pin', 'necklace', 'prop']:
            noun = NOUNS[field]
            for request, value in [
                (f'Preserve the {noun}. Remove the {noun}.', 'none'),
                (f'Remove the {noun}. Restore the original {noun}.', 'original'),
                (f'Bring back the original {noun}. Remove the {noun}.', 'none'),
                (f'Remove the {noun}. Actually, keep the {noun} unchanged.', prior[field]),
            ]:
                patch = {field: 'keep' if value == prior[field] else value}
                yield dict(group='later_instruction', prior_index=prior_index, prior=prior,
                           request=request, patch=patch, updates={field: value})
        for request in [
            'Do not remove the plant. Preserve the pin.',
            'Never restore the original shirt. Preserve the plant.',
            'Perhaps remove the necklace. Do not alter the plant.',
            'If requested, remove the plant. Preserve the pin.',
            '"Remove the necklace" is quoted text. Preserve the plant.',
        ]:
            yield dict(group='no_unconditional_change', prior_index=prior_index, prior=prior,
                       request=request, patch={}, updates={})


def audit():
    groups, failures = {}, []
    for case in cases():
        prior = dict(case['prior'])
        expected = dict(prior, **case['updates'])
        raw = json.dumps(case['patch'])
        actual, trace = method.update(prior, case['request'], [raw, raw])
        # Correct model responses must remain correct; applying them must not
        # mutate the caller's state. No parser output constructs the reference.
        passed = actual == expected and prior == case['prior']
        group = groups.setdefault(case['group'], {'cases': 0, 'passed': 0})
        group['cases'] += 1
        group['passed'] += passed
        if not passed:
            failures.append(dict(**case, expected=expected, actual=actual, trace=trace))
    frozen = json.loads((METHOD_PATH.parent / 'frozen.json').read_text())['sha256']
    sources = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in frozen}
    assert sources == frozen, 'Historical frozen inputs changed'
    return dict(scope='Deterministic reducer verification using constructed correct responses; no model calls',
                actual_model_calls=0, passed=not failures, groups=groups, failures=failures,
                source_sha256=sources,
                verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


if __name__ == '__main__':
    result = audit()
    target = ROOT / 'experiments/clause-normalization-v1/invariant-audit.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ['passed', 'groups']}, indent=2))
    if not result['passed']:
        print(json.dumps(result['failures'][:3], ensure_ascii=False, indent=2))
        raise SystemExit(1)
