"""Conservative explicit KEEP constraints; use only the method's own prior state.

This bounded lexical guard abstains on quoted, conditional, negative, original-
valued, or later-rementioned clauses. It is not a general instruction parser.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'local-studio'))
from request_state import MENTIONS

VERBS = re.compile(r"\b(?:(?:do\s+not|don't|never)\s+)?(?:keep|keeping|leave|leaving|retain|retaining|"
                   r"restore|restoring|reset|resetting|return|returning|revert|reverting|remove|removing|"
                   r"take|taking|use|using|add|adding|wear|wearing|replace|replacing|change|changing|"
                   r"switch|switching|put|putting|set|setting)\b", re.I)
KEEP = re.compile(r'^(?:keep|keeping|leave|leaving|retain|retaining)$', re.I)
UNSAFE = re.compile(r"\b(?:if|unless|maybe|perhaps|not|never|without|don't)\b", re.I)


def obligations(request):
    if any(char in request for char in ['"', '“', '”', '`']):
        return {}
    verbs = list(VERBS.finditer(request))
    rules = {}
    for i, match in enumerate(verbs):
        if not KEEP.fullmatch(match.group()):
            continue
        sentence_start = max(request.rfind('.', 0, match.start()), request.rfind(';', 0, match.start())) + 1
        if UNSAFE.search(request[sentence_start:match.start()]):
            continue
        end = verbs[i + 1].start() if i + 1 < len(verbs) else len(request)
        fragment = re.split(r'[.;]', request[match.start():end], maxsplit=1)[0]
        if UNSAFE.search(fragment) or re.search(r'\boriginal\b', fragment, re.I):
            continue
        remainder = request[match.start() + len(fragment):]
        for field, pattern in MENTIONS.items():
            if re.search(pattern, fragment, re.I) and not re.search(pattern, remainder, re.I):
                rules[field] = {'evidence': fragment.strip()}
    return rules


def enforce(state, request, prior):
    updated = dict(state)
    rules = obligations(request)
    for field in rules:
        updated[field] = prior[field]
    return updated, rules
