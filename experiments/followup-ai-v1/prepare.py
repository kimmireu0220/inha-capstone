"""Lossless scientific crop plates, using the existing face packet layout."""
import hashlib,json,random,secrets
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
    assert not (ROOT/'private/key.json').exists()
    data=json.loads((REPO/'evaluation/app/followup-survey/data.json').read_text())
    items=[dict(source_id=c['id'],reference=str(REPO/'evaluation/public'/c['reference'].lstrip('/')),path=str(REPO/'evaluation/public'/c['candidate'].lstrip('/')),roi=c['roi'],kind='candidate') for c in data]
    seen=set()
    for c in items.copy():
        h=sha(c['reference'])
        if h not in seen:items.append({**c,'path':c['reference'],'kind':'identity_control'});seen.add(h)
    assert len(items)==15
    random.Random(260909).shuffle(items)
    private=[];public=[];plates=[]
    for c in items:
        uid=secrets.token_hex(5)
        with Image.open(c['reference']) as im:a=im.convert('RGB').crop(c['roi'])
        with Image.open(c['path']) as im:b=im.convert('RGB').crop(c['roi'])
        assert a.size==b.size==(320,360)
        plate=Image.new('RGB',(660,400),'white');draw=ImageDraw.Draw(plate)
        draw.text((8,8),uid+'  REFERENCE',fill='black');draw.text((342,8),'CANDIDATE',fill='black')
        plate.paste(a,(0,32));plate.paste(b,(336,32));plate.save(ROOT/'plates'/f'{uid}.png')
        assert plate.crop((0,32,320,392)).tobytes()==a.tobytes()
        assert plate.crop((336,32,656,392)).tobytes()==b.tobytes()
        private.append({'id':uid,**c,'reference_sha256':sha(c['reference']),'output_sha256':sha(c['path']),'reference_crop_pixels_sha256':hashlib.sha256(a.tobytes()).hexdigest(),'candidate_crop_pixels_sha256':hashlib.sha256(b.tobytes()).hexdigest()})
        public.append({'id':uid,'image':str(ROOT/'plates'/f'{uid}.png')});plates.append(plate)
    sheets=[]
    for i in range(0,15,3):
        sheet=Image.new('RGB',(660,1200),'white')
        for j,p in enumerate(plates[i:i+3]):sheet.paste(p,(0,j*400))
        path=ROOT/'plates'/f'sheet-{i//3+1}.png';sheet.save(path);sheets.append({'path':str(path),'ids':[c['id'] for c in public[i:i+3]]})
    save(ROOT/'private/key.json',private);save(ROOT/'items.json',public);save(ROOT/'sheets.json',sheets)
    save(ROOT/'packet-verification.json',{'passed':True,'unique_candidates':12,'identity_controls':3,'lossless_crop_and_placement':True,'protocol_sha256':sha(ROOT/'PROTOCOL.md'),'prepare_sha256':sha(Path(__file__)),'plate_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'plates').glob('*.png')}})
    print('Prepared 15 plates in five sheets.')
if __name__=='__main__':main()
