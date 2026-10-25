"""Post-hoc replay and constructed code checks; no model inference."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value
run=module('development_scope_run',ROOT.parent/'operation-scope-validation-v1/run.py')
checks=module('development_scope_checks',ROOT/'test_method.py')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    source=ROOT.parent/'instruction-transfer-v1'
    histories=json.loads((source/'frozen.json').read_text())['histories']
    records=json.loads((source/'transcripts.json').read_text())
    result=dict(posthoc_development=True,additional_model_calls=0,requests=48,
        methods=run.score(histories,records),
        source_sha256={str(p.relative_to(REPO)):sha(p) for p in [source/'frozen.json',source/'transcripts.json',ROOT/'method.py']})
    run.core.source.save(ROOT/'development-replay.json',result)
    groups={};failures=[]
    for c in [*checks.cases(),*checks.new_cases()]:
        group=c.get('group','new_restore_keep')
        groups.setdefault(group,dict(cases=0,passed=0));groups[group]['cases']+=1
        prior=dict(c['prior']);raw=json.dumps(c['patch'])
        observed,_=run.improved.update(prior,c['request'],[raw,raw])
        if observed==dict(c['prior'],**c['updates']) and prior==c['prior']:
            groups[group]['passed']+=1
        else:failures.append(dict(request=c['request'],prior=c['prior'],observed=observed,expected=dict(c['prior'],**c['updates'])))
    audit=dict(passed=not failures,actual_model_calls=0,groups=groups,failures=failures,
        source_sha256={str(p.relative_to(REPO)):sha(p) for p in [ROOT/'method.py',ROOT/'test_method.py',REPO/'scripts/audit_clause_invariants.py']})
    run.core.source.save(ROOT/'invariant-audit.json',audit)
    assert audit['passed'],failures[:2]
    baseline=result['methods']['baseline_restore']['exact_turns']
    previous=result['methods']['normalized_atomic']['exact_turns']
    expanded=result['methods']['expanded_normalization']['exact_turns']
    total=sum(g['cases'] for g in groups.values())
    (ROOT/'RESULTS.md').write_text(f'''# 복원 표현 처리의 개발 결과

앞선 추가 검증 48개를 방법 개선에 사용하였다. 같은 모델 응답을 다시 적용한 결과, 전체 상태 일치는 기준 {baseline}/48, 기존 정규화 {previous}/48, 개선 정규화 {expanded}/48이었다. 이는 개발 자료 재계산이며 새 모델 호출은 0회다.

자동 코드 검사는 기존 사례 963개와 새 복원·유지 조합 360개, 총 {total}개에서 예상 상태와 입력 상태 보존을 확인하였다. 실제 모델 응답을 사용한 검증은 별도 폴더 operation-scope-validation-v1에 기록한다.
''')
    names=['method.py','test_method.py','report_development.py','PROTOCOL.md','development-replay.json','invariant-audit.json','RESULTS.md']
    run.core.source.save(ROOT/'verification.json',dict(passed=True,additional_model_calls=0,
        sha256={n:sha(ROOT/n) for n in names}))
    print(dict(baseline=baseline,previous=previous,improved=expanded,requests=48,constructed_checks=total))

if __name__=='__main__':main()
