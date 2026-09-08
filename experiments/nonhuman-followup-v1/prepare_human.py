"""Export current final candidates, never AI ratings or method labels."""
import hashlib,json,shutil
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent
SITE=ROOT.parent.parent/'evaluation'
keys=json.loads((ROOT/'private/requirements-key.json').read_text())
face={x['output_sha256']:x for n in ['face','extension-face','coverage-face'] for x in json.loads((ROOT/f'private/{n}-key.json').read_text())}
out=SITE/'public/current-review';out.mkdir(exist_ok=True)
items=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for x in keys:
    uid=x['id'];f=face[x['output_sha256']]
    paths={}
    for kind,src in [('reference',x['reference']),('candidate',x['path'])]:
        dest=out/f'{uid}-{kind}.png';shutil.copy2(src,dest);assert sha(src)==sha(dest)
        crop=out/f'{uid}-{kind}-crop.png'
        with Image.open(src) as im:im.convert('RGB').crop(f['roi']).save(crop)
        paths[kind]=f'/current-review/{dest.name}';paths[kind+'Crop']=f'/current-review/{crop.name}'
    items.append(dict(id=uid,**paths))
assert len(items)==16
(SITE/'app/current-review').mkdir(exist_ok=True)
(SITE/'app/current-review/data.json').write_text(json.dumps(items,indent=2)+'\n')
print('16 unique final candidates; no ratings or methods exported')
