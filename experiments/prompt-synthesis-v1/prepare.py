"""Freeze three prompts: full history, structured latest state, and agent synthesis."""
import hashlib
import json
import re
from pathlib import Path

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

ROOT = Path(__file__).resolve().parent
MODEL = 'mlx-community/Qwen3-4B-4bit'
FIRST = ('Read the chronological image-edit requests. The newest request for an item overrides older '
         'requests, and removals cancel additions. Write one final English edit prompt containing only '
         'the current requirements and all preservation constraints. Never keep superseded colors, '
         'objects, or locations. Do not infer gender or add requirements. Output only the prompt.')
SECOND = ('Audit the proposed final image-edit prompt against the chronological request history. '
          'Resolve overrides and removals exactly. Remove old conditions and invented details; restore '
          'anything current that was omitted. Output only the corrected final prompt.')
GENDERED = re.compile(r'\b(man|male|woman|female|he|him|his|she|her|hers)\b', re.I)
REPLACE = {'man': 'person', 'male': 'person', 'woman': 'person', 'female': 'person',
           'he': 'they', 'him': 'them', 'his': "the person's", 'she': 'they',
           'her': 'the person', 'hers': "the person's"}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ask(model, tokenizer, system, user):
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False,
        add_generation_prompt=True, enable_thinking=False)
    return generate(model, tokenizer, prompt=prompt, max_tokens=1000,
        sampler=make_sampler(temp=0), verbose=False).strip()

def main():
    targets = [ROOT / f'{name}-prompt.txt' for name in ['history', 'state', 'agent']]
    if any(path.exists() for path in targets):
        raise RuntimeError('Prompts already frozen; refusing to regenerate them.')
    source = json.loads((ROOT / 'history.json').read_text())
    turns = source['turns']
    chronological = '\n'.join(f'{i}. {turn["request"]}' for i, turn in enumerate(turns, 1))
    history_prompt = ('Edit only the supplied photograph. Apply these requests in chronological order; '
        'when an item is changed or removed later, its latest instruction takes precedence. Preserve '
        'everything else.\n' + chronological + '\n' + source['preserve'])
    state = {}
    for turn in turns:
        state.update(turn['updates'])
    assert state == {'blazer': 'charcoal gray', 'inner_shirt': 'ivory crew-neck',
        'background': 'quiet library with wooden bookshelves and one warm lamp',
        'pin': 'one small gold square pin on the viewer-right lapel', 'necklace': 'none'}
    state_prompt = ('Edit only the supplied photograph. Apply exactly these final current requirements; '
        'preserve everything else:\n'
        '- Replace the casual top with a charcoal-gray blazer over an ivory crew-neck shirt.\n'
        '- Add exactly one small gold square pin on the lapel at the viewer\'s right; no silver pin.\n'
        '- There must be no necklace or pendant.\n'
        '- Set the background to a quiet library with wooden bookshelves and one warm lamp.\n'
        + source['preserve'])
    user = 'Preservation constraints:\n' + source['preserve'] + '\n\nChronological requests:\n' + chronological
    model, tokenizer = load(MODEL)
    draft = ask(model, tokenizer, FIRST, user)
    audit_user = user + '\n\nDraft final prompt:\n' + draft
    final = ask(model, tokenizer, SECOND, audit_user)
    if not draft or not final:
        raise RuntimeError('Agent returned an empty prompt.')
    before_neutralization = final
    if not GENDERED.search(user):
        final = GENDERED.sub(lambda match: REPLACE[match.group(0).lower()], final)
    transcript = {'model': MODEL, 'temperature': 0, 'max_tokens_per_pass': 1000,
        'history_sha256': sha(ROOT / 'history.json'), 'first': {'system': FIRST, 'user': user,
        'response': draft}, 'second': {'system': SECOND, 'user': audit_user, 'response': before_neutralization},
        'gender_neutralization': {'applied': final != before_neutralization,
        'before': before_neutralization, 'after': final}}
    (ROOT / 'agent-transcript.json').write_text(json.dumps(transcript, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'final-state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    for name, value in [('history', history_prompt), ('state', state_prompt), ('agent', final)]:
        (ROOT / f'{name}-prompt.txt').write_text(value + '\n')
    print('AGENT PROMPT\n' + final, flush=True)

if __name__ == '__main__':
    main()
