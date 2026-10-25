"""Post-hoc comparison with schema-only patch reducers, on every saved request.

These reducers use no lexical request rules and no reference states. Reference
updates enter only the scoring loop, never the reducer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'local-studio'))
from request_state import INITIAL, VALUES, unique_object


def reduce_patch(prior, raws):
    for raw in raws:
        try:
            patch = json.loads(raw[raw.find('{'):raw.rfind('}')+1], object_pairs_hook=unique_object)
            if not isinstance(patch, dict) or any(
                    field not in VALUES or not isinstance(value, str)
                    or value not in VALUES[field]+['original', 'keep'] for field, value in patch.items()):
                continue
        except (ValueError, TypeError):
            continue
        return {**prior, **{k: v for k, v in patch.items() if v != 'keep'}}
    return dict(prior)


def score(histories, records):
    methods = {}
    for name in ['first_only', 'review_then_first']:
        rows, final = [], 0
        for dialogue, turns in histories.items():
            state, gold = dict(INITIAL), dict(INITIAL)
            for number, turn in enumerate(turns, 1):
                record = records[f'{dialogue}-{number}']
                assert record['request'] == turn['request']
                raws = [record['first']] if name == 'first_only' else [record['second'], record['first']]
                state = reduce_patch(state, raws)
                gold.update(turn['updates'])
                rows.append(dict(dialogue=dialogue, turn=number, observed=dict(state), expected=dict(gold),
                                 exact=state == gold, correct_slots=sum(state[k] == gold[k] for k in state)))
            final += state == gold
        methods[name] = dict(exact_turns=sum(row['exact'] for row in rows), turns=len(rows),
                             correct_slots=sum(row['correct_slots'] for row in rows), slots=len(rows)*len(INITIAL),
                             exact_final_dialogues=final, dialogues=len(histories), rows=rows)
    return methods


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', action='append', required=True)
    args = parser.parse_args()
    studies, sources = {}, {}
    for study in args.study:
        folder = ROOT / 'experiments' / study
        benchmark = folder / 'benchmark.json'
        if not benchmark.exists():
            benchmark = folder / 'frozen.json'
        histories = json.loads(benchmark.read_text())['histories']
        transcripts = folder / 'transcripts.json'
        records = json.loads(transcripts.read_text())
        assert len(records) == sum(map(len, histories.values())), 'Wait for complete model responses'
        studies[study] = score(histories, records)
        for path in [benchmark, transcripts]:
            sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = dict(posthoc_analysis=True, additional_model_calls=0,
                  scope='Schema-only initial/reviewed patch reducers; all saved requests, separate study denominators',
                  studies=studies, source_sha256=sources,
                  reducer_schema_sha256=hashlib.sha256((ROOT / 'local-studio/request_state.py').read_bytes()).hexdigest(),
                  verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    target = ROOT / 'experiments/clause-normalization-v1/plain-patch-comparison.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({study: {method: (r['exact_turns'], r['turns'])
                             for method, r in data.items()} for study, data in studies.items()}, indent=2))


if __name__ == '__main__':
    main()
