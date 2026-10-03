"""Freeze a two-call full-history state control before reading annotations."""
import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE = ROOT.parent / 'state-tracking-v2'
sys.path.insert(0, str(REPO / 'local-studio'))
from request_state import INITIAL, MODEL, VALUES, StateExtractor, render_prompt, unique_object

REVISION = '4dcb3d101c2a062e5c1d4bb173588c54ea6c4d25'


class FrozenStateExtractor(StateExtractor):
    def __init__(self):
        from huggingface_hub import snapshot_download
        from mlx_lm import load
        path = snapshot_download(MODEL, revision=REVISION)
        self.model, self.tokenizer = load(path)

SCHEMA = json.dumps({key: values + ['original'] for key, values in VALUES.items()})
FIRST = '''Read all chronological image-edit requests and return the FINAL state.
Return one JSON object containing exactly the six slots in this schema: ''' + SCHEMA + '''
Later requests supersede earlier requests for the same slot. Keep other slots.
Removal means none; original means restore the source image or never edited.
Do not return the history, an image prompt, explanations, or extra keys.
Viewer-left/right means the displayed image. Separate background from prop.'''
SECOND = '''Audit the proposed final state against ALL original chronological requests.
Return a corrected complete final JSON state with exactly these six slots: ''' + SCHEMA + '''
Check latest replacements, removals, re-additions and unchanged slots.
Removal means none; original means restore the source image or never edited.
Viewer-left/right means the displayed image. Separate background from prop.
Return JSON only, including all six slots, whether or not corrections are needed.'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def parse_state(raw):
    state = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(state, dict) or set(state) != set(INITIAL):
        raise ValueError('Exactly six supported slots are required')
    for key, value in state.items():
        if not isinstance(value, str) or value not in VALUES[key] + ['original']:
            raise ValueError('Unsupported value for ' + key)
    return state


def choose_state(outputs):
    parsed, errors = [], []
    for raw in outputs:
        try:
            parsed.append(parse_state(raw))
            errors.append(None)
        except (ValueError, TypeError) as error:
            parsed.append(None)
            errors.append(str(error))
    selected = 1 if parsed[1] is not None else 0 if parsed[0] is not None else None
    return (dict(INITIAL) if selected is None else parsed[selected]), selected, errors


def main():
    source_revision = json.loads((SOURCE / 'run_notes.json').read_text())['cached_model_revisions'][MODEL]
    assert source_revision == REVISION, 'Control must use the recorded source-model revision'
    inputs = {str(path.relative_to(REPO)): sha(path) for path in [
        ROOT / 'PROTOCOL.md', Path(__file__), SOURCE / 'benchmark.json',
        REPO / 'local-studio/request_state.py']}
    frozen = ROOT / 'prepare-inputs.json'
    if frozen.exists():
        assert json.loads(frozen.read_text()) == inputs, 'Frozen inputs changed'
    else:
        save(frozen, inputs)
    histories = json.loads((SOURCE / 'benchmark.json').read_text())['histories']
    prompts = ROOT / 'prompts'
    prompts.mkdir(exist_ok=True)
    extractor = None
    for name, history in histories.items():
        target = prompts / f'{name}-transcript.json'
        if target.exists():
            record = json.loads(target.read_text())
        else:
            if extractor is None:
                extractor = FrozenStateExtractor()
            chronology = '\n'.join(f'{i}. {turn["request"]}'
                                    for i, turn in enumerate(history['turns'], 1))
            user = 'Chronological requests:\n' + chronology
            start = time.monotonic()
            first = extractor.ask(FIRST, user, max_tokens=700)
            second = extractor.ask(SECOND, user + '\n\nProposed final state:\n' + first,
                                   max_tokens=700)
            seconds = time.monotonic() - start
            state, selected, errors = choose_state([first, second])
            record = {'model': MODEL, 'revision': REVISION,
                      'versions': {p: importlib.metadata.version(p) for p in ['mlx-lm', 'mlx', 'transformers']},
                      'temperature': 0, 'max_tokens_per_call': 700,
                      'model_calls': 2, 'seconds': seconds,
                      'system_prompts': [FIRST, SECOND], 'user': user,
                      'responses': [first, second], 'validation_errors': errors,
                      'selected_response_index': selected, 'final_state': state,
                      'final': render_prompt(state)}
            save(target, record)
        (prompts / f'{name}-structured.txt').write_text(record['final'] + '\n')
        print('FROZEN', name, flush=True)
    # No annotations enter model requests. Score only after all four are frozen.
    save(ROOT / 'prepare-manifest.json', {'inputs': inputs,
         'prompts': {p.name: sha(p) for p in sorted(prompts.glob('*.txt'))},
         'transcripts': {p.name: sha(p) for p in sorted(prompts.glob('*.json'))}})
    rows = []
    for name, history in histories.items():
        expected = dict(INITIAL)
        for turn in history['turns']:
            expected.update(turn['updates'])
        observed = json.loads((prompts / f'{name}-transcript.json').read_text())['final_state']
        rows.append({'history': name, 'expected': expected, 'observed': observed,
                     'correct_slots': sum(expected[k] == observed[k] for k in INITIAL)})
    save(ROOT / 'state-scores.json', {'histories': rows, 'total_slots': 24,
         'correct_slots': sum(row['correct_slots'] for row in rows),
         'exact_histories': sum(row['correct_slots'] == 6 for row in rows)})


if __name__ == '__main__':
    main()
