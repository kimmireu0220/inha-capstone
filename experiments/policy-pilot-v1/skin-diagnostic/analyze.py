"""Post hoc ROI and registration ablations, without fitting a detector."""
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import scipy
import skimage
from scipy.ndimage import gaussian_filter
from skimage.color import rgb2gray
from skimage.feature import match_template
from skimage.metrics import structural_similarity
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
P=ROOT.parent
SOURCE=P.parent/'trigger-validation-v1'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
refpath=SOURCE/'P04/reference.png'
ref=np.asarray(Image.open(refpath).convert('RGB'),dtype=np.float32)/255
regions={'forehead':[452,144,568,178],'cheek_viewer_left':[412,264,448,306],'cheek_viewer_right':[572,264,604,306]}
sigmas=[1,3,6]
templates={s:gaussian_filter(rgb2gray(ref),s)[88:448,352:672] for s in sigmas}
def locate(a,s=3):
    gray=gaussian_filter(rgb2gray(a),s)
    score=match_template(gray[24:512,288:736],templates[s])
    y,x=np.unravel_index(score.argmax(),score.shape)
    return dict(dx=int(x-64),dy=int(y-64),ncc=float(score[y,x]),boundary=x in [0,128] or y in [0,128])
refgray=rgb2gray(ref)
refhp=refgray-gaussian_filter(refgray,2)
def skin(a,shift):
    gray=rgb2gray(a)
    hp=gray-gaussian_filter(gray,2)
    per={}
    for name,(x0,y0,x1,y1) in regions.items():
        dx,dy=shift['dx'],shift['dy']
        old=ref[y0:y1,x0:x1]
        new=a[y0+dy:y1+dy,x0+dx:x1+dx]
        per[name]=dict(mae=float(np.mean(np.abs(old-new))),ssim=float(structural_similarity(old,new,channel_axis=2,data_range=1,win_size=7,gaussian_weights=False,use_sample_covariance=True)),highpass_mae=float(np.mean(np.abs(refhp[y0:y1,x0:x1]-hp[y0+dy:y1+dy,x0+dx:x1+dx]))),pixel_count=(x1-x0)*(y1-y0),ssim_valid_count=(x1-x0-6)*(y1-y0-6))
    avg={k:float(np.average([r[k] for r in per.values()],weights=[r['ssim_valid_count' if k=='ssim' else 'pixel_count'] for r in per.values()])) for k in ['mae','ssim','highpass_mae']}
    return dict(**avg,regions=per)
zero={'dx':0,'dy':0}
controls=[]
def control(name,a,known=None):
    loc=locate(a)
    if known is not None: assert (loc['dx'],loc['dy'])==known
    result=dict(name=name,location=loc,fixed=skin(a,zero),aligned=skin(a,loc))
    controls.append(result)
    return result
identity=control('identity',ref,(0,0))
assert identity['aligned']['mae']==0 and identity['aligned']['highpass_mae']==0 and identity['aligned']['ssim']==1
for dx,dy in [(24,35),(-31,-20)]:
    r=control(f'translation_{dx}_{dy}',np.roll(ref,(dy,dx),axis=(0,1)),(dx,dy))
    assert r['aligned']['mae']==0 and r['aligned']['highpass_mae']<1e-7
for offset in [.03,.10]: control(f'brightness_{offset}',np.clip(ref+offset,0,1))
outside=ref.copy()
outside[:,:280]=[.2,.6,.9]
outside[:,744:]=[.8,.3,.1]
r=control('distant_surround_replacement',outside,(0,0))
assert r['aligned']['mae']==0 and r['aligned']['highpass_mae']==0
support=np.zeros(ref.shape[:2],dtype=np.float32)
for x0,y0,x1,y1 in regions.values(): support[y0-10:y1+10,x0-10:x1+10]=1
support=gaussian_filter(support,2)
yy,xx=np.indices(support.shape)
wave=np.sin(xx*2*np.pi/12)*np.sin(yy*2*np.pi/17)*support
for amplitude in [.01,.03,.06]: control(f'added_skin_wave_{amplitude}',np.clip(ref+amplitude*wave[:,:,None],0,1).astype(np.float32))
for s in [1,2]: control(f'blur_{s}',gaussian_filter(ref,(s,s,0)))
waves=[r['aligned']['highpass_mae'] for r in controls if r['name'].startswith('added_skin_wave')]
assert waves[0]<waves[1]<waves[2]
alignment=read(P/'alignment-diagnostic/results.json')
audit=read(P/'audit.json')
rows={}
for path,record in audit['records'].items():
    assert sha(path)==record['sha256']
    a=np.asarray(Image.open(path).convert('RGB'),dtype=np.float32)/255
    positions={str(s):locate(a,s) for s in sigmas}
    primary=positions['3']
    previous=alignment['rows'][path]
    assert (primary['dx'],primary['dy'])==(previous['dx'],previous['dy'])
    spread=max(max(l[k] for l in positions.values())-min(l[k] for l in positions.values()) for k in ['dx','dy'])
    rows[path]=dict(source_sha256=record['sha256'],locations=positions,shift_spread_px=spread,setting_sensitive=spread>3,fixed=skin(a,zero),aligned={s:skin(a,l) for s,l in positions.items()})
progress=read(P/'progress.json')
summary={}
for policy,stages in progress['policies'].items():
    selected=[rows[s['final']['path']] for s in stages]
    summary[policy]={str(sig):dict(mean={k:float(np.mean([r['aligned'][str(sig)][k] for r in selected])) for k in ['mae','ssim','highpass_mae']},final=selected[-1]['aligned'][str(sig)]) for sig in sigmas}
result=dict(controls=controls,rows=rows,summary=summary,regions=regions,unique_outputs=len(rows),registration_sensitive_count=sum(r['setting_sensitive'] for r in rows.values()),max_shift_spread_px=max(r['shift_spread_px'] for r in rows.values()),tests_passed=True,diagnostic_only=True,human_evaluation='not_collected',independent_agent_evaluation='not_collected',versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,skimage=skimage.__version__),source_hashes={str(p):sha(p) for p in [refpath,ROOT/'PROTOCOL.md',Path(__file__),P/'audit.json',P/'progress.json',P/'alignment-diagnostic/results.json']})
save(ROOT/'results.json',result)
# Measured-area overlays for inspection; no generated image is replaced.
def annotated(a,shift,label):
    image=Image.fromarray(np.rint(np.clip(a,0,1)*255).astype('uint8'))
    draw=ImageDraw.Draw(image)
    for x0,y0,x1,y1 in regions.values(): draw.rectangle((x0+shift['dx'],y0+shift['dy'],x1+shift['dx'],y1+shift['dy']),outline='cyan',width=2)
    crop=image.crop((352+shift['dx'],88+shift['dy'],672+shift['dx'],448+shift['dy']))
    tile=Image.new('RGB',(320,390),'white')
    tile.paste(crop,(0,30))
    ImageDraw.Draw(tile).text((5,8),label,fill='black')
    return tile
ref_tile=annotated(ref,zero,'Reference / fixed sampling regions')
ref_tile.save(ROOT/'reference-regions.png')
items=list(rows.items())
for start in range(0,len(items),7):
    sheet=Image.new('RGB',(1280,780),'white')
    sheet.paste(ref_tile,(0,0))
    for n,(path,r) in enumerate(items[start:start+7],1):
        a=np.asarray(Image.open(path).convert('RGB'),dtype=np.float32)/255
        tile=annotated(a,r['locations']['3'],r['source_sha256'][:12])
        sheet.paste(tile,((n%4)*320,(n//4)*390))
    sheet.save(ROOT/f'areas-{start//7+1}.png')
lines=['# 피부 내부 및 위치 보정 안정성 결과','','기존 P04 고유 출력 29장과 합성 코드 대조군 11개. 새 인물·새 생성·사람 정답·학습한 감지기는 없다. 피부 표본은 원본에서 고정한 이마·양쪽 볼 세 사각형이다.','','## 주 분석: sigma3 위치 보정 후 피부 표본','','| 방식 | 평균 MAE ↓ | 평균 SSIM ↑ | 평균 고주파 잔차 오차 ↓ | 최종 MAE ↓ | 최종 SSIM ↑ | 최종 고주파 잔차 오차 ↓ |','|---|---:|---:|---:|---:|---:|---:|']
for p,s in summary.items():
    m,f=s['3']['mean'],s['3']['final']
    lines.append(f"| {p} | {m['mae']:.5f} | {m['ssim']:.4f} | {m['highpass_mae']:.5f} | {f['mae']:.5f} | {f['ssim']:.4f} | {f['highpass_mae']:.5f} |")
lines+=['','## 정합 설정 민감도','',f"sigma1/3/6 사이 이동 추정의 축별 범위가 3px 초과인 이미지: {result['registration_sensitive_count']}/29. 최대 범위 {result['max_shift_spread_px']}px. 이는 설정 민감도이며 위치 정답과의 오차가 아니다.",'','## 코드 대조군','','| 조건 | 추정 dx,dy | 피부 MAE | 피부 SSIM | 피부 고주파 잔차 오차 |','|---|---|---:|---:|---:|']
for c in controls:
    a,l=c['aligned'],c['location']
    lines.append(f"| {c['name']} | {l['dx']},{l['dy']} | {a['mae']:.6f} | {a['ssim']:.5f} | {a['highpass_mae']:.6f} |")
lines+=['','기본 동일성, 알려진 이동 회복, 먼 주변 교체 불변성, 추가 사인 무늬의 진폭별 고주파 반응 증가 검사를 통과했다. 인공 무늬는 실제 모델의 피부 열화를 대표하는 정답이 아니며, 임계값을 맞추거나 분류 정확도를 계산하지 않았다. 밝기·흐림 반응도 확인했으나 모든 조명·형상 변화를 제거하지는 못한다.','','## 측정 영역','','![원본 영역]('+str(ROOT/'reference-regions.png')+')','','29장 전체 영역 검토 시트는 areas-1.png~areas-5.png, 원시 수치는 results.json에 있다. sigma1/6은 민감도 보조 분석이며 좋은 결과를 보고 주 분석을 바꾸지 않는다.','','## 해석 제한','','세 영역은 피부 전체를 덮지 않으며 자동 피부 분할도 아니다. 변형·회전·스케일 변화는 평행이동만으로 해결되지 않는다. 원본의 정상 주름과 작은 피부 무늬도 위치가 조금 달라지면 차이가 난다. 고주파 잔차 오차를 검증된 열화 감지 점수라고 부르지 않는다. 이번 결과로 인간 판단 일치도·정확도·최적 개입 시점은 계산할 수 없다.','','참고: [SciPy Gaussian filter](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter.html), [scikit-image SSIM](https://scikit-image.org/docs/stable/api/skimage.metrics.html).']
(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(summary={p:{s:{'mean':v['mean'],'final':{k:v['final'][k] for k in ['mae','ssim','highpass_mae']}} for s,v in values.items()} for p,values in summary.items()},sensitive=result['registration_sensitive_count'],max_spread=result['max_shift_spread_px'],tests_passed=True),ensure_ascii=False))
