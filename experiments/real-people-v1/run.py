"""Run a two-person pilot through the local studio API, resuming completed calls."""
import base64
import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BASE = 'http://127.0.0.1:8770'
PEOPLE = {'R01': 'assets/people/real/pexels-6311573.jpg',
          'R02': 'assets/people/real/pexels-6311581.jpg'}
REQUESTS = ['셔츠를 남색으로 바꿔줘.', '배경을 옅은 파란색으로 바꿔줘.', '은색 핀 하나 추가해줘.']
STATES = [dict(shirt_color='navy', background='original', pin='original'),
          dict(shirt_color='navy', background='pale blue', pin='original'),
          dict(shirt_color='navy', background='pale blue', pin='silver')]
SEED = 42

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)

def bootstrap():
    return json.load(urllib.request.urlopen(BASE + '/api/bootstrap', timeout=30))

def post(path, body):
    request = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json', 'X-Studio-Token': bootstrap()['token']})
    return json.load(urllib.request.urlopen(request, timeout=30))

def project(pid):
    return next(p for p in bootstrap()['projects'] if p['id'] == pid)

def poll(job):
    for _ in range(1800):
        state = bootstrap()['jobs'][job['id']]
        if state['status'] != 'running':
            if state['status'] != 'done':
                raise RuntimeError(state)
            return project(job['project'])
        time.sleep(2)
    raise TimeoutError(job['id'])

def main():
    plan = {'people': {p: {'source': source, 'source_sha256': sha(REPO / source)}
                       for p, source in PEOPLE.items()}, 'seed': SEED,
            'requests': REQUESTS, 'states': STATES, 'expected_outputs': 8,
            'protocol_sha256': sha(ROOT / 'PROTOCOL.md'),
            'code_sha256': {p: sha(REPO / 'local-studio' / p)
                            for p in ['server.py', 'intent.py', 'state_model.py']}}
    plan_path = ROOT / 'plan.json'
    if plan_path.exists():
        assert json.loads(plan_path.read_text()) == plan
    else:
        save(plan_path, plan)
    ledger_path = ROOT / 'calls.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'projects': {}, 'calls': []}
    for person, source in PEOPLE.items():
        for mode in ['sequential', 'regenerate']:
            key = f'{person}-{SEED}-{mode}'
            pid = ledger['projects'].get(key)
            if pid is None:
                created = post('/api/create', {'image': base64.b64encode((REPO / source).read_bytes()).decode(),
                    'name': f'실제 인물 예비 비교 · {person} · {mode}'})
                pid = created['id']
                ledger['projects'][key] = pid
                save(ledger_path, ledger)
                shutil.copyfile(REPO / 'local-studio/data' / pid / 'reference.png', ROOT / f'reference-{person}.png')
            p = project(pid)
            if p['active_job']:
                p = poll(bootstrap()['jobs'][p['active_job']])
            if p.get('generation_mode') != mode or p.get('generation_seed') != SEED:
                p = post('/api/generation-settings', {'project': pid, 'revision': p['revision'],
                    'mode': mode, 'seed': SEED})
            for stage, (request, state) in enumerate(zip(REQUESTS, STATES), 1):
                if any(c['person'] == person and c['mode'] == mode and c['stage'] == stage
                       for c in ledger['calls']):
                    continue
                existing = next((v for v in p['versions'] if v['mode'] == mode and
                    v['seed'] == SEED and v['state'] == state), None)
                if existing is None:
                    if p['state'] != state:
                        p = poll(post('/api/chat', {'project': pid, 'revision': p['revision'],
                            'request': request}))
                        assert p['state'] == state, p['state']
                    if mode == 'regenerate' and stage < 3:
                        continue
                    print('START', person, mode, stage, flush=True)
                    job = post('/api/generate', {'project': pid, 'revision': p['revision']})
                    save(ROOT / 'running.json', {'status': 'running', 'person': person,
                        'mode': mode, 'stage': stage, 'completed': len(ledger['calls']), 'job': job})
                    p = poll(job)
                    existing = next(v for v in p['versions'] if v['id'] == p['current_version'])
                v = existing
                assert v['mode'] == mode and v['seed'] == SEED and v['state'] == state
                source_dir = REPO / 'local-studio/data' / pid / v['id']
                target_dir = ROOT / 'generated' / f'{key}-s{stage}'
                target_dir.mkdir(parents=True, exist_ok=True)
                for file in source_dir.iterdir():
                    if file.is_file():
                        shutil.copyfile(file, target_dir / file.name)
                ledger['calls'].append({'person': person, 'seed': SEED, 'mode': mode,
                    'stage': stage, 'project': pid, 'version': v,
                    'artifact_dir': str(target_dir.relative_to(ROOT))})
                save(ledger_path, ledger)
                print('DONE', len(ledger['calls']), '/8', person, mode, stage, flush=True)
    save(ROOT / 'running.json', {'status': 'complete', 'outputs': len(ledger['calls'])})

if __name__ == '__main__':
    main()
