"""Resolve explicit actions first; use a constrained local model for other phrasing."""
import json,sys
from intent import resolve,apply,fields,QUESTION

def interpret(payload):
 state=payload['state'];request=payload['request']
 direct=resolve(request,state)
 if direct is not None:return direct
 from mlx_lm import load,generate
 from mlx_lm.sample_utils import make_sampler
 model,tok=load('mlx-community/Qwen3-4B-4bit')
 instructions='''Extract image edit operations. Output JSON only: {"operations":[{"field":"shirt_color|background|pin","op":"set|reset|keep","value":"short English description","evidence":"exact substring from the request"}]}. Never output the entire current state. Only explicitly mentioned fields. reset means original image, NOT a guessed original color. keep means unchanged. set requires a requested value. No changes inferred from examples. If ambiguous, unsupported, or you cannot identify a requested value, output {"clarification":"어떤 항목을 어떻게 바꿀까요?"}. Do not invent values or silently ignore changes. Colors use English; 원본 means reset, 없음/제거 means pin set none. Negation must be respected.'''
 messages=[{'role':'system','content':instructions},{'role':'user','content':'Current: '+json.dumps(state)+'\nRequest: '+request}]
 prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
 raw=generate(model,tok,prompt=prompt,max_tokens=400,sampler=make_sampler(temp=0),verbose=False)
 try:
  result=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
  if result.get('clarification'):return {'clarification':QUESTION}
  ops=result['operations'];mentioned=set(fields(request))
  if {x.get('field') for x in ops}!=mentioned:return {'clarification':QUESTION}
  for op in ops:
   evidence=op.get('evidence')
   if not isinstance(evidence,str) or not evidence or evidence.lower() not in request.lower():return {'clarification':QUESTION}
  result=apply(ops,state)
  # An unchanged model response is not proof that a requested change was understood.
  if result.get('state')==state:return {'clarification':QUESTION}
  return result
 except (ValueError,KeyError,TypeError,AttributeError):return {'clarification':QUESTION}
if __name__=='__main__':print(json.dumps(interpret(json.load(sys.stdin)),ensure_ascii=False))
