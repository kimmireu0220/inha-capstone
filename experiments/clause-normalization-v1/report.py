"""Recompute held-out and explicitly labeled development results, with hashes."""
import hashlib
import json
from pathlib import Path

import run

ROOT = Path(__file__).resolve().parent
LABELS = {'baseline_restore': '기준 방법', 'keep_remove': '기존 유지·삭제',
          'normalized_atomic': '구절 정규화', 'isolated_keep_remove': '항목별 적용',
          'normalized_isolated': '정규화+항목별 적용'}


def compact(methods):
    return {k: {name: value for name, value in data.items() if name != 'rows'}
            for k, data in methods.items()}


def main():
    frozen = json.loads((ROOT / 'frozen.json').read_text())
    assert frozen == json.loads(json.dumps(run.freeze()))
    records = json.loads((ROOT / 'transcripts.json').read_text())
    histories = json.loads((ROOT / 'benchmark.json').read_text())['histories']
    assert set(records) == {f'{name}-{i}' for name in histories for i in range(1, 5)}
    for name, turns in histories.items():
        for i, turn in enumerate(turns, 1):
            record = records[f'{name}-{i}']
            assert record['request'] == turn['request']
            assert record['second_user'] == (turn['request'] + '\nProposed patch: ' + record['first']
                + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.')
    methods = run.score(histories, records)
    assert json.loads((ROOT / 'results.json').read_text()) == dict(
        complete=True, actual_model_calls=32, methods=methods)
    sources, development = {}, {}
    for study in ['paraphrase-contract-v1', 'request-contract-v3', 'isolated-contract-v1']:
        folder = ROOT.parent / study
        benchmark_path = folder / ('frozen.json' if study == 'paraphrase-contract-v1' else 'benchmark.json')
        bench = json.loads(benchmark_path.read_text())['histories']
        transcript_path = folder / 'transcripts.json'
        transcripts = json.loads(transcript_path.read_text())
        development[study] = compact(run.score(bench, transcripts))
        for path in [benchmark_path, transcript_path]:
            sources[str(path.relative_to(run.method.source.REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
    run.source.save(ROOT / 'development-replay.json', dict(posthoc_development=True,
        additional_model_calls=0, sources_sha256=sources, studies=development))
    lines = ['# 지시 구절 정규화와 항목별 적용의 새 대화 검증', '',
        '코드와 정답을 고정한 뒤 새 대화 네 개·요청 16개를 추론하였다. '
        '실제 모델 응답 32개를 모든 방법이 공유한다. 각 방법의 이전 상태를 누적한다.', '',
        '| 방법 | 전체 상태 일치율 | 항목별 일치율 | 최종 상태 일치율 | 새 오류 |',
        '| --- | --- | --- | --- | --- |']
    for mode, label in LABELS.items():
        r = methods[mode]
        lines.append(f"| {label} | {r['exact_turns']}/16 | {r['correct_slots']}/96 | "
                     f"{r['exact_final_dialogues']}/4 | {r['new_errors_vs_baseline']} |")
    lines += ['', '새 오류는 기준 방법이 맞았으나 해당 방법 적용 후 틀린 요청 수다.', '',
              '## 대화별 전체 상태 일치', '', '| 방법 | V1 | V2 | V3 | V4 |', '| --- | --- | --- | --- | --- |']
    for mode, label in LABELS.items():
        counts = [str(sum(r['exact'] for r in methods[mode]['rows'] if r['dialogue'] == f'V{i}'))+'/4'
                  for i in range(1, 5)]
        lines.append('| ' + ' | '.join([label]+counts) + ' |')
    lines += ['', '## 개발 자료 재계산', '',
              '아래 자료는 이미 관찰한 자료이며 추가 모델 호출 없이 재계산하였다. 새 대화 검증과 따로 집계한다.', '',
              '| 자료 | 기준 방법 | 기존 유지·삭제 | 구절 정규화 | 항목별 적용 | 정규화+항목별 적용 |',
              '| --- | --- | --- | --- | --- | --- |']
    for study, data in development.items():
        lines.append('| ' + ' | '.join([study] + [f"{data[m]['exact_turns']}/32" for m in LABELS]) + ' |')
    lines += ['', '## 기준과 결합 방법의 차이', '']
    for a, b in zip(methods['baseline_restore']['rows'], methods['normalized_isolated']['rows'], strict=True):
        if a['observed'] != b['observed']:
            lines += [f"### {a['dialogue']} 요청 {a['turn']}", '', records[f"{a['dialogue']}-{a['turn']}"]['request'], '',
                      f"기준 전체 상태 일치: {a['exact']}, 결합 전체 상태 일치: {b['exact']}.", '',
                      '정규화 기록: ' + json.dumps(b['trace']['normalization'], ensure_ascii=False), '']
    lines += ['## 측정 범위', '',
              '개발자가 작성한 영어 요청, 여섯 상태 항목, 한 종류의 추출 모델을 사용했다. '
              '표본 단위는 대화 네 개이며 같은 대화의 요청을 독립 표본처럼 통계 검정하지 않았다. '
              '검사 대상은 상태 기록이며, 새 이미지 생성과 인간 평가는 수행하지 않았다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    names = ['run.py', 'method.py', 'benchmark.json', 'PROTOCOL.md', 'test_method.py', 'frozen.json',
             'transcripts.json', 'results.json', 'development-replay.json', 'RESULTS.md']
    run.source.save(ROOT / 'verification.json', dict(passed=True, requests=16, actual_model_calls=32,
        sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names},
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print('\n'.join(lines[:14]))


if __name__ == '__main__':
    main()
