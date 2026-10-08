"""Fixed one-pass AI diagnostic; preserve raw responses, including failures."""
import argparse
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
MODEL = 'mlx-community/Qwen2.5-VL-7B-Instruct-4bit'
REVISION = 'fdcc572e8b05ba9daeaf71be8c9e4267c826ff9b'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, obj):
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(p)


def prompt(goals):
    return ('Inspect this photograph. Evaluate each numbered visual goal independently. '
            'Use 1 if visibly satisfied, 0 if visibly contradicted, null if not discernible. '
            'For body direction and hands distinguish the depicted person\'s own left/right '
            'from viewer left/right. Do not infer missing details. Return only JSON '
            '{"scores":[1,0,null],"reasons":["brief visible evidence per goal"]}, '
            'with exactly one score and one reason per goal. Goals:\n' +
            '\n'.join(f'{i}. {g}' for i, g in enumerate(goals, 1)))


def prepare():
    plan = json.loads((ROOT / 'image-plan.json').read_text())
    files = [ROOT / n for n in ['evaluate_images.py', 'image-plan.json', 'image_protocol.md']]
    files += [ROOT / 'images' / (x['id'] + '.png') for x in plan['conditions']]
    frozen = dict(model=MODEL, revision=REVISION, temperature=0, max_tokens=600,
                  sha256={str(p.relative_to(ROOT)): sha(p) for p in files})
    path = ROOT / 'image-evaluation-frozen.json'
    if path.exists():
        assert json.loads(path.read_text()) == frozen, 'Frozen evaluation changed'
    else:
        save(path, frozen)
    return plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    plan = prepare()
    if args.prepare:
        print('Frozen six images and evaluator before inference')
        return
    from huggingface_hub import snapshot_download
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
    from PIL import Image
    path = snapshot_download(MODEL, revision=REVISION, local_files_only=True)
    model, processor = load(path)
    config = load_config(path)
    target = ROOT / 'image-ratings.json'
    result = json.loads(target.read_text()) if target.exists() else dict(
        rater_type='AI', frozen_sha256=sha(ROOT / 'image-evaluation-frozen.json'), ratings={})
    assert result['frozen_sha256'] == sha(ROOT / 'image-evaluation-frozen.json')
    for item in plan['conditions']:
        key = item['id']
        if key in result['ratings']:
            continue
        formatted = apply_chat_template(processor, config, prompt(item['goals']), num_images=1)
        with Image.open(ROOT / 'images' / (key + '.png')) as source:
            image = source.convert('RGB')
        start = time.monotonic()
        response = generate(model, processor, formatted, [image], max_tokens=600,
                            temperature=0, verbose=False)
        raw = response.text if hasattr(response, 'text') else str(response)
        error = None
        try:
            parsed = json.loads(raw[raw.find('{'):raw.rfind('}') + 1])
            scores, reasons = parsed['scores'], parsed['reasons']
            assert len(scores) == len(reasons) == len(item['goals'])
            assert all(x is None or type(x) is int and x in (0, 1) for x in scores)
            assert all(isinstance(x, str) for x in reasons)
        except (ValueError, KeyError, TypeError, AssertionError) as exc:
            scores, reasons, error = [None] * len(item['goals']), [], repr(exc)
        result['ratings'][key] = dict(scores=scores, reasons=reasons, raw=raw,
                                     parse_error=error, seconds=time.monotonic() - start)
        save(target, result)
        print(key, scores, flush=True)


if __name__ == '__main__':
    main()
