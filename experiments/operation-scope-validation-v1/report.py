"""Verify both model runs, replay frozen reducers, and report every method."""
import hashlib
import json
from pathlib import Path
import run

ROOT=Path(__file__).resolve().parent
LABELS={'baseline_restore':'기준 방법','keep_remove':'기존 유지·삭제',
    'normalized_atomic':'기존 정규화','isolated_keep_remove':'항목별 적용',
    'normalized_isolated':'기존 정규화+항목별 적용',
    'expanded_normalization':'개선 정규화','json_first_only':'JSON 최초 응답',
    'json_review_then_first':'JSON 재검토 우선'}
MODELS={'qwen3':'Qwen3-4B','llama32':'Llama-3.2-3B'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    frozen=json.loads((ROOT/'frozen.json').read_text())
    for p,digest in frozen['sha256'].items():assert sha(run.REPO/p)==digest,p
    data=json.loads((ROOT/'benchmark.json').read_text());histories=data['histories']
    assert len(histories)==8 and sum(map(len,histories.values()))==32
    assert len({r['request'] for rows in histories.values() for r in rows})==32
    all_methods={};groups={};failures={}
    for model,info in frozen['models'].items():
        records=json.loads((ROOT/f'transcripts-{model}.json').read_text())
        assert set(records)=={f'{name}-{i}' for name in histories for i in range(1,5)}
        for name,rows in histories.items():
            for i,item in enumerate(rows,1):
                r=records[f'{name}-{i}'];assert r['request']==item['request']
                assert r['second_user']==item['request']+'\nProposed patch: '+r['first']+'\nAudit this patch against the request. Correct errors; output a flat JSON patch only.'
        methods=run.score(histories,records)
        assert json.loads((ROOT/f'results-{model}.json').read_text())==dict(complete=True,model=info,actual_model_calls=64,methods=methods)
        all_methods[model]=methods;groups[model]={};failures[model]=[]
        for method,result in methods.items():
            groups[model][method]={}
            for group in sorted(set(data['groups'].values())):
                rows=[r for r in result['rows'] if data['groups'][r['dialogue']]==group]
                groups[model][method][group]=dict(exact=sum(r['exact'] for r in rows),requests=len(rows))
        for row in methods['expanded_normalization']['rows']:
            if row['exact']:continue
            r=records[f"{row['dialogue']}-{row['turn']}"]
            failures[model].append(dict(dialogue=row['dialogue'],request_number=row['turn'],request=r['request'],
                first=r['first'],second=r['second'],
                differences={k:dict(expected=row['expected'][k],observed=v) for k,v in row['observed'].items() if v!=row['expected'][k]}))
    summary=dict(complete=True,actual_model_calls=128,requests_per_model=32,dialogues=8,
        distinct_request_texts=32,models=frozen['models'],groups=groups,failures=failures,
        metrics={model:{m:{k:v for k,v in result.items() if k!='rows'} for m,result in methods.items()} for model,methods in all_methods.items()})
    run.core.source.save(ROOT/'summary.json',summary)
    lines=['# 두 모델에서의 복원 표현 처리 검증','',
        '같은 합성 영어 대화 8개, 요청 32개를 두 모델에 각각 적용했다. 문장 32개는 모두 서로 다르다. 모델별 호출은 64회이며 총 128회다. 앞선 개발 자료와 요청이 겹치지 않는다. 모든 방법은 각 모델이 반환한 같은 응답을 사용했다.','',
        '| 방법 | Qwen3-4B | Llama-3.2-3B |','| --- | --- | --- |']
    for method,label in LABELS.items():
        lines.append('| '+' | '.join([label]+[f"{all_methods[m][method]['exact_turns']}/32" for m in MODELS])+' |')
    lines+=['','## 항목별 일치와 최종 상태','',
        '| 모델 | 방법 | 항목별 일치 | 최종 상태 일치 | 추가 오류 수 |',
        '| --- | --- | --- | --- | --- |']
    for model,label in MODELS.items():
        for method in LABELS:
            r=all_methods[model][method]
            lines.append(f"| {label} | {LABELS[method]} | {r['correct_slots']}/192 | {r['exact_final_dialogues']}/8 | {r['new_errors_vs_baseline']} |")
    lines+=['','추가 오류 수는 기준 방법이 맞았지만 해당 방법이 틀린 요청 수다. JSON 최초 응답은 첫 응답만 사용하고, 나머지는 추출·재검토 응답을 사용한다.','',
        '## 요청 유형별 전체 상태','',
        '| 유형 | Qwen 기준 | Qwen 기존 정규화 | Qwen 개선 | Llama 기준 | Llama 기존 정규화 | Llama 개선 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for group in sorted(set(data['groups'].values())):
        values=[f"{groups[m][method][group]['exact']}/8" for m in MODELS for method in ['baseline_restore','normalized_atomic','expanded_normalization']]
        lines.append('| '+' | '.join([group]+values)+' |')
    lines+=['','## 개선 방법의 오류 사례','']
    for model,label in MODELS.items():
        lines.append('### '+label);lines.append('')
        if not failures[model]:lines.append('모든 요청의 전체 상태가 정답과 일치했다.')
        for r in failures[model]:
            lines.append(f"- {r['dialogue']} 요청 {r['request_number']}: {json.dumps(r['differences'],ensure_ascii=False)}")
        lines.append('')
    lines+=['## 실험 구성','',
        '앞선 48개 요청은 개선에 사용한 개발 자료이며 그 재계산은 operation-scope-v2에 기록했다. 본 검증의 코드·요청·정답·모델 배포 버전을 추론 전에 고정했다. 두 모델의 결과는 같은 요청에 대한 대응 비교이며 모델별 분모 32개를 사용한다. 상태를 정답과 자동 대조하였다. 모델 가중치는 저장소에 포함하지 않는다.',
        '', 'Llama 실행 모델: https://huggingface.co/mlx-community/Llama-3.2-3B-Instruct-4bit',
        '원 모델 설명: https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct','']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines))
    names=['run.py','report.py','test_design.py','benchmark.json','models.json','PROTOCOL.md','frozen.json','summary.json','RESULTS.md']
    names += [f'{kind}-{model}.json' for kind in ['transcripts','results'] for model in MODELS]
    run.core.source.save(ROOT/'verification.json',dict(passed=True,actual_model_calls=128,requests_per_model=32,
        sha256={n:sha(ROOT/n) for n in names}))
    print('\n'.join(lines[:15]))

if __name__=='__main__':main()
