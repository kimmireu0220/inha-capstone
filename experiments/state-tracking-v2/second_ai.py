"""One fixed, independent local VLM pass over method-masked images."""
import importlib.metadata
import json
import time
from pathlib import Path
from PIL import Image
from huggingface_hub import snapshot_download
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config

ROOT = Path(__file__).resolve().parent
MODEL = 'mlx-community/Qwen2.5-VL-3B-Instruct-4bit'
GOALS = {
    'U1': ['No blazer or jacket', 'A navy blue crew-neck sweater', 'No lapel pin',
           'No necklace chain or pendant', 'Pale blue studio background', 'One green potted plant in the background'],
    'U2': ['A beige blazer', 'A white crew-neck shirt', 'Exactly one blue circular pin on the viewer-left lapel',
           'No necklace chain or pendant', 'Outdoor garden with leafy hedges', 'One stone bench in the background'],
    'U3': ['A green blazer', 'An ivory crew-neck top', 'No lapel pin',
           'Exactly one silver necklace with a small teardrop pendant', 'Library with wooden bookshelves', 'One warm floor lamp in the background'],
    'U4': ['A dark gray blazer', 'A light gray crew-neck sweater', 'Exactly one red triangular pin on the viewer-left lapel',
           'No necklace chain or pendant', 'Red brick studio background', 'No plant, lamp, or bench in the background'],
}


def main():
    path = snapshot_download(MODEL)
    model, processor = load(path)
    config = load_config(path)
    output = ROOT / 'second-ai-ratings.json'
    result = json.loads(output.read_text()) if output.exists() else {
        'rater_type': 'AI', 'method_masked': True, 'model': MODEL,
        'revision': Path(path).name, 'temperature': 0,
        'versions': {p: importlib.metadata.version(p) for p in ['mlx-vlm', 'mlx', 'transformers']},
        'ratings': {}}
    assert result['revision'] == Path(path).name
    for plate in sorted((ROOT / 'blind').glob('*.png')):
        key = plate.stem
        history = key.split('-')[1]
        for index, label in enumerate('AB', 1):
            rating_key = key + '/' + label
            if rating_key in result['ratings']:
                continue
            prompt = ('Assess this image against six goals. Score 1 if visibly satisfied, 0 if visibly '
                      'violated, and null if not possible to judge. Viewer-left means the left side '
                      'of the displayed image. Inspect small accessories carefully. Return only '
                      'JSON with keys scores (six values in order) and reason (brief explanation).\n' +
                      '\n'.join(f'{i}. {g}' for i, g in enumerate(GOALS[history], 1)))
            formatted = apply_chat_template(processor, config, prompt, num_images=1)
            with Image.open(plate) as image:
                crop = image.crop((index * 512, 38, (index + 1) * 512, 806)).convert('RGB')
            start = time.monotonic()
            response = generate(model, processor, formatted, [crop], max_tokens=400,
                                temperature=0, verbose=False)
            raw = response.text if hasattr(response, 'text') else str(response)
            error = None
            try:
                parsed = json.loads(raw.strip().removeprefix('```json').removesuffix('```').strip())
                scores = parsed['scores']
                assert len(scores) == 6 and all(v is None or type(v) is int and v in (0, 1) for v in scores)
            except (ValueError, KeyError, AssertionError, TypeError) as exc:
                scores, error = [None] * 6, repr(exc)
            result['ratings'][rating_key] = {'scores': scores, 'raw': raw,
                'seconds': time.monotonic() - start, 'parse_error': error}
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
            print(rating_key, scores, flush=True)


if __name__ == '__main__':
    main()
