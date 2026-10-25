"""Replay observed first responses through the public pipeline, without new inference."""
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'local-studio'))
from instruction_pipeline import process_request
from request_state import INITIAL,SYSTEM,EXAMPLES,render_prompt

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    study=ROOT/'experiments/single-extraction-validation-v1'
    histories=json.loads((study/'benchmark.json').read_text())['histories']
    paths=[study/'benchmark.json',study/'frozen.json',ROOT/'local-studio/instruction_pipeline.py',
        ROOT/'local-studio/checks/test_instruction_pipeline.py',ROOT/'local-studio/request_state.py',Path(__file__).resolve()]
    checked=0
    for model in ['qwen3','llama32']:
        response_path=study/f'transcripts-{model}.json';result_path=study/f'results-{model}.json'
        records=json.loads(response_path.read_text());result=json.loads(result_path.read_text())['methods']['single_extraction_checked']
        paths += [response_path,result_path]
        observed={(r['dialogue'],r['turn']):r['observed'] for r in result['rows']}
        for dialogue,requests in histories.items():
            state=dict(INITIAL)
            for i,item in enumerate(requests,1):
                extractor=Mock();extractor.ask.return_value=records[f'{dialogue}-{i}']['first']
                prior=dict(state);out=process_request(state,item['request'],extractor)
                extractor.ask.assert_called_once_with(SYSTEM,item['request'],max_tokens=260,examples=EXAMPLES)
                assert state==prior
                assert out['state']==observed[dialogue,i]
                assert out['prompt']==render_prompt(out['state'])
                assert out['model_calls']==1
                state=out['state'];checked+=1
    target=ROOT/'paper/implementation-verification.json'
    target.write_text(json.dumps(dict(passed=True,actual_model_calls=0,replayed_requests=checked,
        one_extraction_per_request=True,state_and_prompt_match=True,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths}),ensure_ascii=False,indent=2)+'\n')
    print('Public one-extraction pipeline verified on',checked,'saved responses; new model calls 0')

if __name__=='__main__':main()
