"""Verify outputs, calculate face similarity, and make three-way blinded sheets."""
import hashlib
import json
import random
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def face(app, path):
    image = cv2.imread(str(path))
    if image is None:
        raise RuntimeError(f'Cannot read {path}')
    found = app.get(image)
    if len(found) != 1:
        return {'face_count': len(found), 'embedding': None}
    return {'face_count': 1, 'score': float(found[0].det_score),
            'embedding': found[0].normed_embedding.astype(np.float64)}

def make_sheet(person, seed, paths, labels):
    original = REPO / 'experiments/real-people-v1' / f'reference-{person}.png'
    ordered = [('ORIGINAL', original)] + [(f'IMAGE {letter}', paths[labels[letter]])
        for letter in ['A', 'B', 'C']]
    panels = []
    for label, path in ordered:
        with Image.open(path) as im:
            picture = im.convert('RGB')
            picture.thumbnail((512, 768))
        panels.append((label, picture))
    board = Image.new('RGB', (2048, max(pic.height for _, pic in panels) + 38), 'white')
    draw = ImageDraw.Draw(board)
    for i, (label, pic) in enumerate(panels):
        board.paste(pic, (512 * i + (512 - pic.width) // 2, 38))
        draw.text((512 * i + 12, 12), f'{person} / seed {seed} / {label}', fill='black')
    folder = ROOT / 'blind'
    folder.mkdir(exist_ok=True)
    board.save(folder / f'{person}-{seed}.png')

def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    calls = json.loads((ROOT / 'calls.json').read_text())['calls']
    assert sha(ROOT / 'PROTOCOL.md') == plan['protocol_sha256']
    assert sha(ROOT / 'prepare.py') == plan['prepare_code_sha256']
    assert sha(ROOT / 'history.json') == plan['history_sha256']
    assert sha(ROOT / 'prompt-audit.json') == plan['prompt_audit_sha256']
    assert len(calls) == plan['expected_outputs']
    assert len({(c['person'], c['seed'], c['mode']) for c in calls}) == len(calls)
    for mode, digest in plan['prompt_sha256'].items():
        assert sha(ROOT / f'{mode}-prompt.txt') == digest
    for person, info in plan['people'].items():
        assert sha(REPO / info['path']) == info['sha256']
    for call in calls:
        folder = ROOT / call['folder']
        for name, digest in [('input.png', call['input_sha256']),
                             ('prompt.txt', call['prompt_sha256']),
                             ('output.png', call['output_sha256'])]:
            assert sha(folder / name) == digest
        assert call['source_sha256'] == plan['people'][call['person']]['sha256']
        assert call['input_sha256'] == call['source_sha256']
        assert call['prompt_sha256'] == plan['prompt_sha256'][call['mode']]
    app = FaceAnalysis(name='buffalo_l', root=str(Path.home() / '.insightface'),
        allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=-1, det_thresh=0.5, det_size=(640, 640))
    refs = {person: face(app, REPO / info['path']) for person, info in plan['people'].items()}
    rows = []
    for call in calls:
        found = face(app, ROOT / call['folder'] / 'output.png')
        original = refs[call['person']]
        similarity = float(np.dot(original['embedding'], found['embedding'])) if (
            original['embedding'] is not None and found['embedding'] is not None) else None
        rows.append({'person': call['person'], 'seed': call['seed'], 'mode': call['mode'],
            'face_count': found['face_count'], 'detection_score': found.get('score'),
            'identity_similarity': similarity, 'output_sha256': call['output_sha256'],
            'folder': call['folder']})
    map_file = ROOT / 'blinding-map.json'
    if map_file.exists():
        mapping = json.loads(map_file.read_text())
    else:
        rng = random.Random(18291)
        mapping = {}
        for person in plan['people']:
            for seed in plan['seeds']:
                modes = list(plan['modes'])
                rng.shuffle(modes)
                mapping[f'{person}-{seed}'] = dict(zip(['A', 'B', 'C'], modes))
        save(map_file, mapping)
    for person in plan['people']:
        for seed in plan['seeds']:
            options = {r['mode']: ROOT / r['folder'] / 'output.png' for r in rows
                       if r['person'] == person and r['seed'] == seed}
            assert set(options) == set(plan['modes'])
            make_sheet(person, seed, options, mapping[f'{person}-{seed}'])
    per_person = {person: {mode: float(np.mean([r['identity_similarity'] for r in rows
        if r['person'] == person and r['mode'] == mode and r['identity_similarity'] is not None]))
        for mode in plan['modes']} for person in plan['people']}
    result = {'complete': True, 'outputs': len(rows), 'comparison_sets': 4,
        'independent_people': 2, 'rows': rows, 'per_person': per_person,
        'references': {p: {'face_count': f['face_count'], 'score': f.get('score')}
        for p, f in refs.items()}, 'method': {'model': 'InsightFace buffalo_l/w600k_r50',
        'detector': 'det_10g', 'det_size': [640, 640], 'det_thresh': 0.5,
        'metric': 'original-to-output cosine similarity'}}
    save(ROOT / 'results.json', result)
    save(ROOT / 'verification.json', {'complete': True, 'outputs': len(rows),
        'comparison_sets': 4, 'input_prompt_output_hashes_verified': True,
        'all_outputs_single_face': all(r['face_count'] == 1 for r in rows),
        'protocol_sha256': sha(ROOT / 'PROTOCOL.md'),
        'analysis_sha256': sha(Path(__file__))})
    print('Verified 12 outputs and created four three-way blinded sheets.')

if __name__ == '__main__':
    main()
