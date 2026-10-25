"""Verify the paired structure study and report all cells, not selected examples."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import run

ROOT = Path(__file__).resolve().parent
LABELS = {'baseline_restore': '기준 방법', 'keep_remove': '기존 유지·삭제',
          'normalized_atomic': '구절 정규화', 'isolated_keep_remove': '항목별 적용',
          'normalized_isolated': '정규화+항목별 적용'}
FORM_LABELS = dict(separated='표준 분리 구절', leaving='leaving 연결',
                   preserving='preserving 연결', bring_back='bring back과 부정형 유지')


def main():
    frozen = json.loads((ROOT / 'frozen.json').read_text())
    for name, expected in frozen['sha256'].items():
        assert hashlib.sha256((run.REPO / name).read_bytes()).hexdigest() == expected, name
    histories = run.benchmark()
    assert frozen['histories'] == histories
    records = json.loads((ROOT / 'transcripts.json').read_text())
    assert set(records) == {f'{name}-{i}' for name in histories for i in range(1, 4)}
    for name, turns in histories.items():
        for i, turn in enumerate(turns, 1):
            record = records[f'{name}-{i}']
            assert record['request'] == turn['request']
            assert record['second_user'] == (turn['request'] + '\nProposed patch: ' + record['first']
                + '\nAudit this patch against the request. Correct errors; output a flat JSON patch only.')
    methods = run.core.score(histories, records)
    assert json.loads((ROOT / 'results.json').read_text()) == dict(
        complete=True, actual_model_calls=72, methods=methods)
    groups = {}
    for name, data in methods.items():
        groups[name] = {}
        for form in run.FORMS:
            rows = [r for r in data['rows'] if r['dialogue'].endswith('__'+form)]
            groups[name][form] = dict(exact_turns=sum(r['exact'] for r in rows), turns=len(rows),
                exact_target_requests=sum(r['exact'] for r in rows if r['turn'] == 2), target_requests=3,
                exact_followups=sum(r['exact'] for r in rows if r['turn'] == 3), followups=3)
    repeats = defaultdict(list)
    for record in records.values():
        repeats[record['request']].append((record['first'], record['second']))
    repeated = [dict(request=req, observations=len(responses), distinct_response_pairs=len(set(responses)))
                for req, responses in repeats.items() if len(responses) > 1]
    summary = dict(complete=True, actual_model_calls=72, dialogues=12, requests=36,
                   distinct_request_texts=len(repeats), target_configurations=3,
                   forms=groups, repeated_requests=repeated,
                   different_repeated_response_groups=sum(r['distinct_response_pairs'] > 1 for r in repeated))
    run.core.source.save(ROOT / 'summary.json', summary)
    lines = ['# 복원과 유지 구절의 문장 구조 대조', '',
        '세 가지 목표 구성을 네 가지 문장 구조로 요청하였다. 대화 12개·요청 36개에 대한 실제 추출·재검토 호출은 72회다. '
        '독립적인 목표 구성은 세 가지이며, 문장 구조 사이의 목표는 같다. 모든 방법은 같은 응답을 사용했다.', '',
        '| 방법 | 전체 상태 일치율 | 항목별 일치율 | 최종 상태 일치율 | 새 오류 수 |',
        '| --- | --- | --- | --- | --- |']
    for name, label in LABELS.items():
        r = methods[name]
        lines.append(f"| {label} | {r['exact_turns']}/36 | {r['correct_slots']}/216 | "
                     f"{r['exact_final_dialogues']}/12 | {r['new_errors_vs_baseline']} |")
    lines += ['', '## 복원과 유지가 함께 있는 두 번째 요청', '',
              '| 문장 구조 | 기준 방법 | 기존 유지·삭제 | 구절 정규화 | 항목별 적용 | 결합 |',
              '| --- | --- | --- | --- | --- | --- |']
    for form, label in FORM_LABELS.items():
        lines.append('| ' + ' | '.join([label]+[f"{groups[m][form]['exact_target_requests']}/3" for m in LABELS])+' |')
    lines += ['', '## 후속 요청 처리 후 전체 상태', '',
              '| 문장 구조 | 기준 방법 | 기존 유지·삭제 | 구절 정규화 | 항목별 적용 | 결합 |',
              '| --- | --- | --- | --- | --- | --- |']
    for form, label in FORM_LABELS.items():
        lines.append('| ' + ' | '.join([label]+[f"{groups[m][form]['exact_followups']}/3" for m in LABELS])+' |')
    lines += ['', '## 반복 호출 확인', '',
              f"요청 문장은 서로 다른 {len(repeats)}개다. 초기 설정과 후속 요청은 같은 항목 구성의 네 문장 구조에서 반복하였다. "
              f"같은 요청의 응답 쌍이 달랐던 그룹은 {summary['different_repeated_response_groups']}개다. "
              '반복 호출을 새로운 목표 구성으로 집계하지 않았다. 반복별 원문은 transcripts.json에 보존하였다.', '',
              '## 측정 범위', '',
              '코드와 요청을 고정한 뒤 수행한 지원 문법의 구조 대조다. 항목 구성이 다른 세 쌍의 대응 결과를 보여 주며, '
              '대화 12개를 서로 다른 사용자 12명의 관측으로 취급하지 않는다. '
              '상태 기록을 정답과 자동 대조하였다. 코드 수정과 새 이미지 생성은 없다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    names = ['run.py', 'PROTOCOL.md', 'frozen.json', 'transcripts.json', 'results.json', 'summary.json', 'RESULTS.md']
    run.core.source.save(ROOT / 'verification.json', dict(passed=True, requests=36, actual_model_calls=72,
        sha256={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names},
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print('\n'.join(lines[:14]))


if __name__ == '__main__':
    main()
