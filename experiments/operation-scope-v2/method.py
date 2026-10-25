"""Normalize explicit source-photo instructions before the frozen reducer.

Only recognized object lists and complete instruction forms are rewritten.
No reference states, model calls, or evaluation-specific IDs enter this module.
"""
import importlib.util
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('scope_previous_method',ROOT.parent/'clause-normalization-v1/method.py')
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
SOURCE=previous.source
# Keep the previous expression intact rather than relying on its outer grouping.
START=re.compile(r'\b(?:get rid of|take away|maintain(?:ing)?|revert(?:ing)?|reset(?:ting)?)\b|'+previous.START.pattern,re.I)
PHOTO=r'(?:the )?(?:original|source) (?:photo|image)'
RESTORE_FORMS=[
    re.compile(r'^(?:revert|reset|return|restore) (.+?) (?:back )?to (?:how (?:it|they) looked in '+PHOTO+r'|'+PHOTO+r'(?: appearance)?)$',re.I),
    re.compile(r'^(?:put|bring) (.+?) back (?:to|as in) '+PHOTO+r'$',re.I),
    re.compile(r'^restore (?:the )?source (.+?)$',re.I),
]
KEEP_FORM=re.compile(r'^(?:keep(?:ing)?|leav(?:e|ing)|maintain(?:ing)?|preserv(?:e|ing)|retain(?:ing)?) (.+?)(?: exactly as (?:it|they) (?:is|are) now| just as (?:it|they) (?:is|are)| alone| as before| unchanged)$',re.I)
REMOVE_FORM=re.compile(r'^(?:get rid of|take away|delete|exclude) (.+?)(?: entirely| completely)?$',re.I)

def objects(text):
    tokens=set(re.findall(r'[a-z]+',text.lower()))
    fields={k for k,p in SOURCE.contract.keep.v1.MENTIONS.items() if re.search(p,text,re.I)}
    return fields if fields and tokens<=previous.OBJECT_WORDS else set()

def normalize(request):
    if any(c in request for c in ['"','“','”','`']):return request,[]
    pieces,evidence=[],[]
    for sentence in re.split(r'[.;]',request):
        if not sentence.strip():continue
        risk=re.sub(r"\b(?:do not|don't) (?:change|alter)\b",'',sentence,flags=re.I)
        if SOURCE.contract.keep.v1.UNSAFE.search(risk):
            pieces.append(sentence.strip());continue
        matches=list(START.finditer(sentence))
        if not matches:pieces.append(sentence.strip());continue
        prefix=sentence[:matches[0].start()].strip(' ,')
        if prefix:pieces.append(prefix)
        for i,match in enumerate(matches):
            end=matches[i+1].start() if i+1<len(matches) else len(sentence)
            fragment=sentence[match.start():end].strip(' ,')
            fragment=re.sub(r'[,\s]+(?:and|but|while|then|without)$','',fragment,flags=re.I).strip(' ,')
            rewritten=fragment
            for pattern in RESTORE_FORMS:
                found=pattern.fullmatch(fragment)
                if found and objects(found[1]):
                    rewritten='Restore the original '+re.sub(r'^the\s+','',found[1],flags=re.I);break
            if rewritten==fragment:
                found=KEEP_FORM.fullmatch(fragment)
                if found and objects(found[1]):rewritten='Keep '+found[1]+' unchanged'
            if rewritten==fragment:
                found=REMOVE_FORM.fullmatch(fragment)
                if found and objects(found[1]) and objects(found[1])<=SOURCE.contract.REMOVABLE:
                    rewritten='Remove '+found[1]
            if rewritten!=fragment:evidence.append(dict(original=fragment,normalized=rewritten))
            pieces.append(rewritten)
    result='. '.join(pieces)+'.' if evidence else request
    normalized,old_evidence=previous.normalize(result)
    return normalized,evidence+old_evidence

def update(prior,request,raws):
    normalized,evidence=normalize(request)
    state,trace=previous.update(prior,normalized,raws,atomic=True)
    trace.update(normalized_request=normalized,normalization=evidence)
    return state,trace
