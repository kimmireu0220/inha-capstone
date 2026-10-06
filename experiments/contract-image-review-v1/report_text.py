"""Render completed review summaries without changing frozen experiment data."""
import hashlib
import json
from pathlib import Path
from run import parse

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads((ROOT / 'summary.json').read_text())
    verification = json.loads((ROOT / 'verification.json').read_text())
    assert data['complete'] and verification['passed']
    for name, digest in verification['sha256'].items():
        assert sha(ROOT / name) == digest
    raw_ratings = json.loads((ROOT / 'ai-ratings.json').read_text())['ratings']
    for rating in raw_ratings.values():
        scores, error = parse(rating['raw'])
        assert scores == rating['scores'] and error == rating['parse_error']
    primary_path = ROOT.parent / 'contract-image-v3/paired-audit.json'
    primary_verification = json.loads((ROOT.parent / 'contract-image-v3/verification.json').read_text())
    assert sha(primary_path) == primary_verification['sha256']['paired-audit.json']
    primary = json.loads(primary_path.read_text())
    labels = {'baseline_restore': '공통 기준', 'keep_remove': '유지·삭제'}
    lines = ['# S 이미지 평가의 대형 모델 민감도 분석', '',
             '1차 평가의 모순을 확인한 뒤 정한 사후 분석이다. 같은 계열의 더 큰 모델을 사용했으며 '
             '1차 결과를 대체하지 않는다. 128조건·66개 고유 이미지·68개 고유 출력–목표 쌍 전체를 평가했다.', '',
             '| 평가 모델 | 방법 | 목표 충족 | 판단 불가 | 6항목 모두 충족 |',
             '| --- | --- | --- | --- | --- |']
    for model, stats in [('3B 1차', data['primary_by_mode']), ('7B 후속', data['by_mode'])]:
        for mode, row in stats.items():
            lines.append(f'| {model} | {labels[mode]} | {row["goals_satisfied"]}/{row["goal_denominator"]} | '
                         f'{row["unknown_goals"]} | {row["all_six_satisfied"]}/{row["conditions"]} |')
    lines += ['', f'7B JSON 파싱 실패: {data["parse_failures"]}/68. 판단 불가를 성공으로 세지 않았다.', '',
              '## 입력이 달랐던 네 쌍', '',
              '| 인물·대화·턴 | 3B 기준→유지·삭제 | 7B 기준→유지·삭제 | 7B 판단 불가 기준→유지·삭제 |',
              '| --- | --- | --- | --- |']
    key = lambda p: (p['person'], p['history'], p['turn'])
    lookup = {key(p): p for p in primary['pairs']}
    for pair in data['pairs']['pairs']:
        if pair['same_input_job']:
            continue
        old = lookup[key(pair)]
        a, b = old['goal_counts']
        c, d = pair['goal_counts']
        x, y = pair['unknown_counts']
        lines.append(f'| {pair["person"]} {pair["history"]} {pair["turn"]}턴 | {a}/6→{b}/6 | {c}/6→{d}/6 | {x}→{y} |')
    lines += ['', '| 항목 점수 변화 | 3B | 7B |', '| --- | --- | --- |']
    before, after = data['primary_changed_pair_transitions'], data['changed_pair_transitions']
    for transition in sorted(set(before) | set(after)):
        lines.append(f'| {transition} | {before.get(transition, 0)} | {after.get(transition, 0)} |')
    lines += ['', '위 변화는 네 쌍×6항목의 24개 대응 점수다. unknown은 판단 불가이며 확정 실패와 구별한다.', '',
              '## 평가 간 일치', '',
              '| 집계 단위 | 전체 판정 | 판단 불가 포함 일치 | 둘 다 판정 가능 | 둘 다 판정 가능할 때 일치 |',
              '| --- | --- | --- | --- | --- |']
    for name, field in [('고유 출력·목표 입력', 'unique_input_agreement'), ('공유 출력을 포함한 조건', 'condition_agreement')]:
        a = data[field]
        lines.append(f'| {name} | {a["decisions"]} | {a["same_including_unknown"]} | '
                     f'{a["both_known"]} | {a["same_when_both_known"]} |')
    lines += ['', '공유 출력 60쌍은 독립 반복이 아니다. 얼굴 지표는 기존 측정을 재사용했으며 새로 평가하지 않았다. '
              '두 AI의 일치가 정답을 보장하지 않으며 원응답의 모순도 보존한다. 제한된 합성 대화·두 인물·한 생성 도구의 사례 분석이다.', '']
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines))
    (ROOT / 'report-verification.json').write_text(json.dumps({
        'summary_sha256': sha(ROOT / 'summary.json'), 'report_sha256': sha(ROOT / 'RESULTS.md'),
        'script_sha256': sha(Path(__file__))}, indent=2) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
