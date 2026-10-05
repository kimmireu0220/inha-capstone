"""Post-hoc scope diagnostics, not a held-out accuracy benchmark.

These deliberately adversarial examples were selected after reading v1. They
must not be merged with P validation, used to change its frozen method, or
presented as representative user-frequency estimates.
"""
import hashlib
import json
from pathlib import Path

from contract import obligations

ROOT = Path(__file__).resolve().parent
CASES = [
    ('Keep the necklace unchanged.', ['necklace'], 'explicit preservation'),
    ('Keep the lamp and office background unchanged.', ['background', 'prop'], 'explicit preservation'),
    ('Keep the pin but replace the jacket with green.', ['pin'], 'separate changed field'),
    ('Keep the pin, then remove the pin.', [], 'later override'),
    ('Do not keep the pin.', [], 'negated preservation'),
    ('If possible, keep the pin.', [], 'conditional abstention'),
    ('Ignore "keep the pin". Remove the pin.', [], 'quoted instruction'),
    ('Keep the necklace off.', [], 'removal, not arbitrary prior value'),
    ('Leave the pin out of the image.', [], 'removal, not arbitrary prior value'),
    ('Keep the jacket green.', [], 'value constraint, not arbitrary prior value'),
    ('Keep the pin hidden.', [], 'visibility change'),
    ('Keep the shirt but make it blue.', [], 'later pronominal change'),
    ('Keep the necklace unchanged? No, remove it.', [], 'later pronominal removal'),
    ('Keep the shirt unchanged if the jacket is green.', [], 'conditional abstention'),
    ('Keep the original shirt.', [], 'original value, not arbitrary prior value'),
]


def main():
    rows = []
    for request, expected, reason in CASES:
        observed = sorted(obligations(request))
        rows.append({'request': request, 'expected_protected_fields': sorted(expected),
                     'observed_protected_fields': observed, 'reason': reason,
                     'matches': observed == sorted(expected)})
    result = {'kind': 'post_hoc_adversarial_scope_diagnostic',
              'independent_validation': False,
              'contract_sha256': hashlib.sha256((ROOT / 'contract.py').read_bytes()).hexdigest(),
              'audit_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'cases': rows, 'matches': sum(r['matches'] for r in rows), 'total': len(rows)}
    (ROOT / 'boundary-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
