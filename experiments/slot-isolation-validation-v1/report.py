"""Replay frozen outputs and apply the predeclared gate without new inference."""
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
    spec = importlib.util.spec_from_file_location('verified_isolation_validation', ROOT / 'run.py')
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
    candidate = results['isolated_restore']
    gate = all(candidate['exact_turns'] > results[mode]['exact_turns']
               and candidate['exact_final_dialogues'] >= results[mode]['exact_final_dialogues']
               and candidate['newly_corrupted_unchanged_slots'] <= results[mode]['newly_corrupted_unchanged_slots']
               for mode in ['baseline_restore', 'latest_atomic_restore'])
    names = {'baseline_restore': '기존 일괄 검증+복원 제약', 'latest_atomic_restore': '최신 패치 일괄 검증+복원 제약',
             'isolated_restore': '항목별 검증+복원 제약', 'isolated': '항목별 검증·복원 제약 없음',
             'first_isolated_restore': '첫 추출만·항목별 검증+복원 제약'}
    lines = ['# 항목별 오류 격리: 별도 O 대화 검증', '',
             '개발자 작성 8대화·32턴이다. 직접 추출과 일반 재검토의 실제 모델 호출은 총64회다. '
             '각 적용 방법은 같은 출력을 재사용한다. 첫 추출만 사용하는 대조는 요청당1회, 나머지는2회다. '
             '방법·대화·모델을 추론 전에 고정했고 모든 출력 저장 후 채점했다.', '',
             '| 방법 | 전체 상태 정확 턴 | 항목 정확 | 최종 대화 정확 | 새 미변경 항목 훼손 |',
             '| --- | --- | --- | --- | --- |']
    for mode, data in results.items():
        lines.append(f'| {names[mode]} | {data["exact_turns"]}/32 | {data["correct_slots"]}/192 | '
                     f'{data["exact_final_dialogues"]}/8 | {data["newly_corrupted_unchanged_slots"]} |')
    lines += ['', '## 대화별 정확 턴', '', '| 방법 | ' + ' | '.join(benchmark) + ' |',
              '| --- | ' + ' | '.join('---' for _ in benchmark) + ' |']
    for mode, data in results.items():
        lines.append('| ' + names[mode] + ' | ' + ' | '.join(str(sum(r['exact'] for r in data['rows'] if r['dialogue'] == name)) + '/4'
                                                          for name in benchmark) + ' |')
    lines += ['', '## 진행 판정', '',
              ('고정한 이미지 단계 진행 기준을 충족했다. 모든 O 대화의2턴·4턴과 두 원본을 사용한 64조건의 이미지 검증으로 진행한다.'
               if gate else '고정한 이미지 단계 진행 기준을 충족하지 못했다. O에서 후보가 성공했다고 선언하지 않는다. 오류 원인을 다음 개발로 넘긴다.'), '',
              '이 연구에서 여러 후보를 반복 개발했다. 이 결과는 제한 어휘·개발자 작성 대화·단일 모델의 검증이며, '
              '외부 사용자 표본이나 일반 우월성의 확증 결과가 아니다. 이미지 목표 충족과 얼굴 보존은 아직 별도 검증이 필요하다. '
              '모든 실패와 대화별 결과를 포함하며 턴을 독립 표본으로 세지 않는다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    verification = {'passed': True, 'advance_to_images': gate,
                    'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ['frozen.json', 'transcripts.json', 'results.json', 'report.py']}}
    (ROOT / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
