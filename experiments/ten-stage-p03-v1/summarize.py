"""Audit recorded calls, compare fixed alarms with independent ratings, and prepare blank human sheets."""
from pathlib import Path
import hashlib
import json
from PIL import Image

EXP = Path(__file__).resolve().parent
ROOT = EXP.parents[1]
def read(p):
    return json.loads(p.read_text())
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

jobs = read(EXP / 'calls.json')
original_jobs = {j['stage']: j for j in read(ROOT / 'experiments/ten-stage-v1/calls.json')}
assert len(jobs) == 20
assert sorted((j['run'], j['stage']) for j in jobs) == [(r,s) for r in [1,2] for s in range(1,11)]
audit = []
for j in jobs + read(EXP / 'interventions/prompts.json')['jobs']:
    output = Path(j['output'])
    log = read(output.with_suffix('.call.json'))
    assert log['prompt'] == j['prompt'] and log['input'] == j['input'] and log['output'] == j['output']
    assert log['attempt'] == 1 and log['status'] == 'success'
    assert Image.open(output).size == (1024,1536)
    assert sha(output) == sha(Path(log['source']))
    if 'method' not in j:
        assert j['prompt'] == original_jobs[j['stage']]['prompt']
        expected = ROOT / 'assets/people/P03.png' if j['stage'] == 1 else EXP / f"run-{j['run']}/step-{j['stage']-1}.png"
        assert Path(j['input']) == expected
    audit.append({'output':str(output.relative_to(ROOT)), 'sha256':sha(output), 'input_sha256':sha(Path(j['input'])), 'first_success':True})
save(EXP / 'audit.json', {'sequential_outputs':20, 'intervention_outputs':6, 'sequential_prompts_exactly_match_P01':True, 'reference_sha256':sha(ROOT/'assets/people/P03.png'), 'outputs':audit})

metrics = read(EXP/'metrics/metrics.json')
mapping = read(EXP/'metrics/blind-mapping.json')['presentation_order']
ratings = read(EXP/'agent-review/ratings.json')['ratings']
by_id = {r['id']:r for r in ratings}
assert len(by_id) == 20 and set(by_id) == {Path(m['file']).stem for m in mapping}
joined = sorted([{**m, **by_id[Path(m['file']).stem]} for m in mapping], key=lambda r:(r['run'],r['step']))
comparisons = {}
for run in [1,2]:
    rows = [r for r in joined if r['run'] == run]
    onset = next((r['step'] for r in rows if r['naturalness'] >= 2), None)
    confusion = {}
    for name in ['mae','ssim','lpips']:
        counts = dict(TP=0,TN=0,FP=0,FN=0,uncertain=0)
        for r in rows:
            if r['uncertain']:
                counts['uncertain'] += 1
                continue
            alarm = next(m for m in metrics['results'] if m['run']==run and m['step']==r['step'])['alarms'][name]
            positive = r['naturalness'] >= 2
            counts['TP' if alarm and positive else 'FP' if alarm else 'FN' if positive else 'TN'] += 1
        confusion[name] = counts
    comparisons[f'run-{run}'] = {'agent_first_clear':onset, 'fixed_first_alarms':metrics['first_alarm_steps'][f'run-{run}'], 'confusion_against_agent_not_human_truth':confusion}
save(EXP/'agent-review/comparison.json', {'rows':joined, 'comparisons':comparisons, 'limitation':'One agent; one identity with two dependent trajectories. No human P03 ratings. Do not report general detector accuracy.'})

human = EXP/'human-review'
human.mkdir(exist_ok=True)
for run in [1,2]:
    lines = [f'# 얼굴 변화 확인 — {run}회차', '', '각 얼굴을 원본과 비교해주세요. 원래 있던 주름과 귀걸이는 제외하고, 새로 생긴 부자연스러운 피부 무늬나 변형을 판단해주세요.', '', '각 단계: 없음 / 약함 / 뚜렷함 / 심함 / 판단 어려움', '']
    for m in sorted([m for m in mapping if m['run']==run],key=lambda m:m['step']):
        lines += [f"## {m['step']}단계", '', '| 원본 | 비교 얼굴 |', '|---|---|', f"| ![원본]({EXP}/metrics/blind-crops/reference.png) | ![비교]({EXP}/metrics/blind-crops/{m['file']}) |", '', '응답: __________', '']
    (human/f'face-run-{run}.md').write_text('\n'.join(lines))
intervention_ratings = EXP/'interventions/agent-review/ratings.json'
if intervention_ratings.exists():
    imap = read(EXP/'interventions/metrics/blind-mapping.json')
    decoded = []
    for group in read(intervention_ratings)['groups']:
        names = {Path(e['file']).stem:e['method'] for e in imap[group['group']]}
        assert set(names) == {r['id'] for r in group['ratings']}
        baseline = next(r for r in group['ratings'] if names[r['id']]=='baseline')
        run = int(group['group'].split('-')[1])
        sequential_rating = next(r for r in joined if r['run']==run and r['step']==2)
        decoded.append({
            'group':group['group'],
            'ratings':[{**r,'method':names[r['id']]} for r in group['ratings']],
            'best_face':[names[i] for i in group['best_face']],
            'usable':[names[i] for i in group['usable']],
            'ranking':[[names[i] for i in tied] for tied in group['ranking']],
            'baseline_naturalness_disagreement':{'sequential_face_agent':sequential_rating['naturalness'], 'intervention_agent':baseline['naturalness']}
        })
    save(EXP/'interventions/agent-review/decoded.json', {'groups':decoded,'note':'Derived only; source judgments unchanged. Different agents and presentation contexts. Not consensus or human truth.'})
for sheet in human.glob('*.md'):
    import re
    for target in re.findall(r'\]\((/[^)]+)\)',sheet.read_text()):
        assert Path(target).is_file(), (sheet,target)
print(json.dumps({'audit':'26 image logs/source bytes and all human-sheet links verified', 'comparisons':comparisons},ensure_ascii=False,indent=2))
