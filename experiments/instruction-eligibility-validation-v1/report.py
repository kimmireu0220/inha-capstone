"""Verify final fresh validation without changing its fixed scoring methods."""
import hashlib
import json
from pathlib import Path
import run

ROOT=Path(__file__).resolve().parent
MODELS={'qwen3':'Qwen3-4B','llama32':'Llama-3.2-3B'}
LABELS={'baseline_restore':'기준 방법','keep_remove':'기존 유지·삭제','normalized_atomic':'기존 정규화',
    'isolated_keep_remove':'항목별 적용','normalized_isolated':'기존 정규화+항목별 적용',
    'expanded_normalization':'복원 표현 개선','json_first_only':'JSON 최초 응답',
    'json_review_then_first':'JSON 재검토 우선','eligible_normalization':'실행 대상 검사 결합'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    frozen=json.loads((ROOT/'frozen.json').read_text())
    for p,d in frozen['sha256'].items():assert sha(run.REPO/p)==d,p
    data=json.loads((ROOT/'benchmark.json').read_text());h=data['histories']
    assert len(h)==4 and sum(map(len,h.values()))==16
    results={};groups={};failures={}
    for model,info in frozen['models'].items():
        records=json.loads((ROOT/f'transcripts-{model}.json').read_text())
        assert set(records)=={f'{name}-{i}' for name in h for i in range(1,5)}
        for name,rows in h.items():
            for i,item in enumerate(rows,1):
                r=records[f'{name}-{i}'];assert r['request']==item['request']
                assert r['second_user']==item['request']+'\nProposed patch: '+r['first']+'\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
        methods=run.score(h,records)
        assert json.loads((ROOT/f'results-{model}.json').read_text())==dict(complete=True,model=info,actual_model_calls=32,methods=methods)
        results[model]=methods;groups[model]={};failures[model]=[]
        for method,result in methods.items():
            groups[model][method]={}
            for group in sorted(set(data['groups'].values())):
                rows=[r for r in result['rows'] if data['groups'][r['dialogue']]==group]
                groups[model][method][group]=dict(exact=sum(r['exact'] for r in rows),requests=len(rows))
        for r in methods['eligible_normalization']['rows']:
            if not r['exact']:
                failures[model].append(dict(dialogue=r['dialogue'],request_number=r['turn'],differences={k:dict(expected=r['expected'][k],observed=v) for k,v in r['observed'].items() if v!=r['expected'][k]}))
    summary=dict(complete=True,actual_model_calls=64,requests_per_model=16,dialogues=4,distinct_request_texts=16,
        models=frozen['models'],groups=groups,failures=failures,
        metrics={model:{m:{k:v for k,v in r.items() if k!='rows'} for m,r in methods.items()} for model,methods in results.items()})
    run.parent.core.source.save(ROOT/'summary.json',summary)
    lines=['# 실행 대상 검사 방법의 새 요청 검증','',
        '개발에 사용한 32개와 겹치지 않는 새 합성 영어 대화 네 개, 요청 16개를 두 모델에 각각 적용하였다. 실제 모델 호출은 모델별 32회, 전체 64회다. 방법과 자료는 추론 전에 고정했다.','',
        '| 방법 | Qwen3-4B | Llama-3.2-3B |','| --- | --- | --- |']
    for method,label in LABELS.items():
        lines.append('| '+' | '.join([label]+[f"{results[m][method]['exact_turns']}/16" for m in MODELS])+' |')
    lines+=['','## 최종 방법의 상세 점수','',
        '| 모델 | 항목별 일치 | 최종 상태 일치 | 추가 오류 수 |',
        '| --- | --- | --- | --- |']
    for model,label in MODELS.items():
        r=results[model]['eligible_normalization']
        lines.append(f"| {label} | {r['correct_slots']}/96 | {r['exact_final_dialogues']}/4 | {r['new_errors_vs_baseline']} |")
    lines+=['','추가 오류 수는 기준이 맞았지만 최종 방법이 틀린 요청 수다.','',
        '## 유형별 결과','',
        '| 유형 | Qwen 기준 | Qwen 복원 표현 개선 | Qwen 최종 | Llama 기준 | Llama 복원 표현 개선 | Llama 최종 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for group in sorted(set(data['groups'].values())):
        values=[f"{groups[m][method][group]['exact']}/8" for m in MODELS for method in ['baseline_restore','expanded_normalization','eligible_normalization']]
        lines.append('| '+' | '.join([group]+values)+' |')
    lines+=['','## 최종 방법의 오류 사례','']
    for model,label in MODELS.items():
        lines.append('### '+label);lines.append('')
        if not failures[model]:lines.append('모든 요청의 전체 상태가 정답과 일치했다.')
        for r in failures[model]:lines.append(f"- {r['dialogue']} 요청 {r['request_number']}: {json.dumps(r['differences'],ensure_ascii=False)}")
        lines.append('')
    (ROOT/'RESULTS.md').write_text('\n'.join(lines))
    names=['run.py','report.py','test_design.py','PROTOCOL.md','benchmark.json','frozen.json','summary.json','RESULTS.md']
    names += [f'{kind}-{m}.json' for kind in ['transcripts','results'] for m in MODELS]
    run.parent.core.source.save(ROOT/'verification.json',dict(passed=True,requests_per_model=16,actual_model_calls=64,sha256={n:sha(ROOT/n) for n in names}))
    print('\n'.join(lines[:16]))

if __name__=='__main__':main()
