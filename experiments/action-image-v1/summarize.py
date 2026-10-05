"""Descriptive image results; repeated conditions are not independent samples."""
import json
from pathlib import Path
import statistics
import sys
from evaluate import packet, save, sha


def aggregate(rows):
    scores = [value for row in rows for value in row['scores']]
    faces = [row['identity_similarity'] for row in rows if row['identity_similarity'] is not None]
    return {'conditions': len(rows), 'goals_satisfied': sum(value == 1 for value in scores),
            'goal_denominator': len(scores), 'unknown_goals': sum(value is None for value in scores),
            'all_six_satisfied': sum(all(value == 1 for value in row['scores']) for row in rows),
            'face_detectable': len(faces), 'face_mean': statistics.mean(faces) if faces else None,
            'unique_jobs': len({row['job'] for row in rows}),
            'unique_rgb_images': len({row['rgb_sha256'] for row in rows})}


def main():
    root = Path(sys.argv[1]).resolve()
    data = packet(root)
    assert json.loads((root / 'evaluation-plan.json').read_text()) == data
    ratings = json.loads((root / 'ai-ratings.json').read_text())
    assert ratings['inputs']['evaluation_plan_sha256'] == sha(root / 'evaluation-plan.json')
    assert set(ratings['ratings']) == set(data['items']), 'AI ratings incomplete'
    measured = json.loads((root / 'face-results.json').read_text())
    for name, digest in measured['input_sha256'].items():
        assert sha(root / name) == digest
    preflight = json.loads((root / 'feasibility-preflight.json').read_text())
    assert preflight['prepared_sha256'] == sha(root / 'prepared.json')
    assert preflight['conditions_excluded'] == 0
    flags = {r['id']: r['target_flags'] for r in preflight['rows']}
    rows = [{**row, 'scores': ratings['ratings'][data['mapping'][row['id']]]['scores'],
             'target_flags': flags[row['id']]} for row in measured['rows']]
    assert {row['id'] for row in rows} == set(data['mapping']) and len(rows) == len(data['mapping'])
    modes = sorted({row['mode'] for row in rows})
    result = {'rater_type': 'AI', 'descriptive_only': True, 'rows': rows,
              'by_mode': {mode: aggregate([r for r in rows if r['mode'] == mode]) for mode in modes},
              'distinct_people': len({r['person'] for r in rows}),
              'distinct_authored_dialogues': len({r['history'] for r in rows})}
    for dimension in ['person', 'history']:
        result['by_' + dimension] = {value: {mode: aggregate([r for r in rows if r[dimension] == value and r['mode'] == mode])
                                             for mode in modes} for value in sorted({r[dimension] for r in rows})}
    result['by_feasibility_flag'] = {str(flag): {mode: aggregate([r for r in rows if bool(r['target_flags']) == flag and r['mode'] == mode])
                                               for mode in modes} for flag in [False, True]}
    inputs = ['prepared.json', 'calls.json', 'evaluation-plan.json', 'ai-ratings.json',
              'face-results.json', 'feasibility-preflight.json']
    result['input_sha256'] = {name: sha(root / name) for name in inputs}
    result['script_sha256'] = sha(Path(__file__))
    save(root / 'summary.json', result)
    lines = ['# 이미지 단계 결과', '', '| 방법 | 목표 충족 | 판단 불가 | 6항목 모두 충족 | 얼굴 코사인 평균 |',
             '| --- | --- | --- | --- | --- |']
    for mode, row in result['by_mode'].items():
        face = '측정 불가' if row['face_mean'] is None else f'{row["face_mean"]:.6f}'
        lines.append(f'| {mode} | {row["goals_satisfied"]}/{row["goal_denominator"]} | {row["unknown_goals"]} | '
                     f'{row["all_six_satisfied"]}/{row["conditions"]} | {face} |')
    lines += ['', f'{len(rows)}조건이며 실제 생성 작업은 {measured["unique_jobs"]}회, 고유 RGB 이미지는 '
              f'{measured["unique_rgb_images"]}종이다. 중복 조건은 독립 반복이 아니다. '
              f'원본 인물 {result["distinct_people"]}명·개발자 작성 대화 {result["distinct_authored_dialogues"]}종이다.', '',
              'AI 점수는 사람 평가가 아니며 모순되는 설명도 원문에 보존했다. 판단 불가를 성공으로 세지 않았다. '
              '옷깃 핀·재킷 의존성 플래그가 있는 조건도 주 집계에 포함했다. 인물·대화·플래그별 수치는 summary.json에 있다. '
              '같은 이미지의 반복 조건과 같은 대화의 여러 턴을 독립 표본으로 간주한 유의성 검정은 하지 않았다.', '']
    (root / 'RESULTS.md').write_text('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
