"""Opt-in protection for explicit, bounded 'X unchanged' clauses only.

No natural-language generality is claimed. Unsupported or pronominal requests
abstain; the ordinary extraction/review result remains in force.
"""
import importlib.util
from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parents[1] / 'keep-contract-v1/contract.py'
spec = importlib.util.spec_from_file_location('keep_v2_predecessor', SOURCE)
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)
SAFE = set('the a an and navy beige green gray grey white ivory silver gold red blue '
           'circular circle square triangular triangle round teardrop viewer left right '
           'lapel pin pins necklace pendant blazer jacket shirt sweater crew neck '
           'plant lamp floor bench office library garden pale brick studio background'.split())


def obligations(request):
    # Do not attempt to resolve later "remove it" or "make it blue" changes.
    if re.search(r'\b(?:it|them|its|their|these|those)\b', request, re.I):
        return {}
    result = {}
    for field, rule in v1.obligations(request).items():
        match = re.fullmatch(r'(?:keep|keeping|leave|leaving|retain|retaining)\s+'
                             r'(.+?)\s+unchanged\s*,?\s*(?:(?:and|but|while)\s*)?',
                             rule['evidence'], re.I)
        if match and set(re.findall(r'[a-z]+', match[1].lower())) <= SAFE:
            result[field] = rule
    return result


def enforce(state, request, prior):
    updated = dict(state)
    rules = obligations(request)
    for field in rules:
        updated[field] = prior[field]
    return updated, rules
