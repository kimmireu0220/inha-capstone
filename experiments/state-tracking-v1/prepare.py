"""Freeze both automatic prompts, then score tracked states against annotations."""
import hashlib
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / 'local-studio'))
from request_state import INITIAL, PRESERVE, StateExtractor, render_prompt

spec = importlib.util.spec_from_file_location('prior_prepare',
    REPO / 'experiments/prompt-synthesis-expanded-v1/prepare.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main(root=None):
    global ROOT
    if root is not None:
        ROOT = Path(root)
    benchmark = json.loads((ROOT / 'benchmark.json').read_text())
    inputs = {'protocol': sha(ROOT / 'PROTOCOL.md'),
              'benchmark': sha(ROOT / 'benchmark.json'),
              'method': sha(REPO / 'local-studio/request_state.py'),
              'prepare': sha(Path(__file__)),
              'prior_prepare': sha(REPO / 'experiments/prompt-synthesis-expanded-v1/prepare.py')}
    if root is not None:
        inputs['entrypoint'] = sha(ROOT / 'prepare.py')
        inputs['runner'] = sha(ROOT / 'run.py')
        inputs['shared_runner'] = sha(Path(__file__).parent / 'run.py')
    frozen = ROOT / 'prepare-inputs.json'
    if frozen.exists():
        assert json.loads(frozen.read_text()) == inputs, 'Preparation inputs changed'
    else:
        save(frozen, inputs)
    prompts, refs = ROOT / 'prompts', ROOT / 'references'
    prompts.mkdir(exist_ok=True)
    refs.mkdir(exist_ok=True)
    for index in range(1, 7):
        name = f'R{index:02d}.png'
        source = REPO / 'experiments/prompt-synthesis-expanded-v1/references' / name
        target = refs / name
        if target.exists():
            assert sha(target) == sha(source)
        else:
            shutil.copyfile(source, target)
    extractor = StateExtractor()
    for name, history in benchmark['histories'].items():
        transcript_path = prompts / f'{name}-transcript.json'
        if transcript_path.exists():
            continue
        # Only request strings cross the model boundary. Annotated updates stay here.
        requests = [turn['request'] for turn in history['turns']]
        chronology = '\n'.join(f'{i}. {request}' for i, request in enumerate(requests, 1))
        user = 'Preservation constraints:\n' + PRESERVE + '\n\nChronological requests:\n' + chronology
        start = time.monotonic()
        draft = extractor.ask(prior.FIRST, user, max_tokens=1100)
        audit_user = user + '\n\nDraft final prompt:\n' + draft
        before_neutralization = extractor.ask(prior.SECOND, audit_user, max_tokens=1100)
        agent = prior.GENDERED.sub(lambda match: prior.REPLACE[match.group(0).lower()],
                                  before_neutralization)
        agent_seconds = time.monotonic() - start
        start = time.monotonic()
        state, ledger = extractor.replay(requests)
        tracked_seconds = time.monotonic() - start
        tracked = render_prompt(state)
        for mode, text in [('agent', agent), ('tracked', tracked)]:
            if not text.strip():
                raise RuntimeError('Empty generated prompt')
            (prompts / f'{name}-{mode}.txt').write_text(text + '\n')
        transcript = {'model': prior.MODEL, 'temperature': 0,
            'agent': {'draft': draft, 'audit_response': before_neutralization,
                'final': agent, 'model_calls': 2, 'seconds': agent_seconds},
            'tracked': {'ledger': ledger, 'final_state': state, 'final': tracked,
                'model_calls': sum(len(row['attempts']) for row in ledger),
                'rejected_turns': sum(not row['accepted'] for row in ledger),
                'seconds': tracked_seconds}}
        save(transcript_path, transcript)
        print('PROMPTS FIXED', name, 'agent', round(agent_seconds, 1),
              'tracked', round(tracked_seconds, 1),
              'rejected', transcript['tracked']['rejected_turns'], flush=True)
    # Evaluate only after every automatic prompt has been fixed.
    rows = []
    for name, history in benchmark['histories'].items():
        transcript = json.loads((prompts / f'{name}-transcript.json').read_text())
        expected = dict(INITIAL)
        for turn, observed in zip(history['turns'], transcript['tracked']['ledger']):
            expected.update(turn['updates'])
            rows.append({'history': name, 'turn': observed['turn'],
                'expected': dict(expected), 'observed': observed['state'],
                'correct_slots': sum(expected[k] == observed['state'][k] for k in INITIAL),
                'changed_correct': sum(expected[k] == observed['state'][k] for k in turn['updates']),
                'changed_total': len(turn['updates']), 'accepted': observed['accepted']})
        (prompts / f'{name}-oracle.txt').write_text(render_prompt(expected) + '\n')
    save(ROOT / 'state-scores.json', {'turns': rows,
        'correct_slots': sum(r['correct_slots'] for r in rows), 'total_slots': len(rows) * 6,
        'changed_correct': sum(r['changed_correct'] for r in rows),
        'changed_total': sum(r['changed_total'] for r in rows),
        'final_correct_slots': sum(r['correct_slots'] for r in rows if r['turn'] == 8),
        'final_total_slots': len(benchmark['histories']) * 6,
        'oracle_prompt_matches': {h: sha(prompts / f'{h}-tracked.txt') == sha(prompts / f'{h}-oracle.txt')
                                 for h in benchmark['histories']}})
    manifest = {'inputs': inputs,
        'references': {p.stem: sha(p) for p in sorted(refs.glob('*.png'))},
        'prompts': {p.stem: sha(p) for p in sorted(prompts.glob('*.txt'))},
        'transcripts': {p.stem: sha(p) for p in sorted(prompts.glob('*-transcript.json'))}}
    save(ROOT / 'prepare-manifest.json', manifest)
    print('All eight automatic prompts frozen. State scores recorded.', flush=True)


if __name__ == '__main__':
    main()
