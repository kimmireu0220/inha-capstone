"""Verify the completed frozen pilot and report all methods without rerunning inference."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
spec = importlib.util.spec_from_file_location('coverage_pilot', ROOT / 'run.py')
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def main():
    frozen = json.loads((ROOT / 'frozen.json').read_text())
    for name, expected in frozen.items():
        if name != 'model_revision':
            assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == expected, name
    histories = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    records = json.loads((ROOT / 'transcripts.json').read_text())
    results = json.loads((ROOT / 'results.json').read_text())
    assert results['complete']
    expected_keys = {f'{name}-{i}' for name, turns in histories.items() for i in range(1, len(turns) + 1)}
    assert set(records) == expected_keys
    assert results['actual_model_calls'] == 3 * len(records)
    diagnostics = {}
    for mode, summary in results['methods'].items():
        correct = exact = changed_correct = changed_total = unchanged_wrong = newly_corrupted = final = 0
        by_dialogue = {}
        row_index = 0
        for name, turns in histories.items():
            observed, expected = dict(run.INITIAL), dict(run.INITIAL)
            dialogue_exact = 0
            for i, turn in enumerate(turns, 1):
                record = records[f'{name}-{i}']
                assert record['request'] == turn['request']
                before_expected, before_observed = dict(expected), dict(observed)
                expected.update(turn['updates'])
                raws = [record['first']] + ([] if mode == 'first_only' else [record[mode]['response']])
                operations, _, _ = run.select(raws, turn['request'], mode == 'coverage')
                observed = run.apply_operations(observed, operations, turn['request'])
                row = summary['rows'][row_index]
                row_index += 1
                assert row['dialogue'] == name and row['turn'] == i
                assert row['expected'] == expected and row['observed'] == observed
                correct += sum(observed[k] == expected[k] for k in expected)
                exact += observed == expected
                dialogue_exact += observed == expected
                for key in expected:
                    if expected[key] != before_expected[key]:
                        changed_total += 1
                        changed_correct += observed[key] == expected[key]
                    else:
                        unchanged_wrong += observed[key] != expected[key]
                        newly_corrupted += (before_observed[key] == before_expected[key]
                                            and observed[key] != expected[key])
            final += observed == expected
            by_dialogue[name] = {'exact_turns': dialogue_exact, 'turns': len(turns), 'final_exact': observed == expected}
        for key, value in [('correct_slots', correct), ('exact_turns', exact),
                           ('changed_correct', changed_correct), ('changed_total', changed_total),
                           ('unchanged_wrong', unchanged_wrong), ('exact_final_dialogues', final)]:
            assert summary[key] == value, (mode, key)
        diagnostics[mode] = {'newly_corrupted_unchanged_slots': newly_corrupted, 'by_dialogue': by_dialogue}
    baseline, candidate = (results['methods'][m] for m in ['generic', 'coverage'])
    advance = (candidate['exact_turns'] > baseline['exact_turns']
               and candidate['unchanged_wrong'] <= baseline['unchanged_wrong']
               and diagnostics['coverage']['newly_corrupted_unchanged_slots']
               <= diagnostics['generic']['newly_corrupted_unchanged_slots'])
    lines = ['# 언급 항목 누락 검사: 개발 파일럿 결과', '',
             '4개 개발자 작성 대화·16턴·상태 96항목을 평가했다. 실제 모델 호출은 48회다. '
             '일반 재검토와 누락 검사 재검토는 각각 턴당 2회(첫 호출 공유)를 사용했다. '
             '모든 출력 저장 후 고정 정답으로 채점했다.', '',
             '| 방법 | 전체 상태 정확 턴 | 항목 정확도 | 최종 대화 정확 | 변경 항목 정확 | 미변경 항목 오류 | 새로 훼손한 미변경 항목 | 배분 시간(초) |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    names = {'first_only': '재검토 없음', 'generic': '일반 재검토', 'coverage': '누락 검사 재검토'}
    for mode, summary in results['methods'].items():
        lines.append(f'| {names[mode]} | {summary["exact_turns"]}/16 | {summary["correct_slots"]}/96 | '
                     f'{summary["exact_final_dialogues"]}/4 | {summary["changed_correct"]}/{summary["changed_total"]} | '
                     f'{summary["unchanged_wrong"]} | {diagnostics[mode]["newly_corrupted_unchanged_slots"]} | {summary["seconds"]:.1f} |')
    lines += ['', '미변경 항목 오류에는 이전 턴에서 이어진 오류도 포함한다. 새로 훼손한 항목은 직전까지 맞았고 '
              '현재 요청에서 바뀌지 않은 항목을 이번 출력이 틀리게 만든 경우만 센다.', '', '## 판단', '',
              ('고정한 파일럿 진행 기준을 충족했다. 다음 단계는 방법을 고정한 별도 대화 검증이며, 아직 이미지 성공률 개선 근거는 아니다.'
               if advance else '고정한 파일럿 진행 기준을 충족하지 못했다. 이 후보의 개선 효과를 입증하지 못했으므로 이미지 생성 확대의 근거로 사용하지 않는다.'),
              '', '이 결과는 제한 어휘의 작은 개발 파일럿이다. 기존 논문의 이미지 실험과 합산하지 않으며 '
              '새 대화 일반화·얼굴 보존 개선·학술적 신규성을 입증한 것으로 해석하지 않는다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in ['frozen.json', 'transcripts.json', 'results.json', 'environment.json', 'report.py']}
    verification = {'passed': True, 'advance_to_heldout': advance, 'diagnostics': diagnostics, 'sha256': hashes}
    (ROOT / 'verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
