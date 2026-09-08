"""Byte-copy full outputs and fixed analytical crops into opaque review sets."""
import hashlib
import json
import secrets
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def save(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
mapping_path = ROOT / 'blind-mapping.json'
if mapping_path.exists():
    mapping = json.loads(mapping_path.read_text())
else:
    mapping = []
    people = ['P04', 'P05', 'P06']
    secrets.SystemRandom().shuffle(people)
    for person in people:
        methods = ['baseline', 'rebase']
        secrets.SystemRandom().shuffle(methods)
        mapping.append({'person': person, 'group': secrets.token_hex(5),
                        'candidates': [{'method': m, 'id': secrets.token_hex(6)} for m in methods]})
    save(mapping_path, mapping)
groups = []
for row in mapping:
    folder = ROOT / row['person']
    stage = json.loads((folder/'trigger.json').read_text())['stage']
    state = json.loads((folder/'rebase-plan.json').read_text())['state']
    out = ROOT / 'blind' / row['group']
    out.mkdir(parents=True, exist_ok=True)
    group = {'id': row['group'], 'requirements': list(state.values()),
             'reference_full': str(out/'reference.png'), 'reference_crop': str(out/'reference-crop.png'), 'candidates': []}
    copies = [(folder/'reference.png', out/'reference.png'), (folder/'crops/reference.png', out/'reference-crop.png')]
    for candidate in row['candidates']:
        filename = f'step-{stage}.png' if candidate['method'] == 'baseline' else 'rebase.png'
        ident = candidate['id']
        group['candidates'].append({'id': ident, 'full': str(out/f'{ident}.png'), 'crop': str(out/f'{ident}-crop.png')})
        copies += [(folder/filename, out/f'{ident}.png'), (folder/'crops'/filename, out/f'{ident}-crop.png')]
    for source, target in copies:
        shutil.copyfile(source, target)
        assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest()
    groups.append(group)
save(ROOT/'blind/manifest.json', {'groups': groups})
print('Prepared three opaque pairs, 18 verified full/crop files.')
