import hashlib
import json
from pathlib import Path
from run import benchmark, save

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
data = benchmark()
items = []
for person in ['R01', 'R02']:
    ref = REPO / 'experiments/state-tracking-v2/references' / f'{person}.png'
    for level in ['single', 'compound', 'mixed']:
        request = data[f'C1-{level}'][0]['request']
        prompt = ('Edit the supplied portrait photograph. ' + request +
                  ' Left and right refer to the depicted person\'s own left and right. '
                  'Preserve the person\'s identity, hair, age, body proportions and all unrequested attributes. '
                  'Keep the original camera framing. Return one photorealistic edited photograph without text or labels.')
        goals = ['The person has a closed-mouth smile; no teeth are visible.']
        if level != 'single':
            goals += ['The torso is turned toward the person\'s own left (toward viewer-right), rather than square to the camera.',
                      'The person\'s right hand is raised rather than resting down or in a pocket.']
        if level == 'mixed':
            goals += ['The person wears a navy jacket.', 'The background is blue.', 'A plant is present.']
        items.append(dict(id=f'{person}-{level}', reference=str(ref.relative_to(REPO)),
                          reference_sha256=hashlib.sha256(ref.read_bytes()).hexdigest(), prompt=prompt, goals=goals))
plan = dict(stage='oracle-generation-diagnostic', conditions=items,
            protocol_sha256=hashlib.sha256((ROOT / 'image_protocol.md').read_bytes()).hexdigest())
path = ROOT / 'image-plan.json'
if path.exists():
    assert json.loads(path.read_text()) == plan
else:
    save(path, plan)
print('Frozen 6 oracle image conditions')
