"""Replay Q and the post-hoc P diagnostic; never rewrite inference."""
import hashlib
import json
from pathlib import Path
import run

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    frozen = json.loads((ROOT / 'frozen.json').read_text())
    assert frozen == {**run.frozen_files(), 'model_revision': run.base.REVISION}
    benchmark = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    records = json.loads((ROOT / 'transcripts.json').read_text())
    assert set(records) == {f'{name}-{i}' for name, turns in benchmark.items() for i in range(1, len(turns) + 1)}
    result = json.loads((ROOT / 'results.json').read_text())
    assert result['complete'] and result['actual_model_calls'] == 64
    methods = run.score(benchmark, records)
    assert result['methods'] == methods
    base, old, new = [methods[m] for m in ['baseline_restore', 'keep_v1', 'keep_v2']]
    gate = (new['exact_turns'] >= base['exact_turns'] and new['exact_turns'] > old['exact_turns']
            and new['newly_corrupted_unchanged_slots'] <= base['newly_corrupted_unchanged_slots']
            and new['exact_final_dialogues'] >= base['exact_final_dialogues'])
    proot = ROOT.parent / 'keep-contract-validation-v1'
    preplay = run.score(json.loads((proot / 'benchmark.json').read_text())['histories'],
                       json.loads((proot / 'transcripts.json').read_text()))
    assert json.loads((ROOT / 'development-P.json').read_text())['methods'] == preplay
    p_equal = all(a['observed'] == b['observed'] for a, b in zip(preplay['keep_v1']['rows'], preplay['keep_v2']['rows']))
    lines = ['# 불변 절로 범위를 좁힌 보호 규칙의 Q 검증', '',
             '새 개발자 작성 8대화·32턴, 고정 Qwen 모델 64회 호출이다. 세 방법은 같은 응답을 사용하고 자기 이전 상태만 참조했다. '
             '지원·비지원 표현을 섞은 스트레스 검사이며 실제 사용자 표현 빈도를 대표하지 않는다.', '',
             '| 방법 | 전체 상태 정확 | 항목 정확 | 최종 대화 정확 | 새 미변경 훼손 | 보호 항목 개입 |',
             '| --- | --- | --- | --- | --- | --- |']
    for name, row in methods.items():
        lines.append(f'| {name} | {row["exact_turns"]}/32 | {row["correct_slots"]}/192 | '
                     f'{row["exact_final_dialogues"]}/8 | {row["newly_corrupted_unchanged_slots"]} | {row["protected_field_events"]} |')
    lines += ['', f'사전 채택 기준 충족: {gate}. 무보호보다 정확 턴·최종 대화·새 훼손에서 나빠지지 않으면서 v1보다 정확 턴이 높아야 한다.', '',
              '## 대화별 정확 턴', '', '| 방법 | ' + ' | '.join(benchmark) + ' |',
              '| --- | ' + ' | '.join('---' for _ in benchmark) + ' |']
    for name, row in methods.items():
        lines.append('| ' + name + ' | ' + ' | '.join(str(sum(r['exact'] for r in row['rows'] if r['dialogue'] == d)) + '/4' for d in benchmark) + ' |')
    lines += ['', f'P의 사후 개발 재계산에서는 v1·v2의 모든 관측 상태가 같은지 확인했다: {p_equal}. '
              'P 이미지 실험은 v1에 대해 시작한 탐색 실험이며 이 재계산을 v2의 새 이미지 검증으로 부르지 않는다.', '',
              '보호 규칙은 제한된 영어 문형만 지원한다. 지원하지 않는 표현에서 개입하지 않는 것이 의미 추출의 성공을 보장하지 않는다. '
              '원본 복원 제약 등 공통 기반의 오류도 남을 수 있다. 새 데이터·다른 모델의 일반화 또는 통계적 우월성을 주장하지 않는다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    run.save(ROOT / 'verification.json', {'passed': True, 'adoption_gate_passed': gate,
                                        'P_observed_states_identical': p_equal,
                                        'sha256': {name: sha(ROOT / name) for name in ['frozen.json', 'transcripts.json', 'results.json', 'development-P.json', 'report.py']}})
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
