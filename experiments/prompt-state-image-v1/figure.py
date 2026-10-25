"""Arrange complete first-output photographs; source pixels remain unchanged."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;REPO=R.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 prepared=json.loads((R/'prepared.json').read_text());ledger=json.loads((R/'calls.json').read_text());jobs={x['job']:R/x['folder']/'output.png' for x in ledger['calls']}
 selected=[next(r for r in prepared['conditions'] if r['person']=='R02' and r['history']=='S2' and r['mode']==mode) for mode in ['full_history','unchecked_state','checked_state']]
 paths=[jobs[x['job']] for x in selected];ims=[Image.open(p).convert('RGB') for p in paths]
 font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',32)
 canvas=Image.new('RGB',(1800,960),'white');draw=ImageDraw.Draw(canvas)
 for j,(im,label) in enumerate(zip(ims,['Full request history','State without checks','State with checks'])):
  im.thumbnail((590,900));canvas.paste(im,(j*600+(600-im.width)//2,60+(900-im.height)//2));draw.text((j*600+15,10),label,fill='black',font=font)
 out=REPO/'paper/figures/prompt-state-image-s2.png';canvas.save(out)
 record=dict(figure=str(out.relative_to(REPO)),figure_sha256=sha(out),selection='Illustration of conditional/quoted S2 request dialogue, R02; aggregate analysis uses all 18 conditions',sources=[dict(condition=x['id'],source=str(p.relative_to(REPO)),sha256=sha(p)) for x,p in zip(selected,paths)],script_sha256=sha(Path(__file__)),display='Full photographs, aspect ratio preserved, no crop')
 (REPO/'paper/figures/prompt-state-image-provenance.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
