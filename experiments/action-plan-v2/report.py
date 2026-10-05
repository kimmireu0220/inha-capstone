"""Recompute the action/value development study without model calls."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def main():
    frozen = json.loads((ROOT / 'frozen.json').read_text())
    for name, expected in frozen.items():
        if name != 'model_revision':
            assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == expected, name
    spec = importlib.util.spec_from_file_location('verified_action', ROOT / 'method.py')
    method = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(method)
    result = json.loads((ROOT / 'results.json').read_text())
    records = json.loads((ROOT / 'transcripts.json').read_text())
    benchmark = json.loads((ROOT.parent / 'coverage-validation-v1/benchmark.json').read_text())['histories']
    expected_keys = {f'{name}-{i}' for name, turns in benchmark.items() for i in range(1, len(turns) + 1)}
    assert set(records) == expected_keys
    exact = correct = final = damage = index = 0
    for name, turns in benchmark.items():
        state, expected = dict(method.INITIAL), dict(method.INITIAL)
        for i, turn in enumerate(turns, 1):
            record = records[f'{name}-{i}']
            assert record['request'] == turn['request']
            old_state, old_expected = dict(state), dict(expected)
            state, errors = method.compile_update(state, turn['request'], record['plan'], record['values'])
            expected.update(turn['updates'])
            assert result['rows'][index]['observed'] == state
            assert result['rows'][index]['expected'] == expected
            assert result['rows'][index]['errors'] == errors
            index += 1
            exact += state == expected
            correct += sum(state[k] == expected[k] for k in state)
            damage += sum(old_state[k] == old_expected[k] == expected[k] and state[k] != expected[k] for k in state)
        final += state == expected
    assert result['complete'] and result['actual_model_calls'] == len(records) * 2
    assert (exact, correct, final, damage) == tuple(result[k] for k in
        ['exact_turns', 'correct_slots', 'exact_final_dialogues', 'newly_corrupted_unchanged_slots'])
    advance = exact > 13 and damage == 0
    text = f'''# 예시를 맞춘 동작 분리: 개발 결과

전체 상태 정확 {exact}/16, 항목 정확 {correct}/96, 최종 대화 정확 {final}/4, 새 미변경 항목 훼손 {damage}개다. 실제 모델 호출은 32회이며 원문은 transcripts.json에 보존했다.

같은 V 대화에서 일반 재검토+무변경 값 생략은 전체 상태 정확 13/16, 항목 정확 93/96이었다. 이 후보는 해당 실패를 보고 설계했으므로 이 차이는 개발 성능이지 새 대화 일반화 효과가 아니다.

고정한 추가 검증 진행 기준 충족: {str(advance).lower()}. 효과가 확인될 때까지 후보 실패 시 다음 개발 실험으로 이어가며, 이 파일의 작성은 전체 연구 완료를 뜻하지 않는다.
'''
    (ROOT / 'RESULTS.md').write_text(text)
    verification = {'passed': True, 'advance_to_frozen_validation': advance,
                    'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ['frozen.json', 'transcripts.json', 'results.json', 'report.py']}}
    (ROOT / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    print(text)


if __name__ == '__main__':
    main()
