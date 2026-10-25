"""Verify frozen inputs and recompute all reported counts from raw responses."""
import hashlib
import json
from pathlib import Path

import run

ROOT = Path(__file__).resolve().parent
LABELS = {'baseline_restore': '기준 방법', 'keep_only': '유지 규칙만',
          'remove_only': '삭제 규칙만', 'keep_remove': '유지·삭제 결합'}


def main():
    frozen = json.loads((ROOT / 'frozen.json').read_text())
    for name, digest in frozen['sha256'].items():
        assert hashlib.sha256((run.REPO / name).read_bytes()).hexdigest() == digest, name
    assert frozen['histories'] == run.benchmark()
    records = json.loads((ROOT / 'transcripts.json').read_text())
    assert set(records) == {f'{name}-{i}' for name in frozen['histories'] for i in range(1, 5)}
    for name, turns in frozen['histories'].items():
        for i, turn in enumerate(turns, 1):
            record = records[f'{name}-{i}']
            assert record['request'] == turn['request']
            assert record['second_user'] == (turn['request'] + '\nProposed patch: ' + record['first']
                + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.')
            assert isinstance(record['second'], str)
    methods = run.source.score(frozen['histories'], records)
    baseline = methods['baseline_restore']['rows']
    for method in methods.values():
        method['new_errors_vs_baseline'] = sum(a['exact'] and not b['exact']
                                               for a, b in zip(baseline, method['rows'], strict=True))
    assert json.loads((ROOT / 'results.json').read_text()) == dict(
        complete=True, actual_model_calls=64, methods=methods)
    lines = ['# 동일한 편집 목표의 표현 변화 검사', '',
        '기존 재검증 대화 여덟 개의 목표를 유지하고 요청 32개의 표현을 바꾸었다. '
        '추출·재검토 응답 64개에 기존 규칙을 수정 없이 적용하였다. 인간 평가는 사용하지 않았다.', '',
        '| 방법 | 전체 상태 일치율 | 항목별 일치율 | 최종 상태 일치율 | 규칙 적용 후 새 오류 |',
        '| --- | --- | --- | --- | --- |']
    for mode, label in LABELS.items():
        r = methods[mode]
        lines.append(f"| {label} | {r['exact_turns']}/32 | {r['correct_slots']}/192 | "
                     f"{r['exact_final_dialogues']}/8 | {r['new_errors_vs_baseline']} |")
    lines += ['', '새 오류는 기준 방법의 전체 상태가 정답이었으나 해당 규칙을 적용한 뒤 틀린 요청 수다.', '',
              '## 대화별 전체 상태 일치', '', '| 방법 | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for mode, label in LABELS.items():
        counts = [str(sum(r['exact'] for r in methods[mode]['rows'] if r['dialogue'] == f'T{i}'))+'/4'
                  for i in range(1, 9)]
        lines.append('| ' + ' | '.join([label] + counts) + ' |')
    lines += ['', '## 규칙이 바꾼 요청', '']
    for a, b in zip(baseline, methods['keep_remove']['rows'], strict=True):
        if a['observed'] != b['observed']:
            lines += [f"### {a['dialogue']} 요청 {a['turn']}", '',
                      records[f"{a['dialogue']}-{a['turn']}"]['request'], '',
                      f"기준 전체 상태 일치: {a['exact']}, 결합 전체 상태 일치: {b['exact']}.", '']
    lines += ['## 측정 범위', '',
              '표현 변화 전후는 동일한 정답을 공유하는 대응 검사다. 기존 T와 표본 수를 따로 집계한다. '
              '개발자가 작성한 영어 요청과 한 종류의 추출 모델을 사용하였다. '
              '이 검사는 편집 상태 기록을 측정하며 이미지를 새로 생성하지 않았다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    paths = ['frozen.json', 'run.py', 'PROTOCOL.md', 'transcripts.json', 'results.json', 'RESULTS.md']
    run.source.save(ROOT / 'verification.json', {'passed': True, 'requests': 32, 'actual_model_calls': 64,
        'paired_with': 'isolated-contract-v1',
        'sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    print('\n'.join(lines[:12]))


if __name__ == '__main__':
    main()
