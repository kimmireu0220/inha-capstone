"""Integer translation sensitivity; original images and policy remain immutable."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from skimage.color import rgb2gray
from skimage.feature import match_template
from skimage.metrics import structural_similarity
import torch
import lpips

ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
SOURCE=PARENT.parent/'trigger-validation-v1'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
refpath=SOURCE/'P04/reference.png'
ref=np.asarray(Image.open(refpath).convert('RGB'),dtype=np.float32)/255
x0,y0,x1,y1=352,88,672,448
radius=64
template=gaussian_filter(rgb2gray(ref),sigma=3)[y0:y1,x0:x1]
refcrop=ref[y0:y1,x0:x1]
torch.set_num_threads(2)
torch.manual_seed(0)
torch.use_deterministic_algorithms(True)
network=lpips.LPIPS(net='alex',version='0.1',verbose=False).cpu().eval()
def metrics(b):
    def tensor(x): return torch.from_numpy(x.transpose(2,0,1).copy()).unsqueeze(0)*2-1
    with torch.no_grad():
        return dict(mae=float(np.mean(np.abs(refcrop-b))),ssim=float(structural_similarity(refcrop,b,channel_axis=2,data_range=1.,win_size=7,gaussian_weights=False,use_sample_covariance=True)),lpips=float(network(tensor(refcrop),tensor(b)).item()))
def locate(a):
    gray=gaussian_filter(rgb2gray(a),sigma=3)
    score=match_template(gray[y0-radius:y1+radius,x0-radius:x1+radius],template)
    iy,ix=np.unravel_index(np.argmax(score),score.shape)
    dx,dy=int(ix-radius),int(iy-radius)
    return dict(dx=dx,dy=dy,ncc=float(score[iy,ix]),boundary=abs(dx)==radius or abs(dy)==radius),a[y0+dy:y1+dy,x0+dx:x1+dx]
tests=[]
for dx,dy in [(0,0),(24,35),(-31,-20)]:
    a=np.roll(ref,(dy,dx),axis=(0,1))
    found,crop=locate(a)
    assert (found['dx'],found['dy'])==(dx,dy)
    assert np.array_equal(crop,refcrop)
    tests.append(dict(kind='known_translation',expected_dx=dx,expected_dy=dy,found=found,before=metrics(a[y0:y1,x0:x1]),after=metrics(crop)))
a=np.clip(ref+.03,0,1)
found,crop=locate(a)
assert found['dx']==found['dy']==0
assert metrics(crop)['mae']>.02
tests.append(dict(kind='brightness_offset_not_corrected',found=found,after=metrics(crop)))
audit=read(PARENT/'audit.json')
oldcache=read(PARENT/'metric-cache.json')
rows={}
cropdir=ROOT/'crops'
cropdir.mkdir(exist_ok=True)
Image.fromarray(np.rint(refcrop*255).astype('uint8')).save(cropdir/'reference.png')
for path,record in audit['records'].items():
    assert sha(path)==record['sha256']
    a=np.asarray(Image.open(path).convert('RGB'),dtype=np.float32)/255
    found,crop=locate(a)
    fixed=a[y0:y1,x0:x1]
    before=metrics(fixed)
    for k,v in before.items(): assert abs(v-oldcache[record['sha256']][k])<1e-6
    after=metrics(crop)
    ident=record['sha256'][:12]
    for name,arr in [('fixed',fixed),('aligned',crop)]: Image.fromarray(np.rint(arr*255).astype('uint8')).save(cropdir/f'{ident}-{name}.png')
    rows[path]=dict(source_sha256=record['sha256'],**found,before=before,after=after,lpips_drop=before['lpips']-after['lpips'],old_threshold_before=before['lpips']>=.0555075,old_threshold_after=after['lpips']>=.0555075,crop_id=ident)
progress=read(PARENT/'progress.json')
summary={}
for policy,stages in progress['policies'].items():
    selected=[rows[s['final']['path']] for s in stages]
    summary[policy]=dict(mean_fixed_lpips=float(np.mean([r['before']['lpips'] for r in selected])),mean_aligned_lpips=float(np.mean([r['after']['lpips'] for r in selected])),final_fixed_lpips=selected[-1]['before']['lpips'],final_aligned_lpips=selected[-1]['after']['lpips'],old_threshold_count_before=sum(r['old_threshold_before'] for r in selected),old_threshold_count_after=sum(r['old_threshold_after'] for r in selected),stage_rows=selected)
save(ROOT/'results.json',dict(method='integer_translation_ncc_sigma3_radius64',reference_sha256=sha(refpath),script_sha256=sha(__file__),protocol_sha256=sha(ROOT/'PROTOCOL.md'),tests=tests,unique_images=len(rows),boundary_hits=sum(r['boundary'] for r in rows.values()),rows=rows,summary=summary,human_evaluation='not_collected',independent_agent_evaluation='not_collected'))
# Scientific comparison panels only: exact measured crops, no restoration assets.
for name,paths in [('finals',[progress['policies'][p][-1]['final']['path'] for p in summary]),('largest-shift',[max(rows,key=lambda p:rows[p]['lpips_drop'])])]:
    canvas=Image.new('RGB',(320*(len(paths)+1),780),'white')
    draw=ImageDraw.Draw(canvas)
    for rowno in range(2): canvas.paste(Image.open(cropdir/'reference.png'),(0,30+390*rowno))
    draw.text((8,8),'Reference',fill='black')
    for i,path in enumerate(paths,1):
        r=rows[path]
        for rowno,kind in enumerate(['fixed','aligned']):
            y=390*rowno
            canvas.paste(Image.open(cropdir/f"{r['crop_id']}-{kind}.png"),(320*i,y+30))
            label=list(summary)[i-1] if name=='finals' else r['crop_id']
            value=r['before' if rowno==0 else 'after']['lpips']
            draw.text((320*i+5,y+8),f'{label} {kind} LPIPS {value:.4f}',fill='black')
    canvas.save(ROOT/f'{name}.png')
lines=['# 위치 보정 전후 진단','', '기존 출력 29장을 정수 평행이동으로 비교했다. 원본·정책·경보 기록은 변경하지 않았다. 새로운 생성 실험이나 피부 열화 분류 정확도 검증이 아니다.','', '| 방식 | 평균 고정 LPIPS | 평균 위치 보정 LPIPS | 최종 고정 LPIPS | 최종 위치 보정 LPIPS | 기존 기준 초과 단계: 전→후 |','|---|---:|---:|---:|---:|---:|']
for p,s in summary.items(): lines.append(f"| {p} | {s['mean_fixed_lpips']:.4f} | {s['mean_aligned_lpips']:.4f} | {s['final_fixed_lpips']:.4f} | {s['final_aligned_lpips']:.4f} | {s['old_threshold_count_before']}→{s['old_threshold_count_after']} |")
lines+=['','0.0555075는 보정 전 기준이다. 보정 후 통과를 정상 판정으로 쓰지 않는다. 위치 추정에는 저주파 구조의 정규화 상관을 쓰고 점수에는 보정 위치의 원래 픽셀을 사용했다. 스케일·회전·색·피부 텍스처는 보정하지 않았다. 점수 차이를 피부 열화의 제거량이나 인과적 기여율로 해석하지 않는다.','',f"알려진 이동 3개 회복 및 밝기 잔여 차이 테스트 통과. 탐색 범위 경계 도달 {sum(r['boundary'] for r in rows.values())}/29장. 이는 구현 확인이며 실제 얼굴 정합의 정답 검증이 아니다.",'','## 최종 얼굴: 위 고정 영역, 아래 이동 영역','',f'![최종 비교]({ROOT}/finals.png)','','## 위치 보정으로 LPIPS가 가장 많이 변한 사례','',f'![위치 민감도]({ROOT}/largest-shift.png)','','사후 선택한 예시이며 전 이미지 결과는 results.json에 보존했다. 이동량과 NCC는 각 이미지 행에 있다. 사람·독립 에이전트 평가는 이번 진단에서 수집하지 않았다.','', '방법: [scikit-image normalized cross-correlation](https://scikit-image.org/docs/stable/auto_examples/features_detection/plot_template.html).']
lines+=['','## 관찰과 결론','','- 고정 간격 방식 5단계의 배경 편집 결과에서 추정 이동량은 오른쪽 21·아래 39픽셀이었다. LPIPS가 0.5144에서 0.1740으로 감소했다. 기존 경보에는 위치 민감도가 크게 반영된 사례가 있다.','- 최종 순차 결과는 이동 보정 뒤에도 LPIPS 0.3044이고, 실행 담당자의 비블라인드 육안 확인에서도 넓은 얼굴 영역에 강한 인위적 무늬가 보였다. 위치 변화만으로 설명되지는 않는다.','- 같은 육안 확인에서 최종 고정 간격 결과에는 상대적으로 약한 잔여 피부 무늬가, 감지 결과에는 그보다 덜 두드러진 무늬가 보였다. 이는 연구자가 방법을 아는 상태의 3개 최종 crop 관찰이며 독립 평가 점수나 사람 정답으로 쓰지 않는다. 크기·조명·형상 변화도 여전히 남는다.','- 최종 고정 간격/감지 LPIPS의 순서는 보정 전 0.2035/0.2213에서 보정 후 0.2069/0.1844로 뒤집혔다. 이전의 최종 점수 우열은 전처리에 민감하므로 지각 품질의 확정 순위로 쓰면 안 된다.','- 고정 간격·감지 방식 모두 기존 기준을 넘는 확정 단계 수는 보정 전후 7개로 같았다. 위치 보정만으로 모든 경보가 없어지지는 않았다. 이것을 피부 열화 감지 정확도로 해석하지 않는다.','- 이 ROI에는 얼굴 피부 외에 머리·목·주변 배경도 포함된다. 보정 후 잔여값도 피부 전용 지표가 아니다. 새로운 피부 열화 감지기를 완성한 것이 아니라 기존 지표의 위치 민감도를 확인한 단계다.','- 다음 검증은 방법·지표를 숨기고 같은 얼굴 자료에서 피부 인위성과 위치·형상 차이를 별개로 평가하는 것이다. 그 뒤 피부 내부 영역 또는 정합 방식을 검토하고, 별도 데이터에서 임계값을 정해야 한다. 이번 출력으로 기준을 맞춘 뒤 같은 출력에서 정확도를 주장하지 않는다.']
(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(summary={p:{k:v for k,v in s.items() if k!='stage_rows'} for p,s in summary.items()},boundary_hits=sum(r['boundary'] for r in rows.values()),largest_drop=max(rows.items(),key=lambda item:item[1]['lpips_drop'])),ensure_ascii=False))
