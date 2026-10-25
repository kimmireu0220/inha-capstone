"""Recompute every result from the frozen requests and recorded responses."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import run

ROOT=Path(__file__).resolve().parent
LABELS={'baseline_restore':'기준 방법','keep_remove':'기존 유지·삭제',
        'normalized_atomic':'구절 정규화','isolated_keep_remove':'항목별 적용',
        'normalized_isolated':'정규화+항목별 적용','json_first_only':'JSON 최초 응답',
        'json_review_then_first':'JSON 재검토 우선'}
GROUPS={'recombined':'기존 어휘의 새 조합','unseen':'규칙에 없는 표현','revision':'앞 지시의 수정'}

def main():
    frozen=json.loads((ROOT/'frozen.json').read_text())
    for p,digest in frozen['sha256'].items():
        assert hashlib.sha256((run.REPO/p).read_bytes()).hexdigest()==digest,p
    histories=run.benchmark()
    assert frozen['histories']==histories
    records=json.loads((ROOT/'transcripts.json').read_text())
    assert set(records)=={f'{name}-{i}' for name in histories for i in range(1,5)}
    for name,requests in histories.items():
        for i,item in enumerate(requests,1):
            r=records[f'{name}-{i}']
            assert r['request']==item['request']
            assert r['second_user']==item['request']+'\nProposed patch: '+r['first']+'\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
    methods=run.core.score(histories,records)
    methods.update({'json_'+k:v for k,v in run.plain.score(histories,records).items()})
    assert json.loads((ROOT/'results.json').read_text())==dict(complete=True,actual_model_calls=96,methods=methods)
    groups={}
    for m,data in methods.items():
        groups[m]={}
        for group in GROUPS:
            rows=[r for r in data['rows'] if r['dialogue'].endswith('__'+group)]
            baseline=[r for r in methods['baseline_restore']['rows'] if r['dialogue'].endswith('__'+group)]
            groups[m][group]=dict(exact=sum(r['exact'] for r in rows),requests=len(rows),
                target_exact=sum(r['exact'] for r in rows if r['turn'] in [2,3]),target_requests=8,
                correct_slots=sum(r['correct_slots'] for r in rows),slots=96,
                final_exact=sum(r['exact'] for r in rows if r['turn']==4),dialogues=4,
                new_errors=sum(a['exact'] and not b['exact'] for a,b in zip(baseline,rows,strict=True)))
    texts=Counter(r['request'] for r in records.values())
    summary=dict(complete=True,actual_model_calls=96,dialogues=12,requests=48,
        distinct_request_texts=len(texts),goal_configurations=4,groups=groups,
        repeated_texts={t:n for t,n in texts.items() if n>1})
    run.core.source.save(ROOT/'summary.json',summary)
    lines=['# 표현과 지시 순서를 바꾼 추가 검증','',
        f'구현을 고정한 상태에서 대화 12개, 요청 48개를 처리했다. 실제 모델 호출은 96회이며 서로 다른 요청 문장은 {len(texts)}개다. 네 가지 편집 목표를 세 표현 유형으로 요청했다. 같은 초기 설정과 후속 요청이 반복된다. 연구자가 구성한 합성 영어 대화다.','',
        '| 방법 | 전체 상태 일치 | 항목별 일치 | 최종 상태 일치 | 추가 오류 수 |',
        '| --- | --- | --- | --- | --- |']
    for m,label in LABELS.items():
        d=methods[m];new=sum(g['new_errors'] for g in groups[m].values())
        lines.append(f"| {label} | {d['exact_turns']}/48 | {d['correct_slots']}/288 | {d['exact_final_dialogues']}/12 | {new} |")
    lines+=['','추가 오류 수는 기준 방법이 맞았지만 해당 방법이 틀린 요청 수다. JSON 최초 응답 조건은 저장한 첫 응답만 사용한다. 나머지 방법은 추출·재검토 응답을 사용한다.',
        '', '## 표현을 바꾼 두 번째와 세 번째 요청','',
        '| 표현 유형 | 기준 방법 | 기존 유지·삭제 | 구절 정규화 | JSON 최초 응답 | JSON 재검토 우선 |',
        '| --- | --- | --- | --- | --- | --- |']
    for group,label in GROUPS.items():
        lines.append('| '+' | '.join([label]+[f"{groups[m][group]['target_exact']}/8" for m in ['baseline_restore','keep_remove','normalized_atomic','json_first_only','json_review_then_first']])+' |')
    lines+=['','## 오류 사례','']
    for row in methods['normalized_atomic']['rows']:
        if row['exact']: continue
        diff={k:dict(expected=row['expected'][k],observed=v) for k,v in row['observed'].items() if v!=row['expected'][k]}
        lines.append(f"- {row['dialogue']} 요청 {row['turn']}: {json.dumps(diff,ensure_ascii=False)}")
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    names=['run.py','report.py','test_design.py','PROTOCOL.md','frozen.json','transcripts.json','results.json','summary.json','RESULTS.md']
    run.core.source.save(ROOT/'verification.json',dict(passed=True,requests=48,actual_model_calls=96,
        sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}))
    print('\n'.join(lines[:23]))

if __name__=='__main__':main()
