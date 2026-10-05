"""Verify P provenance, replay every row and evaluate the frozen progression rule."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def main():
    for name, digest in json.loads((ROOT / 'frozen.json').read_text()).items():
        if name != 'model_revision':
            assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == digest, name
    spec = importlib.util.spec_from_file_location('verified_keep_validation', ROOT / 'run.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    benchmark = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    records = json.loads((ROOT / 'transcripts.json').read_text())
    assert set(records) == {f'{name}-{i}' for name, turns in benchmark.items() for i in range(1, len(turns) + 1)}
    for name, turns in benchmark.items():
        for i, turn in enumerate(turns, 1):
            assert records[f'{name}-{i}']['request'] == turn['request']
    saved = json.loads((ROOT / 'results.json').read_text())
    results = runner.score(benchmark, records)
    assert saved['complete'] and saved['methods'] == results and saved['actual_model_calls'] == 64
    candidate = results['isolated_restore_keep']
    gate = all(candidate['exact_turns'] > results[mode]['exact_turns']
               and candidate['exact_final_dialogues'] >= results[mode]['exact_final_dialogues']
               and candidate['newly_corrupted_unchanged_slots'] <= results[mode]['newly_corrupted_unchanged_slots']
               for mode in ['baseline_restore', 'baseline_restore_keep'])
    names = {'baseline_restore': '기존 일괄 검증+복원', 'baseline_restore_keep': '기존 일괄 검증+복원·유지',
             'isolated_restore': '항목별 검증+복원', 'isolated_restore_keep': '항목별 검증+복원·유지',
             'latest_atomic_restore_keep': '최신 패치 일괄 검증+복원·유지',
             'first_isolated_restore_keep': '첫 추출만·항목별 검증+복원·유지'}
    lines = ['# 유지 보호·항목별 검증: 새 P 대화 결과', '',
             '새 개발자 작성8대화·32턴·192항목이다. 실제 모델 호출은64회이며 같은 직접 추출·일반 재검토 응답을 '
             '모든 코드 대조에 사용했다. 첫 추출 대조는 요청당1회, 나머지는2회다. '
             '방법·모델·대화의 추론 전 해시와 원문 응답을 보존하고 전체 추론 완료 후 채점했다.', '',
             '| 방법 | 전체 상태 정확 | 항목 정확 | 최종 대화 정확 | 새 미변경 훼손 |',
             '| --- | --- | --- | --- | --- |']
    for mode, data in results.items():
        lines.append(f'| {names[mode]} | {data["exact_turns"]}/32 | {data["correct_slots"]}/192 | '
                     f'{data["exact_final_dialogues"]}/8 | {data["newly_corrupted_unchanged_slots"]} |')
    lines += ['', '## 대화별 전체 상태 정확', '', '| 방법 | ' + ' | '.join(benchmark) + ' |',
              '| --- | ' + ' | '.join('---' for _ in benchmark) + ' |']
    for mode, data in results.items():
        lines.append('| ' + names[mode] + ' | ' + ' | '.join(str(sum(r['exact'] for r in data['rows'] if r['dialogue'] == name)) + '/4'
                                                          for name in benchmark) + ' |')
    lines += ['', '## 고정 진행 기준', '',
              ('주 후보가 두 대조보다 전체 상태 정확도가 높고 최종 대화·미변경 훼손에서 악화되지 않았다. '
               '모든32턴과 두 인물·두 방법의128조건 이미지 입력을 준비한다.' if gate else
               '결합 방법의 추가 효과를 인정하는 고정 진행 기준을 충족하지 못했다. 이 후보를 확정된 해결책으로 채택하지 않는다. '
               '효과가 있는 구성요소와 남은 의미 오류를 구분하여 다음 개발로 이어간다.'), '',
              '여러 후보의 반복 개발 이후 수행한 제한된 검증이며 실제 사용자 표본·외부 데이터 검증이 아니다. '
              '대화 안의 턴을 독립 표본으로 세지 않는다. 방법별 이미지 개선은 별도 검증 전 주장하지 않는다. '
              '원본 복원·유지 규칙은 범용 의미 해석기가 아니며, 항목 간 조건부 의존성의 안전한 실행을 보장하지 않는다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    verification = {'passed': True, 'advance_to_images': gate,
                    'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ['frozen.json', 'transcripts.json', 'results.json', 'report.py']}}
    (ROOT / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
