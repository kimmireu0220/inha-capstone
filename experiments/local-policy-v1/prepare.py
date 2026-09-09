import json,hashlib
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parent; repo=R.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
src=repo/'experiments/trigger-validation-v1/P04/reference.png'
Image.open(src).convert('RGB').resize((512,768),Image.Resampling.LANCZOS).save(R/'reference.png')
base=(repo/'experiments/local-open-model-v1/prompt.txt').read_text().split('Apply the following')[0]
requirements=['The existing long-sleeve crewneck shirt is navy blue; keep its shape and fabric texture.','The plain studio background is uniform pale blue; keep lighting on the person unchanged.','Add exactly one small silver circular pin on the chest on the viewer-right side.']
jobs=[]
for seed,arms in [(42,['batch','sequential']),(314,['sequential','batch'])]:
 for arm in arms:
  for stage in range(1,2 if arm=='batch' else 4):
   name=f'{arm}-{seed}-s{stage}'
   prompt=base+'Apply the following complete current requirements; preserve everything else:\n'+ '\n'.join('- '+x for x in requirements[:3 if arm=='batch' else stage])
   (R/(name+'.txt')).write_text(prompt)
   jobs.append(dict(id=name,seed=seed,arm=arm,stage=stage,input='reference.png' if stage==1 else f'generated/{arm}-{seed}-s{stage-1}.png',output=f'generated/{name}.png',prompt_file=name+'.txt',prompt_sha256=sha(R/(name+'.txt'))))
(R/'plan.json').write_text(json.dumps(dict(source=str(src.relative_to(repo)),source_sha256=sha(src),reference_sha256=sha(R/'reference.png'),protocol_sha256=sha(R/'PROTOCOL.md'),jobs=jobs),indent=2)+'\n')
