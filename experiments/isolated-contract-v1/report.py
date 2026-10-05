"""Replay and verify the complete frozen component interaction study."""
import hashlib
import json
from pathlib import Path
import run

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert json.loads((ROOT / 'frozen.json').read_text()) == {**run.frozen_files(), 'model_revision': run.base.REVISION}
    benchmark = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    records = json.loads((ROOT / 'transcripts.json').read_text())
    assert set(records) == {f'{n}-{i}' for n, ts in benchmark.items() for i in range(1, len(ts) + 1)}
    methods = run.score(benchmark, records)
    assert json.loads((ROOT / 'results.json').read_text()) == dict(complete=True, actual_model_calls=64, methods=methods)
    b, n = methods['baseline_restore'], methods['isolated_keep_remove']
    gate = (n['exact_turns'] > b['exact_turns'] and n['exact_final_dialogues'] >= b['exact_final_dialogues']
            and n['newly_corrupted_unchanged_slots'] <= b['newly_corrupted_unchanged_slots'])
    extra = all(n['exact_turns'] > methods[m]['exact_turns'] for m in ['isolated_restore', 'keep_remove'])
    lines = ['# 항목별 적용과 유지·삭제 결합의 T 검증', '',
             '새로 고정한 개발자 작성8대화·32턴·192항목이다. 현재 요청의 추출·재검토64호출을 모든 방법이 공유하고 각자의 이전 상태를 갱신했다. '
             '제한 어휘 스트레스 검사이며 외부 사용자 자료가 아니다.', '',
             '| 방법 | 전체 상태 | 항목 | 최종 대화 | 새 미변경 훼손 |', '| --- | --- | --- | --- | --- |']
    labels = {'baseline_restore': '공통 기준', 'isolated_restore': '항목별 적용',
              'keep_remove': '유지·삭제', 'isolated_keep_remove': '항목별 적용+유지·삭제'}
    for mode, row in methods.items():
        lines.append(f'| {labels[mode]} | {row["exact_turns"]}/32 | {row["correct_slots"]}/192 | {row["exact_final_dialogues"]}/8 | {row["newly_corrupted_unchanged_slots"]} |')
    lines += ['', f'사전 채택 기준 통과: {gate}. 두 단일 구성 각각보다 정확 턴이 많은지: {extra}.', '',
              '| 방법 | ' + ' | '.join(benchmark) + ' |', '| --- | ' + ' | '.join('---' for _ in benchmark) + ' |']
    for mode, row in methods.items():
        lines.append('| ' + labels[mode] + ' | ' + ' | '.join(str(sum(r['exact'] for r in row['rows'] if r['dialogue'] == d)) + '/4' for d in benchmark) + ' |')
    lines += ['', 'S의32/32는 사후 개발 결과로 별도 보존했다. T와 합산하지 않는다. 이미지 효과는 이 결과만으로 주장하지 않는다. '
              '기존 P·S 이미지 연구는 별도이며, 같은 대화의 여러 턴을 독립 표본으로 검정하지 않는다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    run.save(ROOT / 'verification.json', {'passed': True, 'adoption_gate_passed': gate,
                                         'advance_to_images': gate and extra,
                                         'combination_exceeds_each_component': extra,
                                         'sha256': {name: sha(ROOT / name) for name in ['frozen.json', 'transcripts.json', 'results.json', 'report.py', 'development-S.json']}})
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
