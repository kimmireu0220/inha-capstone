"""Development replay of eligibility guards; no additional model calls."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
run=module('eligibility_development_run',ROOT.parent/'instruction-eligibility-validation-v1/run.py')
checks=module('eligibility_invariant_source',ROOT.parent/'operation-scope-v2/test_method.py')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    source=ROOT.parent/'operation-scope-validation-v1'
    histories=json.loads((source/'benchmark.json').read_text())['histories']
    methods={};paths=[source/'benchmark.json',ROOT/'method.py']
    for model in ['qwen3','llama32']:
        p=source/f'transcripts-{model}.json';records=json.loads(p.read_text())
        assert len(records)==32
        methods[model]=run.score(histories,records);paths.append(p)
    run.parent.core.source.save(ROOT/'development-replay.json',dict(posthoc_development=True,additional_model_calls=0,
        requests_per_model=32,methods=methods,source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths}))
    count=0;failures=[]
    for c in [*checks.cases(),*checks.new_cases()]:
        count+=1;prior=dict(c['prior']);raw=json.dumps(c['patch'])
        actual,_=run.method.update(prior,c['request'],[raw,raw])
        if actual!=dict(c['prior'],**c['updates']) or prior!=c['prior']:
            failures.append(dict(request=c['request'],actual=actual,expected=dict(c['prior'],**c['updates'])))
    audit=dict(passed=not failures,cases=count,actual_model_calls=0,failures=failures,
        source_sha256={str(p.relative_to(REPO)):sha(p) for p in [ROOT/'method.py',ROOT/'test_method.py',ROOT.parent/'operation-scope-v2/test_method.py']})
    run.parent.core.source.save(ROOT/'invariant-audit.json',audit);assert audit['passed'],failures[:2]
    lines=['# 실행 대상 검사의 개발 결과','',
        '앞선 32개 요청을 실행 대상 검사 개발에 사용하였다. 동일한 응답을 다시 적용한 개발 자료 재계산이며 새 모델 호출은 0회다.','',
        '| 모델 | 기준 | 복원 표현 개선 | 실행 대상 검사 결합 |','| --- | --- | --- | --- |']
    for model in methods:
        values=[f"{methods[model][m]['exact_turns']}/32" for m in ['baseline_restore','expanded_normalization','eligible_normalization']]
        lines.append('| '+' | '.join([model]+values)+' |')
    lines+=['',f'최종 방법의 자동 코드 검사 {count}개에서 예상 상태와 입력 상태 보존을 확인하였다. 새 요청 검증은 instruction-eligibility-validation-v1에 기록한다.','']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines))
    names=['method.py','test_method.py','report_development.py','PROTOCOL.md','development-replay.json','invariant-audit.json','RESULTS.md']
    run.parent.core.source.save(ROOT/'verification.json',dict(passed=True,additional_model_calls=0,sha256={n:sha(ROOT/n) for n in names}))
    print('\n'.join(lines))

if __name__=='__main__':main()
