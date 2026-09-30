"""Freeze six image inputs and three history/mode prompt sets before generation."""
import hashlib
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageOps
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BASE = REPO / 'experiments/prompt-synthesis-v1'
MODEL = 'mlx-community/Qwen3-4B-4bit'
PEOPLE = {'R01': REPO / 'experiments/real-people-v1/reference-R01.png',
          'R02': REPO / 'experiments/real-people-v1/reference-R02.png',
          'R03': REPO / 'assets/people/real/pexels-17858295.jpg',
          'R04': REPO / 'assets/people/real/pexels-6311615.jpg',
          'R05': REPO / 'assets/people/real/pexels-4461037.jpg',
          'R06': REPO / 'assets/people/real/pexels-4970991.jpg'}
FIRST = ('Read chronological image-edit requests. The newest request for each item overrides old '
         'requests and removals cancel additions. Write one English edit prompt with only the final '
         'current requirements and all preservation constraints. Omit superseded colors, items, and '
         'locations. Do not infer gender or add requirements. Output the prompt only.')
SECOND = ('Audit the draft final edit prompt against the original chronological requests. Correct any '
          'missing final requirement, obsolete condition, wrong count, shape, location, color, or invented '
          'detail. Output only the corrected final edit prompt.')
GENDERED = re.compile(r'\b(man|male|woman|female|he|him|his|she|her|hers)\b', re.I)
REPLACE = {'man': 'person', 'male': 'person', 'woman': 'person', 'female': 'person',
           'he': 'they', 'him': 'them', 'his': "the person's", 'she': 'they',
           'her': 'the person', 'hers': "the person's"}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ask(model, tokenizer, system, user):
    prompt = tokenizer.apply_chat_template([
        {'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return generate(model, tokenizer, prompt=prompt, max_tokens=1100,
        sampler=make_sampler(temp=0), verbose=False).strip()

def current_prompt(state, preserve):
    if state['blazer'] == 'none':
        clothing = ('Replace the casual top with a plain light-gray crew-neck sweater. '
                    'There must be no blazer or jacket visible and no inner shirt visible.')
    else:
        clothing = (f"Replace the casual top with a {state['blazer']} blazer over an "
                    f"{state['inner_shirt']} shirt.")
    pin = ('There must be no pin anywhere.' if state['pin'] == 'none' else
           f"Add exactly {state['pin']}; remove the old silver circular pin.")
    necklace = ('There must be no necklace or pendant.' if state['necklace'] == 'none' else
                f"Add exactly {state['necklace']}; remove the old silver teardrop necklace.")
    background = f"Replace the old background with a {state['background']}."
    return ('Edit only the supplied photograph. Apply only these final current requirements; '
            'preserve everything else:\n- ' + '\n- '.join([clothing, pin, necklace, background]) +
            '\n' + preserve)

def main():
    prompt_dir = ROOT / 'prompts'
    ref_dir = ROOT / 'references'
    if (ROOT / 'prepare-manifest.json').exists() or prompt_dir.exists() or ref_dir.exists():
        raise RuntimeError('Expanded inputs or prompts already prepared; refusing to overwrite them.')
    prompt_dir.mkdir(parents=True)
    ref_dir.mkdir(parents=True)
    photo_manifest = {}
    for person, source in PEOPLE.items():
        target = ref_dir / f'{person}.png'
        if person in ['R01', 'R02']:
            shutil.copyfile(source, target)
        else:
            with Image.open(source) as photo:
                image = ImageOps.exif_transpose(photo).convert('RGB')
                image.load()
            scale = min(512 / image.width, 768 / image.height, 1)
            width = max(128, int(image.width * scale) // 16 * 16)
            height = max(128, int(image.height * scale) // 16 * 16)
            image.resize((width, height), Image.Resampling.LANCZOS).save(target)
        with Image.open(target) as image:
            size = list(image.size)
        photo_manifest[person] = {'source': str(source.relative_to(REPO)),
            'source_sha256': sha(source), 'reference_sha256': sha(target), 'size': size}
    shutil.copyfile(BASE / 'history.json', ROOT / 'histories/H1.json')
    for mode in ['history', 'state', 'agent']:
        shutil.copyfile(BASE / f'{mode}-prompt.txt', prompt_dir / f'H1-{mode}.txt')
    model, tokenizer = load(MODEL)
    histories = {}
    for history_id in ['H1', 'H2', 'H3']:
        source = ROOT / 'histories' / f'{history_id}.json'
        history = json.loads(source.read_text())
        state = {}
        for turn in history['turns']:
            state.update(turn['updates'])
        (ROOT / 'histories' / f'{history_id}-final-state.json').write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        if history_id != 'H1':
            chronology = '\n'.join(f'{i}. {turn["request"]}'
                for i, turn in enumerate(history['turns'], 1))
            user = 'Preservation constraints:\n' + history['preserve'] + '\n\nChronological requests:\n' + chronology
            raw = ('Edit only the supplied photograph. Apply these requests in chronological order; '
                'when an item is changed or removed later, its latest instruction takes precedence. '
                'Preserve everything else.\n' + chronology + '\n' + history['preserve'])
            structured = current_prompt(state, history['preserve'])
            draft = ask(model, tokenizer, FIRST, user)
            audit_user = user + '\n\nDraft final prompt:\n' + draft
            final_before = ask(model, tokenizer, SECOND, audit_user)
            if not draft or not final_before:
                raise RuntimeError(f'Agent returned an empty prompt for {history_id}.')
            final = (GENDERED.sub(lambda match: REPLACE[match.group(0).lower()], final_before)
                     if not GENDERED.search(user) else final_before)
            for mode, value in [('history', raw), ('state', structured), ('agent', final)]:
                (prompt_dir / f'{history_id}-{mode}.txt').write_text(value + '\n')
            transcript = {'model': MODEL, 'temperature': 0, 'max_tokens_per_pass': 1100,
                'first': {'system': FIRST, 'user': user, 'response': draft},
                'second': {'system': SECOND, 'user': audit_user, 'response': final_before},
                'gender_neutralization': {'applied': final != final_before,
                    'before': final_before, 'after': final}}
            (prompt_dir / f'{history_id}-agent-transcript.json').write_text(
                json.dumps(transcript, ensure_ascii=False, indent=2) + '\n')
        histories[history_id] = {'history_sha256': sha(source),
            'final_state_sha256': sha(ROOT / 'histories' / f'{history_id}-final-state.json'),
            'prompts': {mode: sha(prompt_dir / f'{history_id}-{mode}.txt')
                        for mode in ['history', 'state', 'agent']}}
    manifest = {'people': photo_manifest, 'histories': histories,
        'base_experiment': str(BASE.relative_to(REPO)), 'prepare_code_sha256': sha(Path(__file__))}
    (ROOT / 'prepare-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print('Prepared 6 references and 9 fixed prompts.', flush=True)
    for history_id in ['H2', 'H3']:
        print(history_id, (prompt_dir / f'{history_id}-agent.txt').read_text(), flush=True)

if __name__ == '__main__':
    main()
