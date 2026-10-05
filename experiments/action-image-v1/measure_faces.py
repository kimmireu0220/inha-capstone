"""Face metrics for all planned conditions, with unique pixel counts preserved."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from evaluate import packet, save, sha


def main():
    import cv2
    import numpy as np
    from PIL import Image
    from insightface.app import FaceAnalysis
    root = Path(sys.argv[1]).resolve()
    packet(root)  # Enforce complete generation and hashes before any measurement.
    prepared = json.loads((root / 'prepared.json').read_text())
    ledger = json.loads((root / 'calls.json').read_text())
    repo = Path(__file__).resolve().parents[2]
    app = FaceAnalysis(name='buffalo_l', root=str(Path.home() / '.insightface'),
                       allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=-1, det_thresh=0.5, det_size=(640, 640))

    def embedding(path):
        image = cv2.imread(str(path))
        assert image is not None
        found = app.get(image)
        return len(found), found[0].normed_embedding.astype(np.float64) if len(found) == 1 else None

    references = {}
    for person in sorted({r['person'] for r in prepared['conditions']}):
        count, vector = embedding(repo / 'experiments/state-tracking-v2/references' / f'{person}.png')
        assert count == 1, 'Reference must have exactly one detected face'
        references[person] = vector
    jobs = {}
    for call in ledger['calls']:
        path = root / call['folder'] / 'output.png'
        count, vector = embedding(path)
        with Image.open(path) as source:
            rgb = source.convert('RGB')
            digest = hashlib.sha256(str(rgb.size).encode() + rgb.tobytes()).hexdigest()
        jobs[call['job']] = {'face_count': count, 'rgb_sha256': digest,
                            'identity_similarity': None if vector is None else float(np.dot(references[call['person']], vector))}
    rows = [{'id': row['id'], 'person': row['person'], 'history': row['history'], 'turn': row['turn'],
             'mode': row['mode'], 'job': row['job'], **jobs[row['job']]} for row in prepared['conditions']]
    model_folder = Path.home() / '.insightface/models/buffalo_l'
    result = {'metric': 'InsightFace buffalo_l original-to-output cosine similarity',
              'input_sha256': {'prepared.json': sha(root / 'prepared.json'), 'calls.json': sha(root / 'calls.json')},
              'script_sha256': sha(Path(__file__)), 'model_sha256': {p.name: sha(p) for p in sorted(model_folder.glob('*.onnx'))},
              'versions': {name: importlib.metadata.version(name) for name in ['insightface', 'onnxruntime', 'numpy']},
              'conditions': len(rows), 'unique_jobs': len(jobs),
              'unique_rgb_images': len({r['rgb_sha256'] for r in jobs.values()}), 'rows': rows}
    save(root / 'face-results.json', result)
    print('Measured', len(rows), 'conditions;', len(jobs), 'jobs;', result['unique_rgb_images'], 'unique RGB images')


if __name__ == '__main__':
    main()
