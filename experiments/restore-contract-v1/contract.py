"""Conservative, explicit original-restoration constraints for a bounded edit language.

This is a rule-based component, not a claim of general semantic understanding.
Quoted, conditional and negated restoration clauses are left to the underlying
model. A later mention of a slot prevents overriding that slot.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'local-studio'))
from request_state import MENTIONS

VERBS = re.compile(r"\b(?:(?:do\s+not|don't|never)\s+)?(?:restore|reset|return|revert|keep|leave|retain|remove|take|use|add|wear|replace|change|switch|put)\b", re.I)
RESET = re.compile(r'^(?:restore|reset|return|revert)$', re.I)
UNSAFE = re.compile(r"\b(?:if|unless|maybe|perhaps|not|never|without|don't)\b", re.I)


def obligations(request):
    if any(char in request for char in ['"', '“', '”', '`']):
        return {}
    matches = list(VERBS.finditer(request))
    resolved = {}
    for i, match in enumerate(matches):
        if not RESET.fullmatch(match.group()):
            continue
        sentence_start = max(request.rfind('.', 0, match.start()), request.rfind(';', 0, match.start())) + 1
        # Conditional/negative context before the verb is not a hard constraint.
        if UNSAFE.search(request[sentence_start:match.start()]):
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(request)
        fragment = request[match.start():end]
        fragment = re.split(r'[.;]', fragment, maxsplit=1)[0]
        if UNSAFE.search(fragment) or not re.search(r'\boriginal\b', fragment, re.I):
            continue
        fragment_end = match.start() + len(fragment)
        for field, pattern in MENTIONS.items():
            if re.search(pattern, fragment, re.I) and not re.search(pattern, request[fragment_end:], re.I):
                resolved[field] = {'value': 'original', 'evidence': fragment.strip()}
    return resolved


def enforce(state, request):
    updated = dict(state)
    rules = obligations(request)
    for field in rules:
        updated[field] = 'original'
    return updated, rules
