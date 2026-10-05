"""Bounded preservation and removal obligations, with evidence spans.

This is a deterministic guard for explicitly supported clauses, not a general
semantic parser. Unsupported expressions remain with the common LLM reducer.
"""
import importlib.util
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parents[1] / 'keep-contract-v2/contract.py'
spec = importlib.util.spec_from_file_location('request_v3_keep', SOURCE)
keep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keep)
REMOVABLE = {'jacket', 'pin', 'necklace', 'prop'}


def removals(request):
    if any(char in request for char in ['"', '“', '”', '`']):
        return {}
    if re.search(r'\b(?:it|them|its|their|these|those)\b', request, re.I):
        return {}
    verbs = list(keep.v1.VERBS.finditer(request))
    result = {}
    for i, verb in enumerate(verbs):
        if verb.group().lower() not in {'remove', 'removing'}:
            continue
        start = max(request.rfind('.', 0, verb.start()), request.rfind(';', 0, verb.start())) + 1
        if keep.v1.UNSAFE.search(request[start:verb.start()]):
            continue
        end = verbs[i + 1].start() if i + 1 < len(verbs) else len(request)
        fragment = re.split(r'[.;]', request[verb.start():end], maxsplit=1)[0]
        body = fragment[len(verb.group()):].strip().rstrip(',').strip()
        body = re.sub(r'[,\s]+(?:and|but|while|then)\s*$', '', body, flags=re.I)
        if not body or not set(re.findall(r'[a-z]+', body.lower())) <= keep.SAFE:
            continue
        fields = {field for field, pattern in keep.v1.MENTIONS.items() if re.search(pattern, body, re.I)}
        if not fields or not fields <= REMOVABLE:
            continue
        remainder = request[verb.start() + len(fragment):]
        for field in fields:
            if not re.search(keep.v1.MENTIONS[field], remainder, re.I):
                result[field] = {'evidence': fragment.strip(), 'value': 'none'}
    return result


def enforce(state, request, prior, use_keep=True, use_remove=True):
    updated = dict(state)
    rules = {}
    if use_keep:
        updated, protected = keep.enforce(updated, request, prior)
        rules.update({field: {**rule, 'value': prior[field], 'operation': 'keep'} for field, rule in protected.items()})
    if use_remove:
        for field, rule in removals(request).items():
            updated[field] = 'none'
            rules[field] = {**rule, 'operation': 'remove'}
    return updated, rules
