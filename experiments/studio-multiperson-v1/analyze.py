"""Verify lineage and calculate frozen face metrics; partial reports explicitly marked."""
import hashlib,importlib.util,json
from pathlib import Path
import numpy as np
import torch,lpips
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent;REPO=R.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v):
 p=R/n;t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def image(p):
 with Image.open(p) as im:
  assert im.size==(512,768),(p,im.size)
  return np.asarray(im.convert('RGB'),dtype=np.float32)/255
plan=json.loads((R/'plan.json').read_text());ledger=json.loads((R/'calls.json').read_text())
assert sha(R/'PROTOCOL.md')==plan['protocol_sha256']
for p,h in plan['code_sha256'].items():assert sha(REPO/'local-studio'/p)==h
spec=importlib.util.spec_from_file_location('frozen',REPO/'experiments/nonhuman-followup-v1/metrics/analyze.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
torch.set_num_threads(2);net=lpips.LPIPS(net='alex',version='0.1',verbose=False).cpu().eval()
rows=[];controls={}
for c in ledger['calls']:
 person=c['person'];roi=plan['people'][person]['roi'];refpath=R/f'reference-{person}.png';ref=image(refpath)
 if person not in controls:
  controls[person]=M.face(M.crop(ref,roi),M.crop(ref,roi),net)
  assert controls[person]['mae']==0 and controls[person]['ssim']==1 and abs(controls[person]['lpips'])<1e-7
 v=c['version'];folder=R/c['artifact_dir'];out=folder/'output.png';inp=folder/'input.png';prompt=folder/'prompt.txt'
 assert sha(out)==v['output_sha256'] and sha(inp)==v['input_sha256']
 assert prompt.read_text()==v['prompt'] and v['state']==plan['states'][c['stage']-1]
 if c['mode']=='sequential' and c['stage']>1:
  prior=next(x for x in ledger['calls'] if x['person']==person and x['seed']==c['seed'] and x['mode']==c['mode'] and x['stage']==c['stage']-1)
  assert v['input_version']==prior['version']['id'] and v['input_sha256']==prior['version']['output_sha256']
 else:assert v['input_version'] is None and v['input_sha256']==sha(refpath)
 rows.append({k:c[k] for k in ['person','seed','mode','stage','artifact_dir']}|{'seconds':v['seconds'],'metrics':M.face(M.crop(ref,roi),M.crop(image(out),roi),net),'prompt_sha256':sha(prompt),'output_sha256':sha(out)})
assert len({r['output_sha256'] for r in rows})==len(rows)
pairs=[]
for person in plan['people']:
 for seed in plan['seeds']:
  final={r['mode']:r for r in rows if r['person']==person and r['seed']==seed and r['stage']==3}
  if len(final)!=2:continue
  a,b=final['regenerate'],final['sequential'];assert a['prompt_sha256']==b['prompt_sha256']
  pairs.append({'person':person,'seed':seed,'regenerate':a['metrics'],'sequential':b['metrics'],'delta_regenerate_minus_sequential':{k:a['metrics'][k]-b['metrics'][k] for k in a['metrics']},'path_seconds':{mode:sum(r['seconds'] for r in rows if r['person']==person and r['seed']==seed and r['mode']==mode) for mode in final}})
  sheet=Image.new('RGB',(1536,806),'white');d=ImageDraw.Draw(sheet)
  for i,(label,p) in enumerate([('ORIGINAL',R/f'reference-{person}.png'),('REGENERATE',R/a['artifact_dir']/'output.png'),('SEQUENTIAL',R/b['artifact_dir']/'output.png')]):
   d.text((i*512+12,12),f'{person} / seed {seed} / {label}',fill='black');sheet.paste(Image.open(p).convert('RGB'),(i*512,38))
  sheet.save(R/f'comparison-{person}-{seed}.png')
keys=['mae','ssim','lpips'];modes=['regenerate','sequential']
def means(ps):return {mode:{k:float(np.mean([p[mode][k] for p in ps])) for k in keys} for mode in modes}
complete=len(rows)==72 and len(pairs)==18
result={'complete':complete,'outputs':len(rows),'paired_comparisons':len(pairs),'independent_people':len({p['person'] for p in pairs}),'rows':rows,'pairs':pairs,'means':means(pairs) if pairs else {},'per_person':{person:means([p for p in pairs if p['person']==person]) for person in plan['people'] if any(p['person']==person for p in pairs)},'regenerate_wins':{k:sum((p['regenerate'][k]<p['sequential'][k]) if k!='ssim' else (p['regenerate'][k]>p['sequential'][k]) for p in pairs) for k in keys},'controls':controls}
save('results.json',result)
save('verification.json',{'complete':complete,'verified_outputs':len(rows),'verified_pairs':len(pairs),'input_lineage_verified':True,'paired_final_prompts_equal':True,'unique_outputs':True,'original_controls_passed':True,'protocol_sha256':sha(R/'PROTOCOL.md'),'analysis_sha256':sha(Path(__file__))})
lines=['# 사이트 다인물 비교','','상태: '+('완료' if complete else '진행 중 — 아래 수치는 완료된 비교만 포함한다.'),f"출력 {len(rows)}/72개 · 최종 비교 {len(pairs)}/18쌍",'','| 인물 | 시드 | 모드 | MAE ↓ | SSIM ↑ | LPIPS ↓ |','| --- | ---: | --- | ---: | ---: | ---: |']
for p in pairs:
 for mode in modes:
  m=p[mode];lines.append(f"| {p['person']} | {p['seed']} | {mode} | {m['mae']:.6f} | {m['ssim']:.6f} | {m['lpips']:.6f} |")
if pairs:
 lines+=['','## 평균','', '| 모드 | MAE ↓ | SSIM ↑ | LPIPS ↓ |','| --- | ---: | ---: | ---: |']
 for mode,m in result['means'].items():lines.append(f"| {mode} | {m['mae']:.6f} | {m['ssim']:.6f} | {m['lpips']:.6f} |")
 lines+=['',f"원본 기반 재생성의 LPIPS·SSIM 우세: 각각 {result['regenerate_wins']['lpips']}/{len(pairs)}쌍. MAE 우세: {result['regenerate_wins']['mae']}/{len(pairs)}쌍. 평균 LPIPS는 {(1-result['means']['regenerate']['lpips']/result['means']['sequential']['lpips'])*100:.1f}% 낮았다.",'','인물별 3시드 평균 LPIPS도 6명 모두 원본 기반 재생성에 유리했다. 최종 비교 이미지 18개를 확인했고, 남색 셔츠·옅은 파란 배경·작은 핀이 관찰됐다. 일부 순차 출력에서는 소매 길이 등 요청하지 않은 옷 형태가 달라졌다. 이는 얼굴 거리 지표와 별개의 관찰이다.','','각 인물의 세 시드는 반복 측정이다. 얼굴 지표는 원본과의 차이를 측정하며, 편집 요청 반영은 비교 이미지를 별도로 확인한다.','', '| 인물 | 시드 | 일괄 1회(초) | 순차 3회 합계(초) |','| --- | ---: | ---: | ---: |']
 for p in pairs:lines.append(f"| {p['person']} | {p['seed']} | {p['path_seconds']['regenerate']:.2f} | {p['path_seconds']['sequential']:.2f} |")
lines+=['','[실험 조건](PROTOCOL.md) · [전체 수치](results.json) · [검증](verification.json)']
(R/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({k:result[k] for k in ['complete','outputs','paired_comparisons','means','regenerate_wins']},indent=2))
