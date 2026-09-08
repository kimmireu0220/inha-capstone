"""Read-only verification of first-output calls and shared branch data."""
import hashlib,json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    g=ROOT/'generation';p=read(g/'progress.json');assert p['collection_complete'] and not p['full_design_complete']
    assert read(g/'pending.json')==[]
    records=[read(f) for f in sorted((g/'generated').glob('*.call.json'))]
    assert len(records)==len(list((g/'generated').glob('*.png')))==25
    assert len({r['id'] for r in records})==25
    failed=[read(f) for f in (g/'failures').glob('*.json')];assert len(failed)==1
    assert failed[0]['stage']==9 and failed[0]['branches']==['P05-once-triggered']
    assert failed[0]['attempt']==1 and failed[0]['retried'] is False
    assert failed[0]['status']=='failed' and failed[0]['output_exists'] is False
    assert not Path(failed[0]['output']).exists()
    assert failed[0]['input_sha256']==sha(failed[0]['input'])
    assert failed[0]['id']==hashlib.sha256((failed[0]['input_sha256']+'\n'+failed[0]['prompt']).encode()).hexdigest()
    lookup={}
    for r in records:
        assert r['input_sha256']==sha(r['input'])
        assert r['output_sha256']==sha(r['output'])
        assert r['id']==hashlib.sha256((r['input_sha256']+'\n'+r['prompt']).encode()).hexdigest()
        assert r['attempt']==1
        assert 'pocket' not in r['prompt'].lower()
        with Image.open(r['output']) as im:assert im.size==(1024,1536)
        lookup[r['output_sha256']]=r
    branches={b['name']:b for b in p['branches']}
    old={b['name']:b for b in read(ROOT.parent/'revised-tail-v1/progress.json')['branches']}
    for name,b in branches.items():
        rows=b['rows'];expected=[10] if b['policy']=='end-only' else list(range(1,11))
        if b.get('stopped'):
            assert name=='P05-once-triggered' and b['stopped']['stage']==9
            expected=list(range(1,9))
        assert [r['stage'] for r in rows]==expected
        assert b['reference']==old[b['person']]['reference']
        assert b['roi']==old[b['person']]['roi']
        if b['policy']=='once-triggered':
            assert [r['stage'] for r in rows if r['rebased']]==[b['alarm_stage']]
            for previous,r in zip(rows,rows[1:]):
                if r['stage']>b['alarm_stage']:assert sha(r['input'])==sha(previous['output'])
        for r in rows:
            c=lookup.get(sha(r['output']))
            if c and b['policy']!='once-triggered':assert c['input_sha256']==sha(b['reference'])
    assert sha(branches['P03-r1-end-only']['rows'][0]['output'])==sha(branches['P03-r2-end-only']['rows'][0]['output'])
    end=branches['P04-end-only']['rows'][0]['output']
    assert sha(end)==sha(branches['P04-always-original']['rows'][-1]['output'])
    actual_by_branch={}
    for r in records:
        for name in r['branches']:actual_by_branch[name]=actual_by_branch.get(name,0)+1
    result=dict(passed=True,new_successful_unique_calls=25,failed_calls_recorded=1,new_attempts=26,unexecuted_planned_calls=1,retries_recorded=0,dimensions=[1024,1536],branch_count=len(branches),generated_by_branch=actual_by_branch,checks=['collection_terminated_and_no_pending','25_unique_records_and_outputs','failed_stage_and_input','input_and_output_hashes','input_prompt_digest','first_attempt','no_discarded_pocket_prompt','requested_dimensions','stage_coverage_or_explicit_failure','original_reference_and_roi','once_only_reset','continuation_input_link','original_input_for_end_and_always','P03_shared_end','P04_shared_end_and_always'],note='Failure/retry counts describe retained call records; no model-version or seed reproducibility is asserted.',hashes={str(f.relative_to(ROOT)):sha(f) for f in [g/'progress.json',g/'pending.json',ROOT/'PROTOCOL.md',ROOT/'EXTENSION_EVALUATION.md']})
    (ROOT/'generation-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
