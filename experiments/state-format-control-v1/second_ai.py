"""Evaluate only new masked control images with the frozen source VLM settings."""
import importlib.util
import json
import time
from pathlib import Path
from PIL import Image
from prepare import ROOT, SOURCE, save, sha


def main():
    spec = importlib.util.spec_from_file_location('source_evaluator', SOURCE / 'second_ai.py')
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    pending = json.loads((ROOT / 'pending-ratings.json').read_text())
    prior = json.loads((SOURCE / 'second-ai-ratings.json').read_text())
    assert len(prior['ratings']) == 96 and prior['model'] == source.MODEL
    assert prior['revision'] == source.REVISION
    inputs = {'source_evaluator_sha256': sha(SOURCE / 'second_ai.py'),
              'evaluator_sha256': sha(Path(__file__)),
              'pending_sha256': sha(ROOT / 'pending-ratings.json'),
              'source_ratings_sha256': sha(SOURCE / 'second-ai-ratings.json'),
              'plates_sha256': {key.split('/')[0]: sha(ROOT / 'blind' / (key.split('/')[0] + '.png'))
                                for key in pending}}
    assert prior['inputs']['evaluator_sha256'] == inputs['source_evaluator_sha256']
    output = ROOT / 'second-ai-ratings.json'
    result = json.loads(output.read_text()) if output.exists() else {
        'rater_type': 'AI', 'method_masked': True, 'model': source.MODEL,
        'revision': source.REVISION, 'temperature': 0, 'inputs': inputs,
        'versions': {p: source.importlib.metadata.version(p) for p in ['mlx-vlm', 'mlx', 'transformers']},
        'ratings': {}}
    assert result['inputs'] == inputs
    assert result['versions'] == prior['versions'], 'Keep evaluator package versions identical'
    assert set(result['ratings']).issubset(pending)
    model = processor = config = None
    for key, record in sorted(pending.items()):
        if key in result['ratings']:
            continue
        if model is None:
            path = source.snapshot_download(source.MODEL, revision=source.REVISION)
            model, processor = source.load(path)
            config = source.load_config(path)
        comparison, label = key.split('/')
        index = 'ABC'.index(label) + 1
        history = record['history']
        # Deliberately byte-identical to the main evaluator's prompt and crop geometry.
        prompt = source.build_prompt(history)
        formatted = source.apply_chat_template(processor, config, prompt, num_images=1)
        with Image.open(ROOT / 'blind' / (comparison + '.png')) as image:
            crop = image.crop((index * 512, 38, (index + 1) * 512, 806)).convert('RGB')
        start = time.monotonic()
        response = source.generate(model, processor, formatted, [crop], max_tokens=400,
                                   temperature=0, verbose=False)
        raw = response.text if hasattr(response, 'text') else str(response)
        error = None
        try:
            parsed = json.loads(raw.strip().removeprefix('```json').removesuffix('```').strip())
            scores = parsed['scores']
            assert len(scores) == 6 and all(v is None or type(v) is int and v in (0, 1) for v in scores)
        except (ValueError, KeyError, AssertionError, TypeError) as exc:
            scores, error = [None] * 6, repr(exc)
        result['ratings'][key] = {'scores': scores, 'raw': raw,
                                  'seconds': time.monotonic() - start, 'parse_error': error,
                                  'output_sha256': record['output_sha256']}
        save(output, result)
        print(key, scores, flush=True)
    save(output, result)


if __name__ == '__main__':
    main()
