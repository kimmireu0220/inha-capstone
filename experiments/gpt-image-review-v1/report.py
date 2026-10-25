"""Aggregate unchanged GPT agent ratings and compare paired judgments."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inputs = json.loads((ROOT/'blind-inputs.json').read_text())
    mapping = json.loads((ROOT/'blind-mapping.json').read_text())
    prepared = json.loads((REPO/'experiments/prompt-state-image-v1/prepared.json').read_text())['conditions']
    conditions = {c['job']:c for c in prepared}
    previous = json.loads((REPO/'experiments/prompt-state-image-v1/ai-ratings-7b.json').read_text())['ratings']
    source_plan = json.loads((REPO/'experiments/prompt-state-image-v1/evaluation-plan.json').read_text())['items']
    results, indexes, disagreements, previous_disagreements = {}, {}, [], {}
    assert len(inputs) == len(mapping) == 18
    for item in inputs:
        source = Path(mapping[item['id']]['source'])
        key = mapping[item['id']]['evaluation_key']
        assert sha(source) == item['sha256'] == source_plan[key]['sha256']
        assert item['goals'] == source_plan[key]['goals']
    for evaluator in ['a','b']:
        data = json.loads((ROOT/f'ratings-{evaluator}.json').read_text())
        assert data['evaluator'] == 'gpt-6.1-sol' and data['reasoning_effort'] == 'low'
        index = {r['id']:r for r in data['ratings']}
        assert len(data['ratings']) == len(index) == 18 and set(index) == set(mapping)
        indexes[evaluator] = index
        modes = {m:dict(success=0, failure=0, unknown=0, total=0, images=0) for m in ['full_history','unchecked_state','checked_state']}
        previous_disagreements[evaluator] = []
        for ident, row in index.items():
            assert len(row['scores']) == len(row['reasons']) == 6
            assert all(v is None or type(v) is int and v in [0,1] for v in row['scores'])
            assert all(isinstance(v,str) and v.strip() for v in row['reasons'])
            source = Path(mapping[ident]['source'])
            condition = conditions[source.parent.name]
            aggregate = modes[condition['mode']]
            aggregate['images'] += 1
            key = mapping[ident]['evaluation_key']
            for field, (score, old) in enumerate(zip(row['scores'],previous[key]['scores']),1):
                aggregate['total'] += 1
                aggregate['success' if score == 1 else 'failure' if score == 0 else 'unknown'] += 1
                if score != old:
                    previous_disagreements[evaluator].append(dict(id=ident, field=field, gpt=score, qwen7b=old, reason=row['reasons'][field-1]))
        assert all(v['total'] == 36 and v['images'] == 6 for v in modes.values())
        results[evaluator] = modes
    for ident in mapping:
        for i,(a,b) in enumerate(zip(indexes['a'][ident]['scores'],indexes['b'][ident]['scores']),1):
            if a != b:
                disagreements.append(dict(id=ident,field=i,a=a,b=b,reason_a=indexes['a'][ident]['reasons'][i-1],reason_b=indexes['b'][ident]['reasons'][i-1]))
    summary = dict(post_hoc=True,evaluator='gpt-6.1-sol',reasoning_effort='low',images=18,
        goals_per_image=6,raters=2,by_evaluator=results,agreement=dict(equal=108-len(disagreements),total=108),
        disagreements=disagreements,qwen7b_disagreements=previous_disagreements)
    (ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    lines=['# GPT 에이전트 사후 이미지 평가','','동일한 이미지 18장과 목표를 방식명·기존 점수 없이 두 에이전트가 각각 평가하였다. 두 호출 모두 gpt-6.1-sol, low이며 서로 다른 모델 계열의 평가가 아니다.','','| 입력 방식 | 평가 A 충족 | A 판단 불가 | 평가 B 충족 | B 판단 불가 |','| --- | --- | --- | --- | --- |']
    for mode,label in [('full_history','전체 요청 이력'),('unchecked_state','검사 전 현재 조건'),('checked_state','지시 검사 후 현재 조건')]:
        a,b=results['a'][mode],results['b'][mode]
        lines.append(f"| {label} | {a['success']}/36 | {a['unknown']} | {b['success']}/36 | {b['unknown']} |")
    lines+=['',f"평가자 간 항목 점수는 {108-len(disagreements)}/108에서 일치하였다. 불일치 항목과 기존 Qwen2.5-VL-7B 판정과의 차이는 summary.json에 모두 기록하였다. 각 평가자의 원문 점수와 근거를 유지하였다.",'']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines))
    paths=[ROOT/n for n in ['PROTOCOL.md','blind-inputs.json','blind-mapping.json','ratings-a.json','ratings-b.json','report.py','summary.json','RESULTS.md']]
    paths += [REPO/'experiments/prompt-state-image-v1'/n for n in ['prepared.json','evaluation-plan.json','ai-ratings-7b.json']]
    record=dict(passed=True,source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths})
    (ROOT/'verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
