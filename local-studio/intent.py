"""Explicit edit operations, applied to state by code rather than a model rewrite."""
import re
FIELDS={'shirt_color':r'셔츠|상의|\bshirt\b|\btop\b','background':r'배경|\bbackground\b','pin':r'핀|\bpin\b'}
VALUES={'pale blue':r'옅은\s*파란색|연한\s*파란색|\bpale blue\b|\blight blue\b','navy':r'남색|\bnavy\b','white':r'흰색|하얗게|하얀색|\bwhite\b','black':r'검정|검은색|검게|\bblack\b','gray':r'회색|\bgr[ae]y\b','silver':r'은색|\bsilver\b','gold':r'금색|\bgold\b','red':r'빨간색|빨강|\bred\b','blue':r'파란색|파랑|\bblue\b','green':r'초록색|초록|\bgreen\b','ocean':r'바다|\bocean\b|\bsea\b','library':r'도서관|\blibrary\b','garden':r'정원|\bgarden\b','studio':r'스튜디오|\bstudio\b'}
COLORS=set(VALUES)-{'ocean','library','garden','studio'}
QUESTION='어떤 항목을 어떻게 바꿀까요? 셔츠 색, 배경, 핀을 구체적으로 적어주세요.'
def fields(text):return [k for k,v in FIELDS.items() if re.search(v,text,re.I)]
def resolve(request,state):
 text=request.strip().lower()
 if re.search(r'아까|이전처럼|전처럼|\blike before\b|\bas before\b|\bundo\b|취소',text):
  return {'clarification':'어느 버전으로 돌아갈까요? 왼쪽 이전 버전에서 선택해주세요.'}
 if re.search(r'머리|헤어|\bhair\b|ignore.*instructions|지시.*무시',text):return {'clarification':'셔츠 색, 배경, 핀 중 어떤 항목을 바꿀까요?'}
 if not fields(text):return {'clarification':QUESTION}
 clauses=[c.strip() for c in re.split(r'[,.;\n]|\band\b|두고|하고',text) if c.strip()]
 operations=[];unresolved=[]
 for clause in clauses:
  keys=fields(clause)
  if not keys:
   # Continuation "Keep it as it is" only reinforces the immediately preceding keep.
   if operations and re.fullmatch(r'keep it as it is',clause):continue
   if operations and re.fullmatch(r'not (red|white|black|blue|navy|silver|gold|gray|green)',clause):
    if operations[-1].get('value')==clause[4:]:return {'clarification':QUESTION}
    continue
   unresolved.append(clause);continue
  neg_remove=bool(re.search(r'(빼|없애|제거하|삭제하|지우)지\s*말|(?:do not|don.t|never)\s+(?:remove|erase|delete)',clause))
  keep=neg_remove or bool(re.search(r'그대로|유지|\bkeep\b|unchanged',clause))
  reset=bool(re.search(r'원본|\boriginal\b',clause))
  if reset:
   if re.search(r'말|않|\bnot\b|don.t',clause):return {'clarification':QUESTION}
   operations.extend({'field':k,'op':'reset'} for k in keys);continue
  if keep:operations.extend({'field':k,'op':'keep'} for k in keys);continue
  if keys==['pin'] and re.search(r'빼|없애|제거|삭제|지워|\bremove\b|\berase\b|\bdelete\b',clause):
   operations.append({'field':'pin','op':'set','value':'none'});continue
  # Strip explicitly rejected alternatives, preserving the positive clause.
  positive=re.sub(r'\bnot\s+\w+(?:\s+\w+)?$','',clause)
  if '말고' in positive:positive=' '.join(keys)+' '+positive.split('말고',1)[1]
  if re.search(r'하지\s*마|않|don.t|\bnot\b|\bnever\b',positive):return {'clarification':QUESTION}
  hits=[];occupied=[]
  for value,pattern in VALUES.items():
   for match in re.finditer(pattern,positive,re.I):
    if not any(match.start()<b and match.end()>a for a,b in occupied):hits.append(value);occupied.append(match.span())
  values=set(hits)
  if len(keys)==1 and len(values)==1:
   value=next(iter(values));key=keys[0]
   if key!='background' and value not in COLORS:unresolved.append(clause);continue
   operations.append({'field':key,'op':'set','value':value})
  else:unresolved.append(clause)
 if unresolved:return None # Structured model fallback; never partially apply a request.
 if not operations:return {'clarification':QUESTION}
 return apply(operations,state)
def apply(operations,state):
 if not isinstance(operations,list) or not operations or len(operations)>12:return {'clarification':QUESTION}
 updated=dict(state);seen={}
 for a in operations:
  if not isinstance(a,dict) or a.get('field') not in FIELDS or a.get('op') not in ('set','reset','keep'):return {'clarification':QUESTION}
  key=a['field'];op=a['op'];value=state[key] if op=='keep' else 'original' if op=='reset' else a.get('value')
  if not isinstance(value,str) or not value.strip() or len(value)>120 or '\n' in value:return {'clarification':QUESTION}
  if key in seen and seen[key]!=value:return {'clarification':f'{key}에 서로 다른 요청이 있어요. 원하는 값을 하나로 적어주세요.'}
  seen[key]=value;updated[key]=value
 return {'state':updated,'operations':operations,'message':'현재 설정을 유지했어요.' if updated==state else '적용 완료'}
