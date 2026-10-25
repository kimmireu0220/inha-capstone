"""Normalize bounded explicit instruction clauses before existing validation.

No model calls or reference answers. Unknown objects/conditional clauses remain
unchanged. Historical reducers are imported, not edited.
"""
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('clause_contract_source', ROOT.parent / 'request-contract-v3/run.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

START = re.compile(r"\b(?:do not (?:change|alter)|don't (?:change|alter)|bring|preserv(?:e|ing)|"
                   r"retain(?:ing)?|leav(?:e|ing)|keep(?:ing)?|restor(?:e|ing)|return(?:ing)?|"
                   r"remov(?:e|ing)|take|delete|exclude|use|swap|switch|replace|change|make|choose|set|add|wear|put)\b", re.I)
OBJECT_WORDS = source.contract.keep.SAFE | {'or', 'setting', 'scene'}


def normalize(request):
    if any(c in request for c in ['"', '“', '”', '`']):
        return request, []
    pieces, evidence = [], []
    for sentence in re.split(r'[.;]', request):
        if not sentence.strip():
            continue
        matches = list(START.finditer(sentence))
        # Do not turn negation or conditional instructions into obligations.
        risk = re.sub(r"\b(?:do not|don't) (?:change|alter)\b", '', sentence, flags=re.I)
        if source.contract.keep.v1.UNSAFE.search(risk):
            pieces.append(sentence.strip())
            continue
        if not matches:
            pieces.append(sentence.strip())
            continue
        prefix = sentence[:matches[0].start()].strip()
        if prefix:
            pieces.append(prefix)
        for i, match in enumerate(matches):
            end = matches[i+1].start() if i+1 < len(matches) else len(sentence)
            fragment = sentence[match.start():end].strip(' ,')
            fragment = re.sub(r'[,\s]+(?:and|but|while|then|without)$', '', fragment, flags=re.I).strip(' ,')
            original = fragment
            verb = match.group().lower()
            body = fragment[len(match.group()):].strip()
            if verb == 'bring':
                if body.lower().startswith('back the original '):
                    fragment = 'Restore the original ' + body[len('back the original '):]
                else:
                    moved = re.fullmatch(r'(.+?) back to (?:the )?original(?: photo)?', body, re.I)
                    if moved:
                        fragment = 'Restore ' + moved[1] + ' to the original'
            elif verb.startswith(('leave', 'leaving', 'retain', 'keep', 'preserv', 'do not', "don't")):
                objects = re.sub(r'\s+(?:unchanged|as (?:it|they) (?:is|are)|as is|the same)$', '', body, flags=re.I)
                objects = re.sub(r'\bor\b', 'and', objects, flags=re.I)
                objects = re.sub(r'\b(?:scene|setting)\b', 'background', objects, flags=re.I)
                tokens = set(re.findall(r'[a-z]+', objects.lower()))
                fields = [k for k, pattern in source.contract.keep.v1.MENTIONS.items()
                          if re.search(pattern, objects, re.I)]
                explicit = verb.startswith(('preserv', 'retain', 'do not', "don't")) or objects != body
                if explicit and fields and tokens <= OBJECT_WORDS:
                    fragment = 'Keep ' + objects + ' unchanged'
                elif verb == 'leaving':
                    fragment = 'Leave ' + body
            if fragment != original:
                evidence.append({'original': original, 'normalized': fragment})
            pieces.append(fragment)
    return ('. '.join(pieces) + '.' if evidence else request), evidence


def update(prior, request, raws, atomic=False):
    normalized, evidence = normalize(request)
    # Validate fields independently so one malformed operation cannot cancel
    # other valid changes. This component already existed in the T comparison.
    if atomic:
        operations, selected = source.base.noop.select_noop(raws, normalized, prior)
        state = source.base.apply_operations(prior, operations, normalized)
        errors = {} if selected is not None else {'patch': 'No valid patch'}
    else:
        state, errors, selected = source.base.method.update(prior, normalized, raws, atomic=False)
    state, reset = source.base.contract.enforce(state, normalized)
    rules = {}
    clauses = list(re.finditer(r'[^.;]+', normalized))
    for clause in clauses:
        candidate, found = source.contract.enforce(state, clause.group().strip(), prior)
        for field, rule in found.items():
            pattern = source.contract.keep.v1.MENTIONS[field]
            if not re.search(pattern, normalized[clause.end():], re.I):
                state[field] = candidate[field]
                rules[field] = rule
    return state, dict(normalized_request=normalized, normalization=evidence,
                       errors=errors, selected=selected, reset=reset, rules=rules)
