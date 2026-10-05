"""Apply valid fields from the latest parseable patch; reject invalid fields only.

No gold annotation or prior expected state is available to this component.
Omissions/keeps never resurrect a field from an older response.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'local-studio'))
from request_state import unique_object, patch_operations, apply_operations


def update(state, request, raws, atomic=False):
    errors, patch, selected = {}, None, None
    for i in reversed(range(len(raws))):
        try:
            raw = raws[i]
            candidate = json.loads(raw[raw.find('{'):raw.rfind('}') + 1], object_pairs_hook=unique_object)
            if not isinstance(candidate, dict):
                raise ValueError('Expected flat object')
            patch, selected = candidate, i
            break
        except (ValueError, TypeError) as exc:
            errors[f'parse_{i}'] = str(exc)
    if patch is None:
        return dict(state), errors, selected
    if 'clarification' in patch:
        return dict(state), {'clarification': str(patch['clarification'])}, selected
    updated = dict(state)
    invalid = False
    for field, value in patch.items():
        if field in state and (value == state[field] or value == 'keep'):
            continue
        try:
            if field not in state or not isinstance(value, str):
                raise ValueError('Unknown field or non-scalar value')
            operations = patch_operations({field: value}, request)
            updated = apply_operations(updated, operations, request)
        except (ValueError, TypeError, KeyError) as exc:
            errors[field], invalid = str(exc), True
    return (dict(state) if atomic and invalid else updated), errors, selected
