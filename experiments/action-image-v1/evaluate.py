"""One frozen AI pass per unique output/goal pair; no method labels in prompts.

Usage: .venv-local-eval/bin/python evaluate.py EXPERIMENT_DIRECTORY
This script does not generate or edit images. Unknown scores are not passes.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time
from goals import goals, prompt

MODEL = 'mlx-community/Qwen2.5-VL-3B-Instruct-4bit'
REVISION = '46d4cf06a06ffc1a766c214174f9cbed2f45bcab'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def parse(raw):
    try:
        parsed = json.loads(raw.strip().removeprefix('```json').removesuffix('```').strip())
        scores = parsed['scores']
        assert isinstance(scores, list) and len(scores) == 6
        assert all(v is None or type(v) is int and v in (0, 1) for v in scores)
        return scores, None
    except (ValueError, KeyError, AssertionError, TypeError) as exc:
        return [None] * 6, repr(exc)


def packet(root):
    repo = Path(__file__).resolve().parents[2]
    prepared = json.loads((root / 'prepared.json').read_text())
    for name, digest in prepared['inputs'].items():
        assert sha(repo / name) == digest, name
    ledger = json.loads((root / 'calls.json').read_text())
    records = {r['job']: r for r in ledger['calls']}
    assert len(records) == len(ledger['calls'])
    assert set(records) == {c['job'] for c in prepared['conditions']}, 'Generation incomplete'
    items, mapping = {}, {}
    for row in prepared['conditions']:
        record = records[row['job']]
        assert record['person'] == row['person']
        folder = root / record['folder']
        for name, digest in record['sha256'].items():
            assert sha(folder / name) == digest
        reference = repo / 'experiments/state-tracking-v2/references' / f'{row["person"]}.png'
        assert sha(folder / 'input.png') == sha(reference), 'Generation did not use the planned reference'
        assert (folder / 'prompt.txt').read_text() == row['prompt'] + '\n'
        targets = goals(row['person'], row['expected_state'])
        digest = sha(folder / 'output.png')
        key = hashlib.sha256((digest + json.dumps(targets)).encode()).hexdigest()
        items.setdefault(key, {'image': str((folder / 'output.png').resolve()),
                               'sha256': digest, 'goals': targets})
        mapping[row['id']] = key
    return {'prepared_sha256': sha(root / 'prepared.json'), 'ledger_sha256': sha(root / 'calls.json'),
            'evaluator_sha256': sha(Path(__file__)), 'goals_sha256': sha(Path(__file__).with_name('goals.py')),
            'items': items, 'mapping': mapping}


def main():
    root = Path(sys.argv[1]).resolve()
    data = packet(root)
    plan = root / 'evaluation-plan.json'
    if plan.exists():
        assert json.loads(plan.read_text()) == data, 'Evaluation inputs changed'
    else:
        save(plan, data)
    from huggingface_hub import snapshot_download
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    from PIL import Image
    model_path = snapshot_download(MODEL, revision=REVISION, local_files_only=True)
    assert Path(model_path).name == REVISION
    model, processor = load(model_path)
    config = load_config(model_path)
    output = root / 'ai-ratings.json'
    inputs = {'evaluation_plan_sha256': sha(plan), 'model': MODEL, 'revision': REVISION,
              'temperature': 0, 'max_tokens': 400}
    result = json.loads(output.read_text()) if output.exists() else {
        'rater_type': 'AI', 'method_labels_hidden': True, 'inputs': inputs,
        'versions': {p: importlib.metadata.version(p) for p in ['mlx-vlm', 'mlx', 'transformers']},
        'ratings': {}}
    assert result['inputs'] == inputs
    for key, item in sorted(data['items'].items()):
        if key in result['ratings']:
            continue
        formatted = apply_chat_template(processor, config, prompt(item['goals']), num_images=1)
        with Image.open(item['image']) as source:
            image = source.convert('RGB')
        start = time.monotonic()
        response = generate(model, processor, formatted, [image], max_tokens=400,
                            temperature=0, verbose=False)
        raw = response.text if hasattr(response, 'text') else str(response)
        scores, error = parse(raw)
        result['ratings'][key] = {'scores': scores, 'raw': raw, 'parse_error': error,
                                  'seconds': time.monotonic() - start}
        save(output, result)
        print('RATED', len(result['ratings']), '/', len(data['items']), key[:12], scores, flush=True)


if __name__ == '__main__':
    main()
