"""Verify frozen S inputs and all four own-state trajectories."""
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
    assert set(records) == {f'{name}-{i}' for name, turns in benchmark.items() for i in range(1, len(turns) + 1)}
    saved = json.loads((ROOT / 'results.json').read_text())
    methods = run.score(benchmark, records)
    assert saved == {'complete': True, 'actual_model_calls': 64, 'methods': methods}
    base, new = methods['baseline_restore'], methods['keep_remove']
    gate = (new['exact_turns'] > base['exact_turns'] and new['exact_final_dialogues'] >= base['exact_final_dialogues']
            and new['newly_corrupted_unchanged_slots'] <= base['newly_corrupted_unchanged_slots'])
    additional = all(new['exact_turns'] > methods[mode]['exact_turns'] for mode in ['keep_only', 'remove_only'])
    names = {'baseline_restore': '공통 기준', 'keep_only': '유지 보호만', 'remove_only': '삭제 실행만', 'keep_remove': '유지·삭제 결합'}
    lines = ['# 유지·삭제 제약의 새 S 대화 검증', '',
             '개발자 작성 8대화·32턴·192항목, 실제 모델 호출64회다. 모든 방법은 동일한 모델 응답을 사용하며 자기 이전 상태를 갱신했다. '
             '여러 후보를 개발한 뒤 고정한 제한 문형 스트레스 검사이며 외부 사용자 자료가 아니다.', '',
             '| 방법 | 전체 상태 정확 | 항목 정확 | 최종 대화 정확 | 새 미변경 훼손 |',
             '| --- | --- | --- | --- | --- |']
    for mode, row in methods.items():
        lines.append(f'| {names[mode]} | {row["exact_turns"]}/32 | {row["correct_slots"]}/192 | {row["exact_final_dialogues"]}/8 | {row["newly_corrupted_unchanged_slots"]} |')
    lines += ['', f'사전 채택 기준 충족: {gate}. 결합 방식이 두 단일 구성요소 각각보다 정확 턴이 많은지: {additional}.', '',
              '| 방법 | ' + ' | '.join(benchmark) + ' |', '| --- | ' + ' | '.join('---' for _ in benchmark) + ' |']
    for mode, row in methods.items():
        lines.append('| ' + names[mode] + ' | ' + ' | '.join(str(sum(r['exact'] for r in row['rows'] if r['dialogue'] == d)) + '/4' for d in benchmark) + ' |')
    lines += ['', '## 해석 범위', '',
              '형식과 제한된 어휘 검사를 포함한 시스템 비교다. 알려진 영어 문형에 대한 보조 규칙이고 일반적인 의미 이해 알고리즘이 아니다. '
              '정답 상태는 생성에 제공하지 않는다. 이전 상태가 이미 잘못됐거나 조건부·대명사·범위 밖 표현이면 오류가 남을 수 있다. '
              '이미지 개선은 별도 검증 전 주장하지 않으며 같은 대화의 여러 턴을 독립 표본으로 세지 않는다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    run.save(ROOT / 'verification.json', {'passed': True, 'adoption_gate_passed': gate, 'advance_to_images': gate,
                                        'combination_exceeds_each_component': additional,
                                        'sha256': {name: sha(ROOT / name) for name in ['frozen.json', 'transcripts.json', 'results.json', 'report.py', 'development-P.json', 'development-Q.json']}})
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
