"""Three-turn local state update smoke test; no paid API."""
import json,time,argparse
from pathlib import Path
import mlx.core as mx
from mlx_lm import load,generate
from mlx_lm.sample_utils import make_sampler
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(); parser.add_argument('--model',default='mlx-community/Qwen3-0.6B-4bit'); parser.add_argument('--output',default='prompt-results.json'); args=parser.parse_args()
start=time.perf_counter()
model,tokenizer=load(args.model)
load_seconds=time.perf_counter()-start
state={'shirt_color':'gray','background':'studio','pin':'none'}
cases=[('셔츠를 남색으로 바꿔줘.',{'shirt_color':'navy','background':'studio','pin':'none'}),('배경은 옅은 파란색으로 하고 은색 핀 하나 달아줘.',{'shirt_color':'navy','background':'pale blue','pin':'silver'}),('셔츠는 흰색으로 바꾸고 핀은 빼줘. 배경은 그대로.',{'shirt_color':'white','background':'pale blue','pin':'none'})]
records=[]
for request,expected in cases:
    messages=[{'role':'system','content':'당신은 이미지 편집 설정 관리자다. 현재 설정에서 사용자 요청으로 바뀐 값만 변경하고 나머지는 유지하라. 출력은 shirt_color, background, pin 세 키만 있는 JSON 객체다. current나 request 키를 출력하지 마라. 값은 영어로 작성한다. 남색=navy, 흰색=white, 옅은 파란색=pale blue, 은색=silver, 핀 없음=none. 마크다운 없이 JSON만 출력하라.'},
    {'role':'user','content':'현재 설정: {"shirt_color":"red","background":"garden","pin":"gold"}\n요청: 배경만 바다로 바꿔줘.'},
    {'role':'assistant','content':'{"shirt_color":"red","background":"ocean","pin":"gold"}'},
    {'role':'user','content':'현재 설정: '+json.dumps(state,ensure_ascii=False)+'\n요청: '+request}]

    prompt=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    t=time.perf_counter();out=generate(model,tokenizer,prompt=prompt,max_tokens=160,sampler=make_sampler(temp=0),verbose=False)
    elapsed=time.perf_counter()-t
    try:
        parsed=json.loads(out)
        valid=isinstance(parsed,dict) and set(parsed)==set(state) and all(isinstance(v,str) for v in parsed.values())
    except Exception: parsed=None;valid=False
    records.append({'request':request,'input_state':dict(state),'raw':out,'parsed':parsed,'valid_json_schema':valid,'expected':expected,'exact_expected':parsed==expected,'seconds':elapsed})
    if valid: state=parsed
result={'model':args.model,'load_seconds':load_seconds,'mlx_peak_memory_bytes':mx.get_peak_memory(),'cases':records,'passed':all(r['exact_expected'] for r in records),'note':'Three fixed cases only, not general Korean instruction accuracy.'}
(ROOT/args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
