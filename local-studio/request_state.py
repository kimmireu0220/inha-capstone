"""Turn-wise edit extraction, validated state updates, and final-state rendering.

This research pipeline has a bounded six-slot vocabulary. The model never writes
the full state; the reducer owns retention, removal, and the update ledger.
"""
import json
from copy import deepcopy

MODEL = 'mlx-community/Qwen3-4B-4bit'
VALUES = {
    'jacket': ['none', 'navy', 'gray', 'green', 'beige'],
    'top': ['ivory_crewneck', 'white_crewneck', 'gray_sweater', 'navy_sweater'],
    'pin': ['none', 'silver_circle_right', 'gold_square_right',
            'red_triangle_left', 'blue_circle_left'],
    'necklace': ['none', 'silver_teardrop', 'gold_round'],
    'background': ['office', 'library', 'garden', 'blue_studio', 'brick_studio'],
    'prop': ['none', 'plant', 'lamp', 'bench'],
}
INITIAL = {field: 'original' for field in VALUES}
PRESERVE = ("Keep the person's face, facial features, expression, gaze, natural skin "
            "texture, hair, pose, body proportions, lighting on the person, and "
            "camera framing. Do not beautify or smooth the face. No text, logos, "
            "or watermarks.")
SYSTEM = '''Extract operations from ONE new image-edit request. Return JSON only:
{"operations":[{"field":"slot name","op":"set|remove|keep|reset","value":"allowed code for set","evidence":"exact substring of the new request"}]}.
Allowed slot values: SCHEMA
Return only explicitly requested changes. Retain unmentioned fields by returning
no operation for them. keep means retain the current value; remove means none;
reset means the original photograph. Never copy the full current state.
Respect negation: "do not remove" means keep, not remove. "replace X with Y"
means set Y. Several named items in one request require separate operations.
Viewer-left and viewer-right refer to the displayed image. A crew-neck shirt and
a crew-neck sweater are distinct. Background location and its prop are separate.
When a background request explicitly removes props, prop becomes none.
Use evidence exactly copied from the NEW request. Do not invent requirements.
If a requested value is outside the schema or ambiguous, return
{"clarification":"reason"}; do not partially update the state.'''.replace(
    'SCHEMA', json.dumps(VALUES))


def apply_operations(state, operations, request):
    """Validate the complete transaction before changing any state."""
    if set(state) != set(VALUES):
        raise ValueError('State must contain the six supported slots')
    if not isinstance(operations, list) or len(operations) > 6:
        raise ValueError('Invalid operation list')
    updated = deepcopy(state)
    seen = set()
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError('Operation must be an object')
        field, action = operation.get('field'), operation.get('op')
        if field not in VALUES or field in seen:
            raise ValueError('Unknown or duplicate slot')
        seen.add(field)
        evidence = operation.get('evidence')
        if not isinstance(evidence, str) or not evidence.strip() or evidence not in request:
            raise ValueError('Evidence must occur verbatim in the new request')
        if action == 'set':
            value = operation.get('value')
            if value not in VALUES[field]:
                raise ValueError('Value outside supported vocabulary')
        elif action == 'remove':
            value = 'none'
            if value not in VALUES[field]:
                raise ValueError('This slot cannot be removed')
        elif action == 'keep':
            value = state[field]
        elif action == 'reset':
            value = 'original'
        else:
            raise ValueError('Unknown action')
        updated[field] = value
    return updated


class StateExtractor:
    def __init__(self):
        from mlx_lm import load
        self.model, self.tokenizer = load(MODEL)

    def ask(self, system, user, max_tokens=550):
        from mlx_lm import generate
        from mlx_lm.sample_utils import make_sampler
        prompt = self.tokenizer.apply_chat_template([
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user}], tokenize=False,
            add_generation_prompt=True, enable_thinking=False)
        return generate(self.model, self.tokenizer, prompt=prompt,
            max_tokens=max_tokens, sampler=make_sampler(temp=0), verbose=False).strip()

    def update(self, state, request):
        user = 'Current state: ' + json.dumps(state) + '\nNEW request: ' + request
        attempts = []
        for attempt in range(2):
            raw = self.ask(SYSTEM, user)
            record = {'response': raw}
            attempts.append(record)
            try:
                parsed = json.loads(raw[raw.find('{'):raw.rfind('}') + 1])
                if parsed.get('clarification'):
                    raise ValueError(str(parsed['clarification']))
                operations = parsed['operations']
                updated = apply_operations(state, operations, request)
                return {'state': updated, 'operations': operations, 'attempts': attempts}
            except (ValueError, KeyError, TypeError) as error:
                record['error'] = str(error)
                user = ('Current state: ' + json.dumps(state) + '\nNEW request: ' + request
                    + '\nYour invalid response: ' + raw + '\nValidation error: ' + str(error)
                    + '\nCorrect the JSON operations. Use only this request as evidence.')
        raise ValueError(json.dumps({'request': request, 'attempts': attempts}))

    def replay(self, requests):
        state, ledger = dict(INITIAL), []
        for index, request in enumerate(requests, 1):
            before = dict(state)
            try:
                result = self.update(state, request)
                state = result['state']
                ledger.append({'turn': index, 'request': request, 'before': before,
                               'accepted': True, **result})
            except ValueError as error:
                detail = json.loads(str(error))
                ledger.append({'turn': index, 'request': request, 'before': before,
                    'state': dict(state), 'operations': [], 'accepted': False,
                    'attempts': detail['attempts']})
        return state, ledger


def render_prompt(state, preserve=PRESERVE):
    """Compile only the current slots; superseded values are never rendered."""
    if set(state) != set(VALUES):
        raise ValueError('Missing slot')
    for field, value in state.items():
        if value != 'original' and value not in VALUES[field]:
            raise ValueError('Invalid state value')
    parts = []
    jacket = state['jacket']
    if jacket == 'none':
        parts.append('There must be no jacket or blazer visible.')
    elif jacket == 'original':
        parts.append('Keep the original outer garment unchanged.')
    else:
        color = {'navy': 'dark navy', 'gray': 'dark gray',
                 'green': 'forest green', 'beige': 'beige'}[jacket]
        parts.append(f'Wear a {color} blazer.')
    tops = {'ivory_crewneck': 'an ivory crew-neck shirt',
            'white_crewneck': 'a plain white crew-neck shirt',
            'gray_sweater': 'a plain light-gray crew-neck sweater',
            'navy_sweater': 'a plain dark-navy crew-neck sweater'}
    parts.append('Keep the original top unchanged.' if state['top'] == 'original'
                 else 'Wear ' + tops[state['top']] + '.')
    pins = {'silver_circle_right': 'one small circular silver pin on the viewer-right lapel',
            'gold_square_right': 'one small square gold pin on the viewer-right lapel',
            'red_triangle_left': 'one small triangular red pin on the viewer-left lapel',
            'blue_circle_left': 'one small circular blue pin on the viewer-left lapel'}
    for field, names, empty in [
        ('pin', pins, 'There must be no pin anywhere.'),
        ('necklace', {'silver_teardrop': 'one thin silver necklace with one small teardrop pendant',
                      'gold_round': 'one thin gold necklace with one small round gold pendant'},
         'There must be no necklace or pendant.')]:
        value = state[field]
        parts.append(empty if value == 'none' else f'Keep the original {field} unchanged.'
                     if value == 'original' else 'Add exactly ' + names[value] + '.')
    backgrounds = {'office': 'a modern office', 'library': 'a library with wooden bookshelves',
                   'garden': 'an outdoor garden with a leafy hedge',
                   'blue_studio': 'a continuous pale-blue studio backdrop',
                   'brick_studio': 'a studio with a plain red-brick wall'}
    parts.append('Keep the original background unchanged.' if state['background'] == 'original'
                 else 'Set the background to ' + backgrounds[state['background']] + '.')
    props = {'plant': 'one green potted plant', 'lamp': 'one warm floor lamp',
             'bench': 'one stone bench'}
    value = state['prop']
    if value == 'none':
        parts.append('No decorative plants, lamps, or benches in the background.')
    elif value != 'original':
        parts.append('Include exactly ' + props[value] + ' in the background.')
    return ('Edit only the supplied photograph. Apply these final current requirements; '
            'preserve everything else:\n- ' + '\n- '.join(parts) + '\n' + preserve)
