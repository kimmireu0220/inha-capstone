"""Verify the pilot outputs and compare original-to-final face identity."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def detect(app, path):
    image = cv2.imread(str(path))
    if image is None:
        raise RuntimeError(f'Cannot read {path}')
    faces = app.get(image)
    if len(faces) != 1:
        return {'face_count': len(faces), 'error': 'expected exactly one face'}
    face = faces[0]
    return {'face_count': 1, 'score': float(face.det_score),
            'bbox': [float(x) for x in face.bbox],
            'embedding': face.normed_embedding.astype(np.float64)}

def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    ledger = json.loads((ROOT / 'calls.json').read_text())
    assert sha(ROOT / 'PROTOCOL.md') == plan['protocol_sha256']
    for path, digest in plan['code_sha256'].items():
        assert sha(REPO / 'local-studio' / path) == digest
    for person, info in plan['people'].items():
        assert sha(REPO / info['source']) == info['source_sha256']
        assert (ROOT / f'reference-{person}.png').is_file()
    calls = ledger['calls']
    assert len({(c['person'], c['mode'], c['stage']) for c in calls}) == len(calls)
    for call in calls:
        version = call['version']
        folder = ROOT / call['artifact_dir']
        output, input_image, prompt = (folder / name for name in ['output.png', 'input.png', 'prompt.txt'])
        assert sha(output) == version['output_sha256']
        assert sha(input_image) == version['input_sha256']
        assert prompt.read_text() == version['prompt']
        assert version['state'] == plan['states'][call['stage'] - 1]
        if call['mode'] == 'sequential' and call['stage'] > 1:
            prior = next(c for c in calls if c['person'] == call['person'] and
                         c['mode'] == call['mode'] and c['stage'] == call['stage'] - 1)
            assert version['input_version'] == prior['version']['id']
            assert version['input_sha256'] == prior['version']['output_sha256']
        else:
            assert version['input_version'] is None
            assert version['input_sha256'] == sha(ROOT / f"reference-{call['person']}.png")

    app = FaceAnalysis(name='buffalo_l', root=str(Path.home() / '.insightface'),
        allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=-1, det_thresh=0.5, det_size=(640, 640))
    references = {person: detect(app, ROOT / f'reference-{person}.png')
                  for person in plan['people']}
    results = []
    for call in calls:
        output = ROOT / call['artifact_dir'] / 'output.png'
        face = detect(app, output)
        reference = references[call['person']]
        row = {k: call[k] for k in ['person', 'seed', 'mode', 'stage', 'artifact_dir']}
        row.update({'output_sha256': sha(output), 'face_count': face['face_count'],
                    'detection_score': face.get('score')})
        if face['face_count'] == reference['face_count'] == 1:
            row['identity_similarity'] = float(np.dot(reference['embedding'], face['embedding']))
        else:
            row['identity_similarity'] = None
            row['error'] = 'single-face detection failed'
        results.append(row)
    pairs = []
    for person in plan['people']:
        selected = {r['mode']: r for r in results if r['person'] == person and r['stage'] == 3}
        if len(selected) != 2:
            continue
        call_by_mode = {mode: next(c for c in calls if c['person'] == person and
                        c['mode'] == mode and c['stage'] == 3) for mode in selected}
        prompts_equal = call_by_mode['sequential']['version']['prompt'] == call_by_mode['regenerate']['version']['prompt']
        assert prompts_equal
        a = selected['regenerate']['identity_similarity']
        b = selected['sequential']['identity_similarity']
        pairs.append({'person': person, 'seed': plan['seed'],
                      'regenerate_similarity': a, 'sequential_similarity': b,
                      'difference': a - b if a is not None and b is not None else None,
                      'final_prompts_equal': prompts_equal})
        sources = [(ROOT / f'reference-{person}.png', 'ORIGINAL'),
                   (ROOT / selected['regenerate']['artifact_dir'] / 'output.png', 'REGENERATE'),
                   (ROOT / selected['sequential']['artifact_dir'] / 'output.png', 'SEQUENTIAL')]
        thumbnails = []
        for path, label in sources:
            with Image.open(path) as im:
                thumb = im.convert('RGB')
                thumb.thumbnail((512, 768))
                thumbnails.append((thumb, label))
        sheet = Image.new('RGB', (1536, max(thumb.height for thumb, _ in thumbnails) + 38), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, (thumb, label) in enumerate(thumbnails):
            sheet.paste(thumb, (512 * i + (512 - thumb.width) // 2, 38))
            draw.text((512 * i + 12, 12), f'{person} / {label}', fill='black')
        sheet.save(ROOT / f'comparison-{person}.png')
    complete = len(calls) == plan['expected_outputs'] and len(pairs) == len(plan['people'])
    clean_refs = {p: {k: v for k, v in data.items() if k != 'embedding'}
                  for p, data in references.items()}
    output = {'complete': complete, 'outputs': len(calls), 'paired_comparisons': len(pairs),
              'independent_people': len(plan['people']), 'references': clean_refs,
              'rows': results, 'pairs': pairs,
              'method': {'model': 'InsightFace buffalo_l/w600k_r50',
                         'detector': 'det_10g', 'det_size': [640, 640],
                         'det_thresh': 0.5, 'metric': 'original-to-output cosine similarity'}}
    save(ROOT / 'results.json', output)
    save(ROOT / 'verification.json', {'complete': complete,
        'verified_outputs': len(calls), 'verified_pairs': len(pairs),
        'lineage_and_hashes_verified': True, 'final_prompts_equal': all(p['final_prompts_equal'] for p in pairs),
        'protocol_sha256': sha(ROOT / 'PROTOCOL.md'), 'analysis_sha256': sha(Path(__file__))})
    lines = ['# 실제 인물 2명 예비 비교', '',
             f"상태: {'완료' if complete else '진행 중'} · 출력 {len(calls)}/8개 · 최종 비교 {len(pairs)}/2쌍", '',
             '| 인물 | 원본 기반 얼굴 유사도 ↑ | 순차 얼굴 유사도 ↑ | 차이 |',
             '| --- | ---: | ---: | ---: |']
    for pair in pairs:
        fmt = lambda value: f'{value:.6f}' if value is not None else '검출 실패'
        lines.append(f"| {pair['person']} | {fmt(pair['regenerate_similarity'])} | {fmt(pair['sequential_similarity'])} | {fmt(pair['difference'])} |")
    lines.extend(['', '시드 42의 2인물 탐색적 관측이다. 요청 반영과 얼굴 유사도는 별도로 확인하며, 기존 합성 인물 결과와 합산하지 않는다.',
                  '', '[프로토콜](PROTOCOL.md) · [전체 수치](results.json) · [검증](verification.json)'])
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'complete': complete, 'outputs': len(calls), 'pairs': pairs}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
