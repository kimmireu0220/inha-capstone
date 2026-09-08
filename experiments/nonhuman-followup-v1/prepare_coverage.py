"""Blind only reused policy outputs not already present in the two face packets."""
import hashlib,json,random
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
def read(n):return json.loads((ROOT/n).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,x):
    p=ROOT/n;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
known={(r['reference_sha256'],r['output_sha256']) for n in ['private/face-key.json','private/extension-face-key.json'] for r in read(n)}
missing={}
for b in read('generation/progress.json')['branches']:
    for r in b['rows']:
        key=(sha(b['reference']),sha(r['output']))
        if key in known:continue
        missing.setdefault(key,dict(reference=b['reference'],path=r['output'],roi=b['roi'],reference_sha256=key[0],output_sha256=key[1],sources=[]))['sources'].append(dict(branch=b['name'],stage=r['stage']))
assert len(missing)==3
items=list(missing.values());random.Random(26090603).shuffle(items)
dest=ROOT/'blind-coverage-face';dest.mkdir(exist_ok=True)
public=[];private=[];sheet=Image.new('RGB',(1320,800),'white')
for i,x in enumerate(items):
    key=hashlib.sha256(f'coverage-26090603-{i}'.encode()).hexdigest()[:12]
    with Image.open(x['reference']) as im:a=im.convert('RGB').crop(x['roi'])
    with Image.open(x['path']) as im:b=im.convert('RGB').crop(x['roi'])
    pair=Image.new('RGB',(660,400),'white');d=ImageDraw.Draw(pair)
    d.text((12,8),key+' REFERENCE',fill='black');d.text((342,8),'CANDIDATE',fill='black')
    pair.paste(a,(0,32));pair.paste(b,(336,32));pair.save(dest/f'{key}.png')
    sheet.paste(pair,((i%2)*660,(i//2)*400))
    public.append(dict(id=key,image=str(dest/f'{key}.png')));private.append(dict(id=key,**x))
sheet.save(dest/'sheet-01.png')
save('blind-coverage-face/items.json',public);save('blind-coverage-face/sheets.json',[dict(image=str(dest/'sheet-01.png'),ids=[x['id'] for x in public])]);save('private/coverage-face-key.json',private)
print(json.dumps(dict(coverage_candidates=3)))
