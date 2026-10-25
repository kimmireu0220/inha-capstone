"""Recompute the new comparison and distinguish measured calls from method requirements."""
import hashlib
import json
from pathlib import Path
import run

ROOT=Path(__file__).resolve().parent
MODELS={'qwen3':'Qwen3-4B','llama32':'Llama-3.2-3B'}
LABELS={'baseline_restore':'기준 방법','keep_remove':'기존 유지·삭제','normalized_atomic':'기존 정규화',
    'isolated_keep_remove':'항목별 적용','normalized_isolated':'기존 정규화+항목별 적용',
    'expanded_normalization':'복원 표현 개선','json_first_only':'JSON 최초 응답',
    'json_review_then_first':'JSON 재검토 우선','eligible_normalization':'추출·재검토+지시 검사',
    'single_extraction_checked':'한 번 추출+지시 검사'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    frozen=json.loads((ROOT/'frozen.json').read_text())
    for p,digest in frozen['sha256'].items():assert sha(run.REPO/p)==digest,p
    h=json.loads((ROOT/'benchmark.json').read_text())['histories']
    results={};failures={};damage={}
    for model,info in frozen['models'].items():
        records=json.loads((ROOT/f'transcripts-{model}.json').read_text())
        assert set(records)=={f'{name}-{i}' for name in h for i in range(1,5)}
        for name,rows in h.items():
            for i,item in enumerate(rows,1):
                r=records[f'{name}-{i}'];assert r['request']==item['request']
                assert r['second_user']==item['request']+'\nProposed patch: '+r['first']+'\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
        methods=run.score(h,records)
        assert json.loads((ROOT/f'results-{model}.json').read_text())==dict(complete=True,model=info,actual_model_calls=24,methods=methods)
        results[model]=methods;failures[model]=[]
        one=methods['single_extraction_checked'];two=methods['eligible_normalization']
        damage[model]=dict(one_correct_two_wrong=sum(a['exact'] and not b['exact'] for a,b in zip(one['rows'],two['rows'],strict=True)),
            two_correct_one_wrong=sum(b['exact'] and not a['exact'] for a,b in zip(one['rows'],two['rows'],strict=True)))
        for r in one['rows']:
            if not r['exact']:failures[model].append(dict(dialogue=r['dialogue'],request_number=r['turn'],differences={k:dict(expected=r['expected'][k],observed=v) for k,v in r['observed'].items() if v!=r['expected'][k]}))
    summary=dict(complete=True,actual_model_calls=48,requests_per_model=12,dialogues=3,distinct_request_texts=12,
        metrics={m:{k:{field:value for field,value in r.items() if field!='rows'} for k,r in d.items()} for m,d in results.items()},
        failures=failures,review_effect=damage)
    run.parent.parent.core.source.save(ROOT/'summary.json',summary)
    lines=['# 한 번 추출한 응답에 지시 검사를 적용한 결과','',
        '새 합성 영어 대화 세 개, 요청 12개를 두 모델에 각각 적용했다. 문장은 모두 서로 다르며 이전 자료와 겹치지 않는다. 모든 비교를 위해 실제 호출은 모델별 24회, 총 48회 수행했다. 한 번 추출 조건은 최초 응답만 사용하므로 요청당 한 번 호출하는 방법이다.','',
        '| 방법 | 요청당 필요한 호출 | Qwen3-4B | Llama-3.2-3B |','| --- | --- | --- | --- |']
    for method,label in LABELS.items():
        calls=results['qwen3'][method]['required_model_calls_per_request']
        lines.append('| '+' | '.join([label,str(calls)]+[f"{results[m][method]['exact_turns']}/12" for m in MODELS])+' |')
    lines+=['','## 한 번 추출과 지시 검사 결합의 상세 점수','',
        '| 모델 | 항목별 일치 | 최종 상태 일치 | 추가 오류 수 |',
        '| --- | --- | --- | --- |']
    for model,label in MODELS.items():
        r=results[model]['single_extraction_checked']
        lines.append(f"| {label} | {r['correct_slots']}/72 | {r['exact_final_dialogues']}/3 | {r['new_errors_vs_baseline']} |")
    lines+=['','추가 오류 수는 기준 방법이 맞았지만 해당 방법이 틀린 요청 수다. 호출 수는 방법 실행에 필요한 모델 호출 횟수이며 처리 시간이나 금액의 측정값과 구분한다.','',
        '## 재검토의 영향','']
    for model,label in MODELS.items():
        d=damage[model];lines.append(f"- {label}: 한 번 추출이 맞고 재검토 결합이 틀린 요청 {d['one_correct_two_wrong']}개, 반대 경우 {d['two_correct_one_wrong']}개.")
    lines+=['','## 한 번 추출 조건의 오류 사례','']
    for model,label in MODELS.items():
        lines.append('### '+label);lines.append('')
        if not failures[model]:lines.append('모든 요청의 전체 상태가 정답과 일치했다.')
        for r in failures[model]:lines.append(f"- {r['dialogue']} 요청 {r['request_number']}: {json.dumps(r['differences'],ensure_ascii=False)}")
        lines.append('')
    (ROOT/'RESULTS.md').write_text('\n'.join(lines))
    names=['run.py','report.py','report_development.py','test_design.py','PROTOCOL.md','benchmark.json','frozen.json','development-replay.json','summary.json','RESULTS.md']
    names += [f'{kind}-{m}.json' for kind in ['transcripts','results'] for m in MODELS]
    run.parent.parent.core.source.save(ROOT/'verification.json',dict(passed=True,requests_per_model=12,actual_model_calls=48,sha256={n:sha(ROOT/n) for n in names}))
    print('\n'.join(lines[:18]))
if __name__=='__main__':main()
