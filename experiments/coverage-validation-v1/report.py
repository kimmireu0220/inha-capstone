"""Replay all five frozen methods and verify the separate validation set."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SOURCE = ROOT.parent / 'coverage-repair-v1'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    for manifest in ['method-freeze.json', 'frozen.json']:
        for name, digest in json.loads((ROOT / manifest).read_text()).items():
            if name != 'model_revision':
                assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == digest, name
    runner = load_module('verification_runner', SOURCE / 'run.py')
    ablation = load_module('verification_noop', SOURCE / 'ablation.py')
    benchmark = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    records = json.loads((ROOT / 'transcripts.json').read_text())
    expected_keys = {f'{name}-{i}' for name, turns in benchmark.items() for i in range(1, len(turns) + 1)}
    assert set(records) == expected_keys
    base = json.loads((ROOT / 'results.json').read_text())
    assert base['complete'] and base['actual_model_calls'] == 48
    noop = json.loads((ROOT / 'ablation-results.json').read_text())
    methods = dict(base['methods'], **noop['methods'])
    verified = {}
    for mode, result in methods.items():
        use_noop = mode.endswith('_noop_guard')
        base_mode = mode.replace('_noop_guard', '')
        rows, failures, dialogues = [], [], {}
        new_damage = 0
        for name, turns in benchmark.items():
            state, expected = dict(runner.INITIAL), dict(runner.INITIAL)
            joint = 0
            for i, turn in enumerate(turns, 1):
                record = records[f'{name}-{i}']
                assert record['request'] == turn['request']
                previous, old_expected = dict(state), dict(expected)
                raws = [record['first']] + ([] if base_mode == 'first_only' else [record[base_mode]['response']])
                if use_noop:
                    operations, _ = ablation.select_noop(raws, turn['request'], state)
                else:
                    operations, _, _ = runner.select(raws, turn['request'], base_mode == 'coverage')
                state = runner.apply_operations(state, operations, turn['request'])
                expected.update(turn['updates'])
                original = result['rows'][len(rows)]
                assert original['observed'] == state and original['expected'] == expected
                incorrect = [k for k in state if state[k] != expected[k]]
                new_damage += sum(old_expected[k] == expected[k] == previous[k] and state[k] != expected[k]
                                  for k in state)
                exact = not incorrect
                joint += exact
                rows.append({'exact': exact, 'correct_slots': 6 - len(incorrect)})
                if incorrect:
                    failures.append({'dialogue': name, 'turn': i, 'incorrect_slots': incorrect,
                                     'observed': dict(state), 'expected': dict(expected)})
            dialogues[name] = {'exact_turns': joint, 'final_exact': state == expected}
        exact = sum(r['exact'] for r in rows)
        correct = sum(r['correct_slots'] for r in rows)
        assert result['exact_turns'] == exact and result['correct_slots'] == correct
        verified[mode] = {'exact_turns': exact, 'correct_slots': correct,
                          'exact_final_dialogues': sum(d['final_exact'] for d in dialogues.values()),
                          'newly_corrupted_unchanged_slots': new_damage, 'by_dialogue': dialogues, 'failures': failures}
    names = {'first_only': '첫 출력', 'generic': '일반 재검토', 'coverage': '누락 검사 재검토',
             'first_only_noop_guard': '첫 출력 + 무변경 값 생략',
             'generic_noop_guard': '일반 재검토 + 무변경 값 생략'}
    lines = ['# 고정 방법의 별도 대화 검증', '',
             '2026-10-06. 개발 파일럿 이후 방법을 고정하고 별도 V1–V4 대화 16턴을 평가했다. '
             '실제 모델 호출 48회이며 코드 대조는 같은 출력을 재사용했다. '
             '모든 모델 입력에서 정답을 제외하고, 추론 완료 뒤 저장한 출력을 다시 적용해 검산했다.', '',
             '| 방법 | 전체 상태 정확 턴 | 항목 정확도 | 최종 대화 정확 | 새로 훼손한 미변경 항목 |',
             '| --- | --- | --- | --- | --- |']
    for mode, result in verified.items():
        lines.append(f'| {names[mode]} | {result["exact_turns"]}/16 | {result["correct_slots"]}/96 | '
                     f'{result["exact_final_dialogues"]}/4 | {result["newly_corrupted_unchanged_slots"]} |')
    lines += ['', '## 대화별 전체 상태 정확 턴', '', '| 방법 | V1 | V2 | V3 | V4 |', '| --- | --- | --- | --- | --- |']
    for mode, result in verified.items():
        lines.append('| ' + names[mode] + ' | ' + ' | '.join(str(result['by_dialogue'][name]['exact_turns']) + '/4'
                                                           for name in benchmark) + ' |')
    lines += ['', '## 해석 범위', '',
              '개발자가 작성한 제한 어휘 대화이며 독립 외부 사용자의 자료는 아니다. '
              '4개 대화·16턴에서의 차이로 효과를 확정하지 않는다. '
              '이미지 생성·얼굴 보존 효과는 이번 검증의 대상이 아니다.', '',
              '`ablation-results.json`의 posthoc 표시는 파일럿용 공통 생성기의 원래 필드다. '
              '이 추가 검증에서 무변경 값 생략 규칙은 method-freeze.json으로 추론 전에 고정했으며 '
              '이 데이터의 결과를 보고 변경하지 않았다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in ['method-freeze.json', 'frozen.json', 'transcripts.json', 'results.json',
                           'ablation-results.json', 'report.py']}
    verification = {'passed': True, 'noop_rule_frozen_before_inference': True,
                    'methods': verified, 'sha256': hashes}
    (ROOT / 'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
