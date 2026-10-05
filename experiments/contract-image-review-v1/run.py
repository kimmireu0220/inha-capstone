"""Frozen, post-hoc whole-study evaluation with a larger same-family VLM."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PRIMARY = REPO / 'experiments/contract-image-v3'
HELPERS = REPO / 'experiments/action-image-v1'
sys.path.insert(0, str(HELPERS))
from evaluate import packet, parse, save, sha
from goals import prompt
from summarize import aggregate
from analyze_pairs import compare

MODEL = 'mlx-community/Qwen2.5-VL-7B-Instruct-4bit'
REVISION = 'fdcc572e8b05ba9daeaf71be8c9e4267c826ff9b'
VERSIONS = {'mlx-vlm': '0.7.4', 'mlx': '0.32.3', 'transformers': '5.18.0'}


def transitions(paired):
    counts = {}
    for pair in paired['pairs']:
        if pair['same_input_job']:
            continue
        for old, new in zip(*pair['scores']):
            key = f"{'unknown' if old is None else old}->{ 'unknown' if new is None else new}"
            counts[key] = counts.get(key, 0) + 1
    return counts


def prepare():
    data = packet(PRIMARY)
    assert data == json.loads((PRIMARY / 'evaluation-plan.json').read_text())
    first = json.loads((PRIMARY / 'ai-ratings.json').read_text())
    assert set(first['ratings']) == set(data['items']) and len(data['items']) == 68
    assert json.loads((PRIMARY / 'verification.json').read_text())['passed']
    files = [ROOT / 'run.py', ROOT / 'PROTOCOL.md', ROOT / 'test_run.py', PRIMARY / 'evaluation-plan.json',
             PRIMARY / 'ai-ratings.json', PRIMARY / 'summary.json', PRIMARY / 'verification.json']
    files += [HELPERS / n for n in ['evaluate.py', 'goals.py', 'summarize.py', 'analyze_pairs.py']]
    frozen = {'model': MODEL, 'revision': REVISION, 'temperature': 0, 'max_tokens': 400,
              'versions': VERSIONS, 'post_hoc': True, 'unique_evaluation_inputs': len(data['items']),
              'sha256': {str(p.relative_to(REPO)): sha(p) for p in files}}
    path = ROOT / 'frozen.json'
    if path.exists():
        assert json.loads(path.read_text()) == frozen, 'Frozen inputs changed'
    else:
        save(path, frozen)
    return data, frozen


def run():
    data, frozen = prepare()
    from huggingface_hub import snapshot_download
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    from PIL import Image
    assert {p: importlib.metadata.version(p) for p in VERSIONS} == VERSIONS
    path = snapshot_download(MODEL, revision=REVISION, local_files_only=True)
    assert Path(path).name == REVISION
    model, processor = load(path)
    config = load_config(path)
    target = ROOT / 'ai-ratings.json'
    result = json.loads(target.read_text()) if target.exists() else {
        'rater_type': 'AI', 'method_labels_hidden': True, 'frozen_sha256': sha(ROOT / 'frozen.json'),
        'ratings': {}, 'technical_failures': []}
    assert result['frozen_sha256'] == sha(ROOT / 'frozen.json')
    for key, item in sorted(data['items'].items()):
        if key in result['ratings']:
            continue
        formatted = apply_chat_template(processor, config, prompt(item['goals']), num_images=1)
        with Image.open(item['image']) as source:
            image = source.convert('RGB')
        started = time.monotonic()
        try:
            response = generate(model, processor, formatted, [image], max_tokens=400,
                                temperature=0, verbose=False)
        except Exception as exc:
            result['technical_failures'].append({'key': key, 'error': repr(exc)})
            save(target, result)
            raise
        raw = response.text if hasattr(response, 'text') else str(response)
        scores, error = parse(raw)
        result['ratings'][key] = {'scores': scores, 'raw': raw, 'parse_error': error,
                                  'seconds': time.monotonic() - started}
        save(target, result)
        print('REVIEWED', len(result['ratings']), '/', len(data['items']), key[:12], scores, flush=True)


def report():
    data, frozen = prepare()
    ratings = json.loads((ROOT / 'ai-ratings.json').read_text())
    assert ratings['frozen_sha256'] == sha(ROOT / 'frozen.json')
    assert set(ratings['ratings']) == set(data['items']), 'Review incomplete'
    primary = json.loads((PRIMARY / 'summary.json').read_text())
    primary_ratings = json.loads((PRIMARY / 'ai-ratings.json').read_text())['ratings']
    rows = [{**r, 'scores': ratings['ratings'][data['mapping'][r['id']]]['scores']}
            for r in primary['rows']]
    modes = ['baseline_restore', 'keep_remove']
    pairs = compare(rows, modes)

    def agreement(a, b):
        values = list(zip(a, b))
        known = [(x, y) for x, y in values if x is not None and y is not None]
        return {'decisions': len(values), 'same_including_unknown': sum(x == y for x, y in values),
                'both_known': len(known), 'same_when_both_known': sum(x == y for x, y in known)}

    result = {'complete': True, 'post_hoc': True, 'rater_type': 'AI', 'descriptive_only': True,
              'model': MODEL, 'revision': REVISION, 'rows': rows, 'pairs': pairs,
              'changed_pair_transitions': transitions(pairs),
              'primary_changed_pair_transitions': transitions(compare(primary['rows'], modes)),
              'primary_by_mode': primary['by_mode'],
              'by_mode': {m: aggregate([r for r in rows if r['mode'] == m]) for m in modes},
              'parse_failures': sum(r['parse_error'] is not None for r in ratings['ratings'].values()),
              'unique_input_agreement': agreement(
                  [v for k in sorted(data['items']) for v in primary_ratings[k]['scores']],
                  [v for k in sorted(data['items']) for v in ratings['ratings'][k]['scores']]),
              'condition_agreement': agreement(
                  [v for r in primary['rows'] for v in r['scores']],
                  [v for r in rows for v in r['scores']])}
    for dimension in ['person', 'history']:
        result['by_' + dimension] = {
            value: {m: aggregate([r for r in rows if r[dimension] == value and r['mode'] == m])
                    for m in modes} for value in sorted({r[dimension] for r in rows})}
    result['sha256'] = {'frozen.json': sha(ROOT / 'frozen.json'), 'ai-ratings.json': sha(ROOT / 'ai-ratings.json')}
    save(ROOT / 'summary.json', result)
    save(ROOT / 'verification.json', {'passed': True, 'conditions': len(rows),
        'unique_evaluation_inputs': len(data['items']), 'post_hoc': True,
        'sha256': {n: sha(ROOT / n) for n in ['frozen.json', 'ai-ratings.json', 'summary.json', 'run.py']}})
    print(json.dumps({k: v for k, v in result.items() if k not in ['rows', 'pairs', 'by_person', 'by_history']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'run', 'report'])
    action = parser.parse_args().action
    {'prepare': prepare, 'run': run, 'report': report}[action]()
