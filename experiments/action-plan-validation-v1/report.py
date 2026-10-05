"""Verify frozen inference inputs, replay the validation, and apply the declared gate."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def main():
    for name, expected in json.loads((ROOT / 'frozen.json').read_text()).items():
        if name != 'model_revision':
            assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == expected, name
    spec = importlib.util.spec_from_file_location('action_validation_verifier', ROOT / 'run.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    benchmark = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    records = json.loads((ROOT / 'transcripts.json').read_text())
    expected_keys = {f'{name}-{i}-{mode}' for name, turns in benchmark.items()
                     for i in range(1, len(turns) + 1) for mode in ['generic', 'action']}
    assert set(records) == expected_keys
    for name, turns in benchmark.items():
        for i, turn in enumerate(turns, 1):
            for mode in ['generic', 'action']:
                assert records[f'{name}-{i}-{mode}']['request'] == turn['request']
    saved = json.loads((ROOT / 'results.json').read_text())
    recomputed = runner.score(benchmark, records)
    assert saved['complete'] and saved['methods'] == recomputed
    assert saved['actual_model_calls'] == len(records) * 2 == 96
    candidate = recomputed['action']
    controls = [recomputed[m] for m in ['generic', 'generic_noop']]
    gate = all(candidate['exact_turns'] > baseline['exact_turns']
               and candidate['exact_final_dialogues'] >= baseline['exact_final_dialogues']
               and candidate['newly_corrupted_unchanged_slots'] <= baseline['newly_corrupted_unchanged_slots']
               for baseline in controls)
    names = {'first_only': '첫 출력', 'generic': '일반 재검토', 'generic_noop': '일반 재검토+무변경 값 생략',
             'action': '동작 분리·항목별 거부', 'action_atomic': '동작 분리·일괄 거부'}
    lines = ['# 동작 분리의 새 대화 고정 검증', '',
             '6개 개발자 작성 대화·24턴·상태 144항목. 각 추론 방법은 턴당 2회 호출했고 실제 호출 총 96회를 저장했다. '
             '모든 결과를 저장한 뒤 고정한 정답으로 채점했다. N 대화의 결과를 본 뒤 방법을 수정하지 않았다.', '',
             '| 방법 | 전체 상태 정확 턴 | 항목 정확도 | 최종 대화 정확 | 새 미변경 항목 훼손 |',
             '| --- | --- | --- | --- | --- |']
    for mode, data in recomputed.items():
        lines.append(f'| {names[mode]} | {data["exact_turns"]}/24 | {data["correct_slots"]}/144 | '
                     f'{data["exact_final_dialogues"]}/6 | {data["newly_corrupted_unchanged_slots"]} |')
    lines += ['', '## 대화별 전체 상태 정확 턴', '',
              '| 방법 | ' + ' | '.join(benchmark) + ' |', '| --- | ' + ' | '.join('---' for _ in benchmark) + ' |']
    for mode, data in recomputed.items():
        counts = [str(sum(r['exact'] for r in data['rows'] if r['dialogue'] == name)) + '/4' for name in benchmark]
        lines.append('| ' + names[mode] + ' | ' + ' | '.join(counts) + ' |')
    operation_scores = {}
    for mode, data in recomputed.items():
        counts = {key: {'correct': 0, 'total': 0} for key in ['set', 'remove', 'reset', 'unchanged']}
        previous = {name: dict(runner.action.INITIAL) for name in benchmark}
        for row in data['rows']:
            name = row['dialogue']
            for slot, expected in row['expected'].items():
                category = ('unchanged' if previous[name][slot] == expected else
                            'reset' if expected == 'original' else 'remove' if expected == 'none' else 'set')
                counts[category]['total'] += 1
                counts[category]['correct'] += row['observed'][slot] == expected
            previous[name] = row['expected']
        operation_scores[mode] = counts
    lines += ['', '## 사전 진행 기준', '',
              ('두 일반 재검토 대조보다 전체 상태 정확도가 높고 최종 대화·미변경 훼손에서 악화되지 않아 이미지 단계로 진행한다.'
               if gate else '이미지 단계 진행 기준을 충족하지 못했다. 이 후보를 유효한 해결책으로 채택하지 않고 오류를 분석해 다음 개발 단계로 이어간다.'),
              '', '한 생성 모델의 제한 어휘·개발자 작성 대화에서의 검사다. 턴을 독립 표본으로 계산하지 않는다. '
              '동작 분리 원리는 선행 연구가 있으며 새 알고리즘 최초 제안으로 주장하지 않는다. '
              '현재 결과만으로 이미지 성공률·얼굴 보존 효과를 주장하지 않는다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in ['frozen.json', 'transcripts.json', 'results.json', 'report.py']}
    (ROOT / 'verification.json').write_text(json.dumps({'passed': True, 'advance_to_images': gate,
        'operation_scores': operation_scores, 'sha256': hashes}, ensure_ascii=False, indent=2) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
