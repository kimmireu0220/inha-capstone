"""Verify frozen files and measure every original-to-output face similarity."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from insightface.app import FaceAnalysis

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def face(app, path):
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f'Cannot read image: {path}')
    faces = app.get(image)
    return (len(faces), faces[0].normed_embedding.astype(np.float64) if len(faces) == 1 else None)


def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    calls = json.loads((ROOT / 'calls.json').read_text())['calls']
    assert len(calls) == plan['expected_outputs'] == 96
    for file, key in [('PROTOCOL.md', 'protocol_sha256'), ('benchmark.json', 'benchmark_sha256'),
                      ('prepare-manifest.json', 'prepare_manifest_sha256')]:
        assert sha(ROOT / file) == plan[key]
    assert sha(REPO / 'local-studio/request_state.py') == plan['method_sha256']
    expected = {(p, h, s, m) for p in plan['people_order'] for h in plan['histories']
                for s in plan['seeds'] for m in plan['modes']}
    assert {(c['person'], c['history'], c['seed'], c['mode']) for c in calls} == expected
    for call in calls:
        folder = ROOT / call['folder']
        assert call['source_sha256'] == call['input_sha256'] == plan['people'][call['person']]
        assert call['prompt_sha256'] == plan['prompts'][f"{call['history']}-{call['mode']}"]
        for file, key in [('input.png', 'input_sha256'), ('prompt.txt', 'prompt_sha256'),
                          ('output.png', 'output_sha256')]:
            assert sha(folder / file) == call[key]
    app = FaceAnalysis(name='buffalo_l', root=str(Path.home() / '.insightface'),
        allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=-1, det_thresh=0.5, det_size=(640, 640))
    references = {p: face(app, ROOT / 'references' / f'{p}.png')[1] for p in plan['people_order']}
    assert all(value is not None for value in references.values())
    rows = []
    for call in calls:
        count, embedding = face(app, ROOT / call['folder'] / 'output.png')
        score = float(np.dot(references[call['person']], embedding)) if embedding is not None else None
        rows.append({**call, 'face_count': count, 'identity_similarity': score})
    (ROOT / 'face-results.json').write_text(json.dumps({'rows': rows,
        'metric': 'InsightFace buffalo_l original-to-output cosine similarity'}, indent=2) + '\n')
    (ROOT / 'verification.json').write_text(json.dumps({'complete': True, 'outputs': 96,
        'paired_comparisons': 48, 'frozen_inputs_prompts_and_output_hashes_verified': True,
        'single_face_outputs': sum(r['face_count'] == 1 for r in rows),
        'analysis_sha256': sha(Path(__file__))}, indent=2) + '\n')
    print('Verified all 96 outputs and calculated face metrics.')


if __name__ == '__main__':
    main()
