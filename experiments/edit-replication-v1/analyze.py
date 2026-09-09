"""Incremental measurement of saved outputs; never generates or reads human labels."""
import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import lpips
import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE = REPO / 'experiments/nonhuman-followup-v1/metrics/analyze.py'
SPEC = importlib.util.spec_from_file_location('existing_metrics', SOURCE)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def local(path):
    return REPO / ('experiments/' + path.split('/experiments/', 1)[1])


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def stats(values):
    return {'n': len(values), 'values': values, 'mean': float(np.mean(values)),
            'min': min(values), 'max': max(values)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--partial', action='store_true')
    args = parser.parse_args()
    plan = json.loads((ROOT / 'plan.json').read_text())
    assert M.sha(ROOT / 'PROTOCOL.md') == plan['protocol_sha256']
    for person in plan['people'].values():
        assert M.sha(local(person['reference'])) == person['reference_sha256']
    assert len(plan['jobs']) == 16 and len({j['id'] for j in plan['jobs']}) == 16
    jobs = {j['id']: j for j in plan['jobs']}
    completed = [j for j in plan['jobs'] if local(j['output']).exists()]
    if not args.partial:
        assert len(completed) == 16, len(completed)
    torch.set_num_threads(2)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    network = lpips.LPIPS(net='alex', version='0.1', verbose=False).cpu().eval()
    state = hashlib.sha256()
    for name, value in sorted(network.state_dict().items()):
        state.update(name.encode()); state.update(str(tuple(value.shape)).encode())
        state.update(value.cpu().numpy().tobytes())
    prior = json.loads((SOURCE.parent / 'manifest.json').read_text())
    assert state.hexdigest() == prior['lpips_state_dict_sha256']
    signature = {'metric_source_sha256': M.sha(SOURCE), 'analysis_sha256': M.sha(Path(__file__)),
                 'plan_sha256': M.sha(ROOT / 'plan.json'), 'lpips_state_dict_sha256': state.hexdigest()}
    cache = ROOT / 'measured'
    cache.mkdir(exist_ok=True)
    person = next(iter(plan['people'].values()))
    ref = M.image(local(person['reference']))
    M.REGIONS = person['skin_regions']
    control = M.measure(ref, ref, person['roi'], network, True)
    for mode in M.MODES:
        assert control['face'][mode]['mae'] == 0 and control['face'][mode]['ssim'] == 1
        assert abs(control['face'][mode]['lpips']) < 1e-7
        assert control['skin'][mode]['mae'] == control['skin'][mode]['highpass_mae'] == 0
    rows, hashes, pixels = [], {}, defaultdict(list)
    for job in completed:
        person = plan['people'][job['person']]
        ref = M.image(local(person['reference']))
        M.REGIONS = person['skin_regions']
        path = local(job['output']); inp = local(job['input']); logpath = path.with_suffix('.call.json')
        log = json.loads(logpath.read_text())
        assert all(log[k] == v for k, v in job.items())
        assert log['status'] == 'success' and log['attempt'] == 1
        assert M.sha(path) == log['output_sha256'] and M.sha(inp) == log['input_sha256']
        if job['stage'] > 1:
            prev = jobs[f"{job['person']}-{job['order']}-r{job['repeat']}-s{job['stage']-1}"]
            assert job['input'] == prev['output']
            prevlog = json.loads(inp.with_suffix('.call.json').read_text())
            assert prevlog['completed'] <= log['started']
        else:
            assert job['input'] == person['reference']
        for p in (path, inp, logpath):
            hashes[str(p.relative_to(REPO))] = M.sha(p)
        with Image.open(path) as im:
            assert im.size == (1024, 1536)
            pixel = hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()
        pixels[pixel].append(job['id'])
        key = {**signature, 'input_sha256': log['input_sha256'], 'output_sha256': log['output_sha256']}
        dest = cache / (job['id'] + '.json')
        old = json.loads(dest.read_text()) if dest.exists() else None
        if old and old['signature'] == key:
            row = old
        else:
            a = M.image(path)
            original = M.measure(a, ref, person['roi'], network, True)
            previous = original if job['stage'] == 1 else M.measure(a, M.image(inp), person['roi'], network, True)
            row = {k: job[k] for k in ('id', 'person', 'order', 'repeat', 'stage', 'added', 'completed_set')}
            row.update(signature=key, pixel_sha256=pixel, original=original, previous=previous)
            save(dest, row)
        rows.append(row)
        print(f"[{len(rows)}/{len(completed)}] {job['id']} LPIPS={row['original']['face']['fixed']['lpips']:.6f}", flush=True)

    groups = defaultdict(list)
    for r in rows:
        if r['stage'] == (1 if r['order'] == 'batch' else 3):
            groups[r['person'] + ':final:' + r['order']].append(r)
        if r['order'] != 'batch':
            groups[f"{r['person']}:stage:{r['stage']}:added:{r['added']}"].append(r)
            if r['stage'] == 2:
                groups[r['person'] + ':two_step:' + r['order'][:2]].append(r)
    summary = {}
    for group, selected in groups.items():
        summary[group] = {'ids': [r['id'] for r in selected], 'n_paths': len(selected),
                          'metrics': {basis: {scope: {mode: {k: stats([r[basis][scope][mode][k] for r in selected])
                                                for k in keys} for mode in M.MODES}
                                          for scope, keys in [('face', M.FACE_KEYS), ('skin', M.SKIN_KEYS)]}
                                      for basis in ('original', 'previous')}}
    result = {'complete': len(rows) == 16, 'planned': 16, 'measured': len(rows), 'rows': rows,
              'summary': summary, 'unique_pixel_outputs': len(pixels),
              'duplicate_pixel_groups': [v for v in pixels.values() if len(v) > 1],
              'boundary_hits': {basis: sum(v['boundary'] for r in rows for v in r[basis]['locations'].values())
                                for basis in ('original', 'previous')},
              'identity_control': control, 'human_evaluation': 'not_collected',
              'independent_agent_evaluation': 'not_collected'}
    for path, digest in hashes.items():
        assert M.sha(REPO / path) == digest
    save(ROOT / 'results.json', result)
    save(ROOT / 'manifest.json', {'signature': signature, 'files_sha256': hashes, 'people': plan['people'], 'device': 'cpu', 'threads': 2,
                                 'packages': {k: importlib.metadata.version(k) for k in
                                              ('torch', 'torchvision', 'numpy', 'lpips', 'Pillow', 'scipy', 'scikit-image')},
                                 'generation_model_version': 'not_exposed', 'generation_seed': 'not_exposed',
                                 'generation_tool': 'image_gen.imagegen', 'complete': result['complete']})
    with (ROOT / 'metrics.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'person', 'order', 'repeat', 'stage', 'added', 'completed_set',
                                              'basis', 'scope', 'region', 'mode', 'mae', 'ssim', 'lpips', 'highpass_mae'],
                                lineterminator='\n')
        writer.writeheader()
        for r in rows:
            for basis in ('original', 'previous'):
                for mode in M.MODES:
                    base = {**{k: r[k] for k in ('id', 'person', 'order', 'repeat', 'stage', 'added', 'completed_set')},
                            'basis': basis, 'mode': mode}
                    writer.writerow({**base, 'scope': 'face', 'region': 'whole_roi', **r[basis]['face'][mode]})
                    skin = r[basis]['skin'][mode]
                    for region, v in [('weighted_three_regions', skin), *skin['regions'].items()]:
                        writer.writerow({**base, 'scope': 'skin', 'region': region, **{k: v[k] for k in M.SKIN_KEYS}})
    print(json.dumps({k: result[k] for k in ('complete', 'measured', 'unique_pixel_outputs', 'boundary_hits')}))


if __name__ == '__main__':
    main()
