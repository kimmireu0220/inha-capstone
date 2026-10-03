"""Verify all control outputs and measure only previously unseen face images."""
import importlib.util
import json
from pathlib import Path
from prepare import ROOT, REPO, SOURCE, save, sha
from run import signature, verify_files


def main():
    plan = json.loads((ROOT / 'plan.json').read_text())
    calls = json.loads((ROOT / 'calls.json').read_text())['calls']
    original = json.loads((SOURCE / 'plan.json').read_text())
    assert sha(SOURCE / 'plan.json') == plan['source_plan_sha256']
    assert sha(SOURCE / 'calls.json') == plan['source_calls_sha256']
    assert sha(ROOT / 'prepare-manifest.json') == plan['prepare_manifest_sha256']
    assert sha(ROOT / 'run.py') == plan['runner_sha256']
    manifest = json.loads((ROOT / 'prepare-manifest.json').read_text())
    for relative, digest in manifest['inputs'].items():
        assert sha(REPO / relative) == digest
    for group in ['prompts', 'transcripts']:
        for name, digest in manifest[group].items():
            assert sha(ROOT / 'prompts' / name) == digest
    expected = {(p, h, s) for p in original['people_order']
                for h in original['histories'] for s in original['seeds']}
    assert len(calls) == 48 and {(r['person'], r['history'], r['seed']) for r in calls} == expected
    pending = json.loads((ROOT / 'pending-ratings.json').read_text())
    ratings = json.loads((ROOT / 'ai-ratings.json').read_text()) if pending else {'ratings': {}}
    assert set(ratings['ratings']) == set(pending), 'Finish primary masked ratings before metrics'
    base_rows = json.loads((SOURCE / 'face-results.json').read_text())['rows']
    assert len(base_rows) == 96
    base_by_folder = {r['folder']: r for r in base_rows}
    rows, app, common, references = [], None, None, {}
    for row in calls:
        verify_files(ROOT, row)
        assert row['input_sha256'] == original['people'][row['person']]
        assert row['prompt_sha256'] == manifest['prompts'][row['history'] + '-structured.txt']
        assert row['model'] == plan['model'] and row['steps'] == plan['steps']
        if row['reused']:
            old = base_by_folder[row['reused_from']]
            enriched = {**old, 'model': original['model'], 'steps': original['steps']}
            assert signature(row) == signature(enriched)
            assert row['output_sha256'] == old['output_sha256']
            count, similarity = old['face_count'], old['identity_similarity']
        else:
            if app is None:
                spec = importlib.util.spec_from_file_location('face_analysis', SOURCE.parent / 'state-tracking-v1/analyze.py')
                common = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(common)
                app = common.FaceAnalysis(name='buffalo_l', root=str(Path.home() / '.insightface'),
                    allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider'])
                app.prepare(ctx_id=-1, det_thresh=0.5, det_size=(640, 640))
            person = row['person']
            if person not in references:
                references[person] = common.face(app, SOURCE / 'references' / (person + '.png'))[1]
                assert references[person] is not None
            count, embedding = common.face(app, ROOT / row['folder'] / 'output.png')
            similarity = float(common.np.dot(references[person], embedding)) if embedding is not None else None
        rows.append({**row, 'face_count': count, 'identity_similarity': similarity})
    save(ROOT / 'face-results.json', {'rows': rows,
         'metric': 'InsightFace buffalo_l original-to-output cosine similarity',
         'source_face_results_sha256': sha(SOURCE / 'face-results.json')})
    save(ROOT / 'verification.json', {'complete': True, 'outputs': 48,
         'reused': sum(r['reused'] for r in calls), 'analysis_sha256': sha(Path(__file__)),
         'frozen_inputs_prompts_and_output_hashes_verified': True})
    print('Verified all 48 control conditions; retained exact-image reuse provenance.')


if __name__ == '__main__':
    main()
