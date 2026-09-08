"""Verify policy chains and export a descriptive report, not significance tests."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import shutil
import numpy as np
from PIL import Image
import torch
import lpips

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'trigger-validation-v1'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
data=read(ROOT/'progress.json')
assert data['complete'] and read(ROOT/'pending.json')==[]
steps=[x for x in read(SOURCE/'calls.json') if x['person']=='P04']
prefix=read(SOURCE/'rebase-template.json')['prefix']
ref=SOURCE/'P04/reference.png'
records={}
summary={}
for policy,rows in data['policies'].items():
    assert len(rows)==10
    prev=str(ref)
    for stage,row in enumerate(rows,1):
        assert row['stage']==stage and row['input']==prev and row['state']==steps[stage-1]['state']
        raw=read(Path(row['raw']['record']))
        assert raw['input']==prev and raw['prompt']==steps[stage-1]['prompt']
        expected=(policy=='fixed3' and stage%3==0) or (policy=='triggered' and row['before']['lpips']>=.0555075)
        assert row['rebased']==expected
        if expected:
            final=read(Path(row['final']['record']))
            assert final['input']==str(ref)
            assert final['prompt']==prefix+'\n'.join('- '+v for v in row['state'].values())
            decision=read(ROOT/f'{policy}-stage-{stage}-decision.json')
            assert decision['raw']==row['raw'] and decision['metrics']==row['before']
            # A shared earlier rebase may predate this policy's decision.
        else: assert row['raw']==row['final']
        for role in ['raw','final']:
            path=Path(row[role]['path'])
            recordpath=Path(row[role]['record'])
            call=read(recordpath)
            assert call['output']==str(path) and call['attempt']==1
            assert sha(path)==sha(call['source'])
            assert Image.open(path).size==(1024,1536)
            if 'input_sha256' in call: assert call['input_sha256']==sha(call['input'])
            records[str(path)]=dict(sha256=sha(path),input=call['input'],input_sha256=sha(call['input']),record=str(recordpath),record_sha256=sha(recordpath))
        prev=row['final']['path']
    summary[policy]={**data['summary'][policy],**{f'mean_{k}':float(np.mean([r['after'][k] for r in rows])) for k in ['mae','ssim']},'final_metrics':rows[-1]['after']}
out=ROOT/'finals'
out.mkdir(exist_ok=True)
shutil.copy2(ref,out/'reference.png')
for policy,rows in data['policies'].items(): shutil.copy2(rows[-1]['final']['path'],out/f'{policy}.png')
weights={'alexnet':str(Path(torch.hub.get_dir())/'checkpoints/alexnet-owt-7be5be79.pth'),'lpips':str(Path(lpips.__file__).parent/'weights/v0.1/alex.pth')}
audit=dict(checked_at=datetime.now(timezone.utc).isoformat(),all_checks_passed=True,person='P04',unique_portraits=1,policy_rows=30,unique_used_outputs=len(records),new_actual_calls=data['new_calls'],records=records,source_files={str(p):sha(p) for p in [SOURCE/'calls.json',SOURCE/'config.json',SOURCE/'rebase-template.json',ROOT/'PROTOCOL.md',ROOT/'run.py',ROOT/'report.py']},weight_sha256={k:sha(p) for k,p in weights.items()},human_evaluation='not_collected',independent_agent_evaluation='not_collected')
save(ROOT/'audit.json',audit)
save(ROOT/'summary.json',summary)
lines=['# 재생성 정책 예비 비교 결과','', 'P04 한 인물의 동일한 10단계 요구에 대해 재생성 뒤에도 편집을 이어갔다. 기존 순차 경로와 동일 호출 결과를 재사용한 탐색적 비교이며 새 인물의 독립 검증이 아니다. 신규 내장 이미지 생성 호출 18회, 기존 출력 11장을 재사용했다. 모델 버전·시드는 노출되지 않는다.','', '| 방식 | 재생성 단계 | 논리적 총 호출 | 평균 LPIPS ↓ | 최종 LPIPS ↓ | 평균 MAE ↓ | 평균 SSIM ↑ | 확정 출력 경보 단계 수 |','|---|---|---:|---:|---:|---:|---:|---:|']
labels={'sequential':'순차 유지','fixed3':'3단계마다 재생성','triggered':'경보 시 재생성'}
for p,s in summary.items(): lines.append(f"| {labels[p]} | {', '.join(map(str,s['rebase_stages'])) or '없음'} | {s['logical_calls_completed']} | {s['mean_lpips']:.4f} | {s['final_lpips']:.4f} | {s['mean_mae']:.4f} | {s['mean_ssim']:.4f} | {s['alarm_stages']}/10 |")
lines+=['','평균은 각 단계 개입이 끝난 확정 출력 10개의 산술평균이다. 총 호출은 정책별 순차 10회+재생성 횟수이며, 공유한 이미지도 각각 그 정책의 호출로 센다. 실제 신규 호출 비용과 동일하지 않다. 지표 계산·대기 시간이나 API 금액은 포함하지 않는다.','', '## 해석','', '- 감지 방식의 평균 LPIPS는 낮았으나 재생성이 8회 발생해 고정 간격 3회보다 많았다. 비용 절감은 관찰되지 않았다.','- 최종 LPIPS는 고정 간격 0.2035, 감지 0.2213으로 감지 방식이 더 낮지 않았다. 두 방식 모두 최종 경보가 남았다.','- 원본과 비교하는 고정 좌표 지표에는 피부뿐 아니라 얼굴 위치·크기·조명 변화가 반영된다. 실행 담당자의 비블라인드 육안 확인에서 배경 변경과 함께 인물 위치가 달라진 출력이 관찰됐다. 점수 증가를 피부 열화의 크기로 단정하지 않는다.','- 감지 방식은 3단계부터 사실상 매 단계 재생성으로 작동했다. 현재 지표·임계값이 필요한 개입만 골라준다는 근거는 확보되지 않았다.','- 재생성 직후 점수가 낮아져도 다음 편집에서 다시 상승할 수 있다. 재생성 1회 비교의 개선만으로 지속적인 품질 유지나 정책 효율을 주장할 수 없다.','- LPIPS로 개입을 선택하고 LPIPS로 평가하므로 평균 점수 개선만으로 감지기의 우수성을 입증할 수 없다. 모든 요구 충족, 자연스러움, 사용 가능 여부에 대한 별도 사람·독립 에이전트 평가는 이번 실험에서 수집하지 않았다. 이전 평가를 이번 출력의 평가로 옮겨 쓰지 않는다.','', '## 단계별 확정 출력 LPIPS','', '| 단계 | 순차 | 고정 간격 | 감지 |','|---|---:|---:|---:|']
for i in range(10): lines.append('| '+str(i+1)+' | '+' | '.join(f"{data['policies'][p][i]['after']['lpips']:.4f}" for p in labels)+' |')
lines+=['','## 최종 이미지','']
for p in labels: lines += [f'### {labels[p]}','',f'![{labels[p]}]({out/p}.png)','']
lines+=['## 다음 판단에 필요한 것','','새 이미지를 더 늘리기 전에, 이번 경보가 실제 피부 인위성인지 위치 변화인지 구분하는 동일 이미지의 평가가 필요하다. 이후 위치 보정 또는 변화 유형 분리를 검토하되, 현재 결과와 임계값은 그대로 남기고 별도 실험으로 검증한다.','', '설계: PROTOCOL.md. 입력 연결·실제 프롬프트: generated/*.call.json 및 progress.json. 검증: audit.json. 최종 프롬프트는 calls.json의 10단계 current state와 동일하며 재생성은 rebase-template.json prefix에 그 상태만 열거했다.']
(ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(summary=summary,audit_passed=True,unique_used_outputs=len(records),new_calls=data['new_calls']),ensure_ascii=False))
