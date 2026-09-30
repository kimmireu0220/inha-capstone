"""Verify frozen conditions, score face embeddings, and create blind comparison sheets."""
import hashlib
import json
import random
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
MODES = ['history', 'state', 'agent']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def face(app, path):
    image = cv2.imread(str(path))
    if image is None:
        raise RuntimeError(f'Cannot read: {path}')
    detected = app.get(image)
    if len(detected) != 1:
        return {'face_count': len(detected), 'embedding': None}
    return {'face_count': 1, 'detection_score': float(detected[0].det_score),
        'embedding': detected[0].normed_embedding.astype(np.float64)}


def make_sheet(person, history, seed, options, labels):
    items = [('ORIGINAL', ROOT / 'references' / f'{person}.png')]
    items += [(f'IMAGE {letter}', options[labels[letter]]) for letter in 'ABC']
    panels = []
    for label, path in items:
        with Image.open(path) as source:
            image = source.convert('RGB')
            image.thumbnail((512, 768))
        panels.append((label, image))
    canvas = Image.new('RGB', (2048, 806), 'white')
    draw = ImageDraw.Draw(canvas)
    for index, (label, image) in enumerate(panels):
        canvas.paste(image, (index * 512 + (512 - image.width) // 2,
            38 + (768 - image.height) // 2))
        draw.text((index * 512 + 12, 12),
            f'{person} / {history} / seed {seed} / {label}', fill='black')
    folder = ROOT / 'blind'
    folder.mkdir(exist_ok=True)
    canvas.save(folder / f'{person}-{history}-{seed}.png')


def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    calls = json.loads((ROOT / 'calls.json').read_text())['calls']
    assert len(calls) == plan['expected_outputs'] == 108
    assert sha(ROOT / 'PROTOCOL.md') == plan['protocol_sha256']
    assert sha(ROOT / 'prompt-audit.json') == plan['prompt_audit_sha256']
    assert sha(ROOT / 'prepare-manifest.json') == plan['prepare_manifest_sha256']
    for person, digest in plan['people'].items():
        assert sha(ROOT / 'references' / f'{person}.png') == digest
    for name, digest in plan['prompts'].items():
        assert sha(ROOT / 'prompts' / f'{name}.txt') == digest
    for history, digest in plan['histories'].items():
        assert sha(ROOT / 'histories' / f'{history}.json') == digest
    keys = [(c['person'], c['history'], c['seed'], c['mode']) for c in calls]
    assert len(set(keys)) == len(keys)
    expected = {(p, h, s, m) for p in plan['people_order']
        for h in plan['history_order'] for s in plan['seeds'] for m in MODES}
    assert set(keys) == expected
    for call in calls:
        assert call['source_sha256'] == plan['people'][call['person']]
        assert call['input_sha256'] == call['source_sha256']
        assert call['prompt_sha256'] == plan['prompts'][f"{call['history']}-{call['mode']}"]
        folder = ROOT / call['folder']
        for name, key in [('input.png', 'input_sha256'),
                          ('prompt.txt', 'prompt_sha256'),
                          ('output.png', 'output_sha256')]:
            assert sha(folder / name) == call[key], (call['folder'], name)
        with Image.open(folder / 'input.png') as image:
            assert image.size == (call['width'], call['height'])
        with Image.open(folder / 'output.png') as image:
            image.verify()

    app = FaceAnalysis(name='buffalo_l', root=str(Path.home() / '.insightface'),
        allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=-1, det_thresh=0.5, det_size=(640, 640))
    references = {p: face(app, ROOT / 'references' / f'{p}.png')
        for p in plan['people_order']}
    assert all(f['embedding'] is not None for f in references.values())
    rows = []
    for index, call in enumerate(calls, 1):
        found = face(app, ROOT / call['folder'] / 'output.png')
        original = references[call['person']]
        similarity = (float(np.dot(original['embedding'], found['embedding']))
            if found['embedding'] is not None else None)
        rows.append({key: call[key] for key in ('person', 'history', 'seed', 'mode',
            'reused', 'output_sha256', 'folder')} | {
            'face_count': found['face_count'],
            'detection_score': found.get('detection_score'),
            'identity_similarity': similarity})
        if index % 12 == 0:
            print(f'Face analysis {index}/108', flush=True)

    map_path = ROOT / 'blinding-map.json'
    if map_path.exists():
        mapping = json.loads(map_path.read_text())
    else:
        rng = random.Random(18291)
        mapping = {}
        for person in plan['people_order']:
            for history in plan['history_order']:
                for seed in plan['seeds']:
                    modes = list(MODES)
                    rng.shuffle(modes)
                    mapping[f'{person}-{history}-{seed}'] = dict(zip('ABC', modes))
        save(map_path, mapping)
    for key, labels in mapping.items():
        person, history, seed_string = key.split('-')
        seed = int(seed_string)
        options = {r['mode']: ROOT / r['folder'] / 'output.png' for r in rows
            if (r['person'], r['history'], r['seed']) == (person, history, seed)}
        assert set(options) == set(MODES)
        make_sheet(person, history, seed, options, labels)
    assert len(mapping) == 36
    results = {'complete': True, 'outputs': len(rows), 'comparison_sets': 36,
        'independent_people': 6, 'rows': rows,
        'references': {p: {'face_count': f['face_count'],
            'detection_score': f.get('detection_score')} for p, f in references.items()},
        'method': {'model': 'InsightFace buffalo_l/w600k_r50',
            'detector': 'det_10g', 'det_size': [640, 640], 'det_thresh': 0.5,
            'metric': 'original-to-output cosine similarity'}}
    save(ROOT / 'results.json', results)
    save(ROOT / 'verification.json', {'complete': True, 'outputs': len(rows),
        'comparison_sets': 36, 'input_prompt_output_hashes_verified': True,
        'all_outputs_single_face': all(r['face_count'] == 1 for r in rows),
        'protocol_sha256': sha(ROOT / 'PROTOCOL.md'),
        'analysis_sha256': sha(Path(__file__))})
    print('Verified 108 outputs and created 36 blind comparison sheets.', flush=True)


if __name__ == '__main__':
    main()
