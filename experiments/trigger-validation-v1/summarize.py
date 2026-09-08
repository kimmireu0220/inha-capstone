"""Audit immutable inputs and build descriptive results and unfilled human forms."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    return json.loads(Path(path).read_text())
def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

jobs = read(ROOT/'calls.json')
original_jobs = {j['stage']: j for j in read(REPO/'experiments/ten-stage-p03-v1/calls.json') if j['run']==1}
config = read(ROOT/'config.json')
assert len(jobs) == 30 and len(original_jobs) == 10
audited = []
def audit_call(path, plan=None):
    call = read(path)
    assert call['attempt'] == 1
    assert timestamp(call['started']) < timestamp(call['completed'])
    if plan:
        for key in ('prompt', 'input', 'output'):
            assert call[key] == plan[key], (path, key)
    assert sha(call['source']) == sha(call['output']), path
    assert Image.open(call['output']).size == (1024,1536)
    audited.append({'record': str(path.relative_to(ROOT)), 'record_sha256': sha(path),
                    'output_sha256': sha(call['output']),
                    'input_sha256': sha(call['input']) if 'input' in call else None})
    return call

summaries = []
for person in ('P04','P05','P06'):
    folder = ROOT/person
    reference = audit_call(folder/'reference.call.json')
    expected_ref = next(r['prompt'] for r in read(ROOT/'reference-prompts.json') if r['id']==person)
    assert reference['prompt'] == expected_ref
    metrics = read(folder/'metrics.json')
    assert metrics['reference_sha256'] == sha(folder/'reference.png')
    assert metrics['config_sha256'] == sha(ROOT/'config.json')
    assert metrics['roi_xyxy'] == config['roi_xyxy'][person]
    assert len(metrics['results']) == 11
    prior_completed = timestamp(reference['completed'])
    for stage in range(1,11):
        job = next(j for j in jobs if j['person']==person and j['stage']==stage)
        assert job['prompt'] == original_jobs[stage]['prompt']
        assert job['state'] == original_jobs[stage]['state']
        assert Path(job['input']) == folder/('reference.png' if stage==1 else f'step-{stage-1}.png')
        call = audit_call(folder/f'step-{stage}.call.json', job)
        assert timestamp(call['started']) >= prior_completed
        prior_completed = timestamp(call['completed'])
        row = next(r for r in metrics['results'] if r['stage']==stage)
        assert row['source_sha256'] == sha(job['output'])
    trigger = read(folder/'trigger.json')
    stage = trigger['stage']
    assert stage == metrics['first_alarm_steps']['lpips'] == trigger['steps_available_at_detection']
    baseline = next(r for r in metrics['results'] if r['stage']==stage)
    assert trigger['baseline_sha256'] == baseline['source_sha256']
    plan = read(folder/'rebase-plan.json')
    assert plan['stage'] == stage and plan['state'] == original_jobs[stage]['state']
    assert plan['input'] == str(folder/'reference.png')
    expected_prompt = read(ROOT/'rebase-template.json')['prefix'] + '\n'.join('- '+s for s in plan['state'].values())
    assert plan['prompt'] == expected_prompt
    rebase_call = audit_call(folder/'rebase.call.json', plan)
    assert timestamp(rebase_call['started']) >= timestamp(trigger['recorded_at'])
    rebase = next(r for r in metrics['results'] if r['file']=='rebase.png')
    assert rebase['source_sha256'] == sha(folder/'rebase.png')
    summaries.append({'person': person, 'stage': stage, 'first_alarms': metrics['first_alarm_steps'],
                      'baseline': baseline, 'rebase': rebase,
                      'delta': {key: rebase[key]-baseline[key] for key in ('mae','ssim','lpips')}})

manifest = read(ROOT/'blind/manifest.json')
ratings = read(ROOT/'blind/ratings.json')
mapping = read(ROOT/'blind-mapping.json')
expected_viewed = set()
assert {g['id'] for g in ratings['groups']} == {g['id'] for g in manifest['groups']}
for group in manifest['groups']:
    mapped = next(m for m in mapping if m['group']==group['id'])
    summary = next(s for s in summaries if s['person']==mapped['person'])
    rating = next(r for r in ratings['groups'] if r['id']==group['id'])
    assert {c['id'] for c in rating['candidates']} == {c['id'] for c in group['candidates']}
    expected_viewed.update(str(Path(group[k]).relative_to(ROOT/'blind')) for k in ('reference_full','reference_crop'))
    by_id = {c['id']: c['method'] for c in mapped['candidates']}
    summary['agent_best'] = [by_id[ident] for ident in rating['best_face_ids']]
    summary['agent_ratings'] = {by_id[c['id']]: c for c in rating['candidates']}
    for c in group['candidates']:
        expected_viewed.update(str(Path(c[k]).relative_to(ROOT/'blind')) for k in ('full','crop'))
        row = next(r for r in rating['candidates'] if r['id']==c['id'])
        assert [r['requirement'] for r in row['requirements']] == group['requirements']
        method = by_id[c['id']]
        name = f"step-{summary['stage']}.png" if method=='baseline' else 'rebase.png'
        assert sha(c['full']) == sha(ROOT/mapped['person']/name)
        assert sha(c['crop']) == sha(ROOT/mapped['person']/'crops'/name)
assert expected_viewed == set(ratings['viewed_files']) and len(expected_viewed)==18
assert len(audited) == 36
save(ROOT/'audit.json', {'passed': True, 'generated_images': 36, 'calls': audited,
                       'input_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [ROOT/'PROTOCOL.md',ROOT/'config.json',ROOT/'calls.json',ROOT/'blind/ratings.json',ROOT/'blind-mapping.json']},
                       'validated_blind_files': 18, 'thresholds_refitted': False, 'human_evaluation_status': 'excluded_incompatible_protocol_2026-09-08'})
save(ROOT/'summary.json', {'schema': 'trigger-validation-summary-v1', 'portraits': 3, 'trajectories': 3,
                          'sequential_outputs': 30, 'rebase_outputs': 3, 'results': summaries, 'human_evaluation_status': 'excluded_incompatible_protocol_2026-09-08'})
lines = ['# 고정 경보 시점 검증 — P04~P06', '',
         '새 원본 3인물·각 10단계 1회, 첫 경보에서 일괄 적용 1회씩을 생성했다. 원본 3장·순차 30장·대응 3장 모두 첫 성공 출력이며 기존 자료와 구분한다. ' + '과거 혼합 사람 평가는 형식 불일치로 제외했다.', '',
         '## 최초 경보', '', '| 인물 | MAE | SSIM | LPIPS (개입 기준) |', '|---|---:|---:|---:|']
for s in summaries:
    a=s['first_alarms']; lines.append(f"| {s['person']} | {a['mae']} | {a['ssim']} | {a['lpips']} |")
lines += ['', 'P01에서 고정한 임계값과 P03의 편집 프롬프트를 그대로 사용했다. 매 단계 저장 직후 계산해 최초 경보를 기록했으며, 이후 단계 결과를 보고 시점을 옮기지 않았다. 재생성 결과는 순차 경로에 투입하지 않았다.', '',
          '## 경보 단계의 동일 요구 비교', '', '| 인물 | 방법 | MAE ↓ | SSIM ↑ | LPIPS ↓ | LPIPS 경보 |', '|---|---|---:|---:|---:|---|']
for s in summaries:
    for key,label in [('baseline','순차 유지'),('rebase','원본 기반 일괄')]:
        r=s[key]; lines.append(f"| {s['person']} | {label} | {r['mae']:.6f} | {r['ssim']:.6f} | {r['lpips']:.6f} | {'있음' if r['alarms']['lpips'] else '없음'} |")
lines += ['', 'MAE는 RGB [0,1] 단위다. 고정 320×360 얼굴 영역을 원본과 비교하며 위치·색상·크기 보정은 하지 않는다. 따라서 지표에는 피부 인위성 외에도 위치·조명 변화가 반영된다.', '',
          '## 독립 에이전트 평가', '', '| 인물 | 요구 충족 | 피부 인위성 순차→일괄 | 얼굴 최선 | 사용 가능 |', '|---|---|---|---|---|']
for s in summaries:
    a=s['agent_ratings']; fulfilled=all(r['rating']=='충족' for v in a.values() for r in v['requirements'])
    usable='·'.join({'baseline':'순차','rebase':'일괄'}[k] for k,v in a.items() if v['usable']=='예') or '둘 다 불가'
    best='·'.join({'baseline':'순차','rebase':'일괄'}[k] for k in s['agent_best'])
    lines.append(f"| {s['person']} | {'두 후보 모두' if fulfilled else '상세 응답 참조'} | {a['baseline']['skin_artifact']}→{a['rebase']['skin_artifact']} | {best} | {usable} |")
lines += ['', '피부 인위성은 0 없음·1 약함·2 뚜렷함·3 심함이다. 에이전트 1회 평가이며 원본·전체 후보·동일 crop 총 18파일을 방법·지표·기존 응답을 가리고 제시했다. 모든 후보에서 장신구 요구는 충족으로 평가했지만 사용 가능 여부는 달랐다. 평가 지시 원문과 근거는 blind/TASK.md·ratings.json·review.md에 남겼다.', '',
          '## 해석', '',
          '세 사례에서 원본 기반 일괄 적용은 MAE·SSIM·LPIPS가 모두 개선됐고 세 지표의 고정 경보가 모두 해제됐다. 에이전트도 세 사례 모두 일괄 적용을 얼굴 상대 최선으로 골랐다. 그러나 P05는 경보가 해제됐는데도 뚜렷한 피부 인위성이 남아 사용 불가로 평가됐다. 경보 해제를 지각적 복원 성공으로 취급할 수 없으며 상대 개선과 사용 가능한 복원을 구분해야 한다.', '',
          '경보 시점 후보에 대한 에이전트 평가는 전체 30단계의 감지 정확도 검증이 아니다. 미경보 단계·정상 대조군의 독립 평가 없이 오탐률·미탐률을 제시하지 않는다. 사람 응답, 장기 후속 편집 효과, 비용 대비 최적 개입 시점은 미검증이다. 같은 순서의 단순 비얼굴 편집 조건에 한정하며 복합 장면으로 일반화하지 않는다.', '',
          '## 기록 검증', '',
          'summarize.py는 36개 호출의 첫 시도·입력 연결·원본 출력 복사 해시·프롬프트 일치·경보 기록 시각·평가 ID를 대조한다. audit.json과 summary.json은 이 검사로 재생성된다. 기존 평가와 임계값은 변경하지 않았다.', '']
(ROOT/'RESULTS.md').write_text('\n'.join(lines))

print(json.dumps({'audit':'passed', 'images':len(audited), 'results':[{'person':s['person'],'stage':s['stage'],'delta':s['delta'],'agent_best':s['agent_best'],'rebase_alarms':s['rebase']['alarms']} for s in summaries]},ensure_ascii=False))
