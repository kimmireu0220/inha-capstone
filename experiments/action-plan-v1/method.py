"""Separate edit actions from categorical values; compile validated slot updates."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'local-studio'))
from request_state import INITIAL, VALUES, patch_operations, apply_operations, unique_object

ACTIONS = {'set', 'remove', 'reset', 'keep'}
PLAN_SYSTEM = '''Read ONE image-edit request. Classify the action for EACH of six slots:
jacket (blazer/coat), top (shirt/sweater), pin, necklace (pendant), background, prop (plant/lamp/bench).
Return a flat JSON object with exactly these six keys and actions only:
set = add or replace with a specified NEW choice;
remove = take away / absent / none;
reset = restore the ORIGINAL reference-image attribute;
keep = leave current attribute unchanged, do not remove, or unmentioned.
Assign each verb to its OWN noun. A keep clause for one object never makes another object keep.
Restoring the original is RESET, NOT KEEP. In "replace X with Y", the action is SET, not KEEP.
Do not output colors, object value codes, explanations or nested structures. JSON only.'''
VALUE_SYSTEM = '''Extract the NEW categorical values for slots whose action is set.
Use the original request, not superseded choices. Return one flat JSON object with exactly the set slots.
Never output keep, original, or none. No slots whose action is keep/remove/reset.
If no slot is set, return {}. If a set value is ambiguous, output "unknown" for that slot.
Allowed values: ''' + json.dumps({k: [v for v in values if v != 'none'] for k, values in VALUES.items()})


def object_from(raw):
    value = json.loads(raw[raw.find('{'):raw.rfind('}') + 1], object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise ValueError('Expected one JSON object')
    return value


def parse_plan(raw):
    plan = object_from(raw)
    if set(plan) != set(INITIAL) or any(not isinstance(v, str) or v not in ACTIONS for v in plan.values()):
        raise ValueError('Plan requires six scalar actions')
    for key, action in plan.items():
        if action == 'remove' and 'none' not in VALUES[key]:
            raise ValueError('Cannot remove ' + key)
    return plan


def compile_update(state, request, plan_raw, values_raw):
    errors = {}
    try:
        plan = parse_plan(plan_raw)
    except (ValueError, TypeError) as error:
        return dict(state), {'plan': str(error)}
    try:
        values = object_from(values_raw)
    except (ValueError, TypeError) as error:
        values = {}
        errors['values'] = str(error)
    updated = dict(state)
    for key, action in plan.items():
        if action == 'keep':
            continue
        value = 'original' if action == 'reset' else 'none' if action == 'remove' else values.get(key)
        try:
            if action == 'set' and (not isinstance(value, str) or value in ['none', 'original', 'keep']):
                raise ValueError('Missing or invalid set value')
            operations = patch_operations({key: value}, request)
            updated = apply_operations(updated, operations, request)
        except (ValueError, TypeError, KeyError) as error:
            errors[key] = str(error)
    return updated, errors
