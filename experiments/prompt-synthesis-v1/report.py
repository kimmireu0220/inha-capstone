"""Join method labels only after blinded goal scoring is saved."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODES = ['history', 'state', 'agent']

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    result = json.loads((ROOT / 'results.json').read_text())
    rating = json.loads((ROOT / 'blind-ratings.json').read_text())
    mapping = json.loads((ROOT / 'blinding-map.json').read_text())
    audit = json.loads((ROOT / 'prompt-audit.json').read_text())
    assert result['complete'] and len(result['rows']) == 12
    assert len(rating['rubric_order']) == 6 and len(rating['ratings']) == 4
    rows = []
    for person in ['R01', 'R02']:
        for seed in [42, 314]:
            key = f'{person}-{seed}'
            labels = mapping[key]
            scores = rating['ratings'][key]
            assert set(labels.values()) == set(MODES)
            for letter in ['A', 'B', 'C']:
                values = scores[letter]
                assert len(values) == 6 and all(v in (0, 1, None) for v in values)
                mode = labels[letter]
                source = next(r for r in result['rows'] if r['person'] == person and
                    r['seed'] == seed and r['mode'] == mode)
                rows.append({'person': person, 'seed': seed, 'mode': mode,
                    'goal_score': sum(v for v in values if v is not None),
                    'uncertain_items': sum(v is None for v in values),
                    'identity_similarity': source['identity_similarity'],
                    'blind_note': scores['note']})
    totals = {mode: sum(r['goal_score'] for r in rows if r['mode'] == mode) for mode in MODES}
    per_person = {person: {mode: {'goal_score': sum(r['goal_score'] for r in rows
        if r['person'] == person and r['mode'] == mode),
        'mean_identity_similarity': result['per_person'][person][mode]}
        for mode in MODES} for person in ['R01', 'R02']}
    assert all(audit[mode]['final_targets_present'] == 6 for mode in MODES)
    joined = {'complete': True, 'people': 2, 'seeds_per_person': 2,
        'outputs': 12, 'final_goal_items_per_output': 6,
        'goal_totals_out_of_24': totals, 'per_person': per_person,
        'rows': rows, 'prompt_audit': audit,
        'blinded_evaluation': 'single operator; method labels hidden until ratings saved'}
    save(ROOT / 'joined-results.json', joined)
    lines = ['# 편집 대화 최종 요구 종합 실험', '',
        '상태: 완료 · 실제 인물 2명 × 시드 2개 × 방법 3개 = 새 출력 12장 · 4개 비교 세트', '',
        '| 인물 | 시드 | 전체 대화 목표/6 | 상태 정리 목표/6 | 에이전트 목표/6 |',
        '| --- | ---: | ---: | ---: | ---: |']
    for person in ['R01', 'R02']:
        for seed in [42, 314]:
            scores = {r['mode']: r['goal_score'] for r in rows
                      if r['person'] == person and r['seed'] == seed}
            lines.append(f"| {person} | {seed} | {scores['history']} | {scores['state']} | {scores['agent']} |")
    lines.extend(['', f"최신 목표 6개 반영 점수는 전체 대화 {totals['history']}/24, "
        f"구조화 상태 정리 {totals['state']}/24, 에이전트 종합 {totals['agent']}/24였다. "
        '전체 대화 조건에서는 이전 목걸이·원형 핀·남색 재킷이 일부 출력에 남았다. '
        '에이전트는 텍스트 단계에서 최신 조건 6개를 모두 남기고 이전 조건 4개를 제거했다.',
        '', '| 인물 | 전체 대화 얼굴 유사도 ↑ | 상태 정리 얼굴 유사도 ↑ | 에이전트 얼굴 유사도 ↑ |',
        '| --- | ---: | ---: | ---: |'])
    for person in ['R01', 'R02']:
        p = per_person[person]
        lines.append(f"| {person} | {p['history']['mean_identity_similarity']:.6f} | "
            f"{p['state']['mean_identity_similarity']:.6f} | "
            f"{p['agent']['mean_identity_similarity']:.6f} |")
    lines.extend(['', '요청 반영과 얼굴 보존은 서로 다른 결과였다. 에이전트 종합은 이 작은 표본에서 목표 점수가 가장 높았지만, 얼굴 유사도는 두 인물 모두 전체 대화보다 낮았고 R02에서는 크게 낮았다. 일부 출력은 얼굴 표정·구도·자세도 눈에 띄게 바뀌었다. 따라서 “종합이 전반적으로 더 좋다”고 결론 내릴 수 없다.',
        '', '구조화 상태 정리는 각 요청의 의미를 사람이 미리 정확히 기록한 상한 기준이다. 에이전트와 입력 준비 비용이 같지 않다. 금색 핀의 사각형 여부 등 육안 점수에는 한 평가자의 판단이 포함된다. 인물 2명·각 2시드의 탐색적 자료이며 일반화나 유의성 검정은 하지 않는다.',
        '', '[실험 조건](PROTOCOL.md) · [원문 이력](history.json) · [프롬프트 사전 점검](prompt-audit.json) · [가림 평가 기준](EVALUATION.md) · [가림 점수](blind-ratings.json) · [전체 결과](joined-results.json) · [검증](verification.json)',
        '', '비교판: [R01·42](blind/R01-42.png), [R01·314](blind/R01-314.png), [R02·42](blind/R02-42.png), [R02·314](blind/R02-314.png)'])
    (ROOT / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'goal_totals': totals, 'per_person': per_person}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
