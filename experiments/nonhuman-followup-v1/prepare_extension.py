"""Make deterministic blinded observation materials; preserve source image bytes."""
import hashlib,json,random,shutil
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def uid(label):return hashlib.sha256(label.encode()).hexdigest()[:12]
def copy(src,dst):
    if dst.exists():assert sha(src)==sha(dst)
    else:shutil.copy2(src,dst)
def main():
    progress=read(ROOT/'generation/progress.json')
    assert progress['collection_complete'], 'Run only after generation collection has terminated.'
    old=read(ROOT.parent/'revised-tail-v1/progress.json')['branches']
    new=progress['branches']; specs={b['name']:b for b in old+new}
    calls=[read(p) for p in sorted((ROOT/'generation/generated').glob('*.call.json'))]
    assert len(calls)==25 and progress['new_failed_calls']==1
    face=[]
    for c in calls:
        b=specs[c['branches'][0]]
        assert sha(c['output'])==c['output_sha256']
        face.append(dict(reference=b['reference'],path=c['output'],roi=b['roi'],output_sha256=c['output_sha256'],reference_sha256=sha(b['reference']),sources=[dict(branch=name,stage=c['stage']) for name in c['branches']]))
    assert len({x['output_sha256'] for x in face})==25
    rng=random.Random(26090627)
    refs=list({sha(b['reference']):b for b in old}.values())
    for b in rng.sample(refs,4):face.append(dict(reference=b['reference'],path=b['reference'],roi=b['roi'],output_sha256=sha(b['reference']),reference_sha256=sha(b['reference']),sources=[],control='reference_reference'))
    for i in rng.sample(range(25),4):face.append(dict(face[i],duplicate_of_source=face[i]['output_sha256']))
    rng.shuffle(face)
    public=[];private=[];plates=[]
    dest=ROOT/'blind-extension-face';dest.mkdir(exist_ok=True)
    for i,x in enumerate(face):
        key=uid(f'extension-face-26090627-{i}')
        with Image.open(x['reference']) as im:a=im.convert('RGB').crop(x['roi'])
        with Image.open(x['path']) as im:b=im.convert('RGB').crop(x['roi'])
        assert a.size==b.size==(320,360)
        pair=Image.new('RGB',(660,400),'white');draw=ImageDraw.Draw(pair)
        draw.text((12,8),key+' REFERENCE',fill='black');draw.text((342,8),'CANDIDATE',fill='black')
        pair.paste(a,(0,32));pair.paste(b,(336,32));pair.save(dest/f'{key}.png')
        public.append(dict(id=key,image=str(dest/f'{key}.png')));private.append(dict(id=key,**x));plates.append(pair)
    sheets=[]
    for offset in range(0,len(plates),4):
        sheet=Image.new('RGB',(1320,800),'white')
        for j,p in enumerate(plates[offset:offset+4]):sheet.paste(p,((j%2)*660,(j//2)*400))
        path=dest/f'sheet-{offset//4+1:02d}.png';sheet.save(path)
        sheets.append(dict(image=str(path),ids=[x['id'] for x in public[offset:offset+4]]))
    save(dest/'items.json',public);save(dest/'sheets.json',sheets);save(ROOT/'private/extension-face-key.json',private)
    finals={}
    for b in old+new:
        r=b['rows'][-1]
        if r['stage']!=10:
            assert b['name']=='P05-once-triggered' and b['stopped']['stage']==9
            continue
        p=r.get('output',r.get('final',r.get('path')));k=(sha(b['reference']),sha(p))
        finals.setdefault(k,dict(reference=b['reference'],path=p,reference_sha256=k[0],output_sha256=k[1],sources=[]))['sources'].append(b['name'])
    candidates=list(finals.values());rng.shuffle(candidates)
    dest=ROOT/'blind-requirements';dest.mkdir(exist_ok=True)
    public=[];private=[]
    for i,x in enumerate(candidates):
        key=uid(f'requirements-final-26090627-{i}');ref=uid('reference-'+x['reference_sha256'])
        candidate=dest/f'{key}.png';reference=dest/f'{ref}.png'
        copy(x['path'],candidate);copy(x['reference'],reference)
        public.append(dict(id=key,candidate=str(candidate),reference=str(reference)))
        private.append(dict(id=key,**x))
    save(dest/'items.json',public);save(ROOT/'private/requirements-key.json',private)
    save(ROOT/'packet-audit.json',dict(new_face_candidates=25,face_controls=4,face_repeats=4,face_total=len(face),face_sheets=len(sheets),final_unique_candidates=len(candidates),final_branch_count=sum(len(x['sources']) for x in candidates),omitted_final_branches=['P05-once-triggered'],source_hashes_verified=True))
    print(json.dumps(read(ROOT/'packet-audit.json')))
if __name__=='__main__':main()
