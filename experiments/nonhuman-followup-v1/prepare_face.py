"""Create blinded scientific crop plates without changing the source images."""
import hashlib,json,random
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
EXP=ROOT.parent
def read(p):return json.loads(p.read_text())
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
branches=read(EXP/'revised-tail-v1/progress.json')['branches']
spec={b['name']:b for b in branches}
unique={}
for r in read(EXP/'revised-tail-v1/curves.json'):
    b=spec[r['branch']]; k=(sha(b['reference']),r['sha256'])
    unique.setdefault(k,dict(reference=b['reference'],path=r['path'],roi=b['roi'],sources=[]))['sources'].append(dict(branch=r['branch'],stage=r['stage']))
items=list(unique.values())
refs={sha(b['reference']):b for b in branches}
for b in refs.values():items.append(dict(reference=b['reference'],path=b['reference'],roi=b['roi'],sources=[],control='identity'))
rng=random.Random(260906)
for i in rng.sample(range(len(unique)),8):items.append(dict(items[i],duplicate_of_source=sha(items[i]['path'])))
rng.shuffle(items)
public=[];private=[]
out=ROOT/'blind-face';out.mkdir(exist_ok=True)
plates=[]
for n,item in enumerate(items):
    uid=hashlib.sha256(f'face-packet-v1-{n}-260906'.encode()).hexdigest()[:10]
    with Image.open(item['reference']) as im:a=im.convert('RGB').crop(item['roi'])
    with Image.open(item['path']) as im:b=im.convert('RGB').crop(item['roi'])
    assert a.size==b.size==(320,360)
    pair=Image.new('RGB',(660,400),'white');d=ImageDraw.Draw(pair)
    d.text((12,8),uid+'  REFERENCE',fill='black');d.text((342,8),'CANDIDATE',fill='black')
    pair.paste(a,(0,32));pair.paste(b,(336,32))
    pair.save(out/f'{uid}.png')
    public.append(dict(id=uid,image=str(out/f'{uid}.png')))
    private.append(dict(id=uid,**item,reference_sha256=sha(item['reference']),output_sha256=sha(item['path'])))
    plates.append(pair)
sheets=[]
for offset in range(0,len(plates),4):
    sheet=Image.new('RGB',(1320,800),'white')
    for j,pair in enumerate(plates[offset:offset+4]):sheet.paste(pair,((j%2)*660,(j//2)*400))
    dest=out/f'sheet-{offset//4+1:02d}.png';sheet.save(dest)
    sheets.append(dict(image=str(dest),ids=[x['id'] for x in public[offset:offset+4]]))
save(out/'items.json',public);save(out/'sheets.json',sheets)
save(ROOT/'private/face-key.json',private)
print(json.dumps(dict(unique_candidates=len(unique),controls=6,hidden_repeats=8,total=len(items),sheets=len(sheets))))
