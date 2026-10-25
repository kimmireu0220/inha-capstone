"""Keep non-executable instructions from changing the stored edit state."""
import importlib.util
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('eligibility_previous',ROOT.parent/'operation-scope-v2/method.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
NEGATED=re.compile(r"\b(?:do not|don't|never)\s+(?:get rid of|take away|take off|remove|delete|exclude|restore|reset|revert|return|change|alter|add|wear|put|bring)\b",re.I)
QUOTES=re.compile(r'"[^"\n]*"|“[^”\n]*”|`[^`\n]*`')
DESCRIPTION=re.compile(r'\b(?:caption|quoted text|not an editing instruction)\b',re.I)

def ignored_spans(request):
    spans=[]
    quoted=list(QUOTES.finditer(request))
    outside=QUOTES.sub(' ',request)
    if DESCRIPTION.search(outside):
        spans.extend(dict(start=q.start(),end=q.end(),reason='quoted_text',evidence=q.group()) for q in quoted)
    for sentence in re.finditer(r'[^.;]+',request):
        text=sentence.group()
        if re.search(r'\bif\b',text,re.I):
            spans.append(dict(start=sentence.start(),end=sentence.end(),reason='conditional',evidence=text.strip()))
            continue
        for negative in NEGATED.finditer(text):
            # The next action begins a different instruction in the same sentence.
            following=previous.START.search(text,negative.end())
            end=following.start() if following else len(text)
            spans.append(dict(start=sentence.start()+negative.start(),end=sentence.start()+end,
                reason='negated',evidence=text[negative.start():end].strip(' ,')))
    return spans

def protected_fields(request):
    spans=ignored_spans(request);protected={}
    for field,pattern in previous.SOURCE.contract.keep.v1.MENTIONS.items():
        mentions=list(re.finditer(pattern,request,re.I))
        if not mentions:continue
        last=mentions[-1]
        found=[s for s in spans if s['start']<=last.start()<s['end']]
        if found:protected[field]=found[-1]
    return protected

def update(prior,request,raws):
    state,trace=previous.update(prior,request,raws)
    protected=protected_fields(request)
    for field in protected:state[field]=prior[field]
    trace['ignored_instructions']=protected
    return state,trace
