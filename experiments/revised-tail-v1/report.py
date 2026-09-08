"""Audit and summarize current, revised trajectories without importing ratings."""
import json
import math
from pathlib import Path
from PIL import Image
import run as scheduler

ROOT=scheduler.ROOT
read=scheduler.read
sha=scheduler.sha
save=scheduler.save
data=read(ROOT/'progress.json')
assert data['complete'] and read(ROOT/'pending.json')==[]
assert data['human_evaluation']==data['independent_agent_evaluation']=='not_collected'
records=[read(p) for p in sorted((ROOT/'generated').glob('*.call.json'))]
assert len(records)==len(list((ROOT/'generated').glob('*.png')))
for r in records:
    assert r['attempt']==1 and 'pocket' not in r['prompt'].lower()
    assert sha(r['input'])==r['input_sha256']
    assert sha(r['output'])==r['output_sha256']==sha(r['source'])
    with Image.open(r['output']) as im: assert im.size==(1024,1536)

curves=[]
summary=[]
lines=['# 교체 실험 결과', '', '9단계: 아이보리 셔츠 → 버건디 셔츠. 10단계: 사무실 → 나무 책장 도서관.', '', '기존 1~8단계 재사용. 새 9~10단계 사람·독립 에이전트 평가는 미수집이다. 지표는 원본 얼굴과의 차이이며 지각적 열화의 정답이 아니다.', '', '## 최종 출력 지표', '', '| 경로 | MAE ↓ | SSIM ↑ | LPIPS ↓ |', '|---|---:|---:|---:|']
gallery=['# 교체 결과 이미지', '', '방법명과 단계가 공개된 확인용 목록이며 블라인드 평가가 아니다.', '']
for b in data['branches']:
    scheduler.metrics.REF=Path(b['reference']); scheduler.metrics.ROI=b['roi']
    assert [r['stage'] for r in b['rows']]==[9,10]
    assert b['rows'][0]['input']==b['initial']
    assert b['rows'][1]['input']==b['rows'][0]['final']
    files=b['prefix_files']+[r['final'] for r in b['rows']]
    values=[scheduler.metrics.metric(p) for p in files]
    for stage,(p,m) in enumerate(zip(files,values),1):
        assert all(math.isfinite(v) for v in m.values())
        curves.append(dict(branch=b['name'],stage=stage,path=p,sha256=sha(p),metrics=m,source='reused_prefix' if stage<=8 else 'revised_tail'))
    rebases=b.get('prefix_rebases',[])+[r['stage'] for r in b['rows'] if r['rebased']]
    row=dict(branch=b['name'],final=values[-1],mean={k:sum(m[k] for m in values)/10 for k in values[0]},alarm_stages=sum(m['lpips']>=.0555075 for m in values),rebase_stages=rebases,logical_calls=10+len(rebases))
    summary.append(row)
    m=values[-1]
    lines.append(f"| {b['name']} | {m['mae']:.6f} | {m['ssim']:.6f} | {m['lpips']:.6f} |")
    gallery += [f"## {b['name']}", '', f"[원본]({b['reference']}) · [8단계]({b['initial']})", '', '| 9단계 확정 출력 | 10단계 확정 출력 |', '|---|---|',f"| ![9단계]({b['rows'][0]['final']}) | ![10단계]({b['rows'][1]['final']}) |", '']
lines += ['', '## P04 정책 비교', '', '| 정책 | 평균 LPIPS ↓ | 최종 LPIPS ↓ | 재생성 횟수 | 논리 호출 수 |', '|---|---:|---:|---:|---:|']
for s in summary:
    if s['branch'] in ('P04','P04-fixed3','P04-triggered'):
        lines.append(f"| {s['branch']} | {s['mean']['lpips']:.6f} | {s['final']['lpips']:.6f} | {len(s['rebase_stages'])} | {s['logical_calls']} |")
lines += ['',f"신규 실제 생성: {len(records)}장. 순차 7경로의 9~10단계 14장과 정책 비교를 위한 추가 생성이다. 공유 결과는 별도 반복 표본으로 세지 않는다.", '', '## 해석 제한', '', '- 요청 오류 관찰 후 항목을 교체한 탐색적 수정이며 독립 본 실험이 아니다.', '- 기존 9~10단계와 이를 포함한 전체 요약·평가를 새 결과에 합치지 않는다.', '- 고정 얼굴 영역은 위치·조명 변화에도 반응한다. 재생성 정책을 선택하는 LPIPS만으로 정책 우월성을 확정하지 않는다.', '- 피부/정렬 진단의 기존 9~10단계 수치는 폐기 대상이다. 새 결과의 해당 진단은 아직 수행하지 않았다.', '- 사람 평가와 독립 에이전트 평가를 새로 수집하기 전에는 요구 전체 충족률·사용 가능률을 주장하지 않는다.', '']
save(ROOT/'curves.json',curves)
save(ROOT/'summary.json',summary)
(ROOT/'RESULTS.md').write_text('\n'.join(lines))
(ROOT/'GALLERY.md').write_text('\n'.join(gallery))
save(ROOT/'audit.json',dict(passed=True,new_images=len(records),branches=len(summary),sequential_branches=7,identities=6,current_policy_stage_rows=len(curves),preserved_prefix_hashes_verified=True,source_copies_verified=True,no_pocket_in_new_prompts=True,new_ratings_imported=False,scripts={str(p):sha(p) for p in [ROOT/'run.py',ROOT/'report.py',ROOT/'PROTOCOL.md']}))
print(json.dumps(dict(audit='passed',new_images=len(records),summary=summary),ensure_ascii=False))
