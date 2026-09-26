"""Write the six-person AI-agreement report and run integrity checks."""
import importlib.util
import io
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('agreement_calcs', ROOT/'analyze.py')
calc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)


def pct(value):
    return 'null' if value is None else f'{value*100:.2f}%'


def dec(value):
    return 'null' if value is None else f'{value:.6f}'


def main():
    spec = importlib.util.spec_from_file_location('agreement_integrity', ROOT/'test_integrity.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stream = io.StringIO()
    run = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    assert run.wasSuccessful(), stream.getvalue()

    d = calc.read(ROOT/'results.json')
    c = d['catalog']
    inter = d['inter_rater_unique']
    lines = [
        '# 초기 6인물 AI 평가 일치도', '',
        '합성 인물 6명의 순차 편집 6경로와 P04 정책 경로를 대상으로, 같은 기반 모델의 독립 두 세션이 인위적 얼굴 변화를 0~3등급으로 평가했다. 두 세션은 사람 평가나 서로 다른 모델의 합의를 뜻하지 않는다.', '',
        '## 평가 자료', '',
        f'- 고유 출력 {c["unique_candidates"]}개, 원본 대조 {c["identity_controls"]}개, 숨긴 반복 {c["hidden_repeats"]}개를 포함해 세션당 {c["total"]}개를 평가했다.',
        f'- 초기 순차 경로는 6개이며 단계 기록은 {c["sequential_stage_records"]}개다. P01을 제외한 보조 분석은 {c["excluding_p01_stage_records"]}개다.',
        f'- 전체 현행 정책 단계 기록은 {c["current_final_stage_records"]}개다.', '',
        '## 세션 간 일치', '',
        '| 항목 | 결과 |', '|---|---:|',
        f'| 등급 정확 일치 | {inter["ordinal_exact_count"]}/{inter["n_complete"]} = {pct(inter["ordinal_exact_agreement"])} |',
        f'| 선형 가중 Cohen κ | {dec(inter["linear_weighted_kappa"]["value"])} |',
        f'| severity≥2 이진 일치 | {inter["binary_agreement_count"]}/{inter["n_complete"]} = {pct(inter["binary_agreement"])} |', '',
        '## 동결 지표와 AI 등급 비교', '',
        '양성은 AI severity≥2이며 기존 MAE·SSIM·LPIPS 임계값을 변경하지 않았다. 아래 값은 AI 관찰과의 일치도이며 사람 정답 기준 감지 정확도가 아니다.', '',
        '| 자료 | AI | 지표 | Precision | Recall | Specificity |',
        '|---|---|---|---:|---:|---:|'
    ]
    for cohort, reviewers in d['frozen_threshold_comparison'].items():
        for reviewer, metrics in reviewers.items():
            for metric, values in metrics.items():
                lines.append(f'| {cohort} | {reviewer.upper()} | {metric} | {pct(values["precision"])} | {pct(values["recall"])} | {pct(values["specificity"])} |')

    lines += ['', '## 경로별 최초 관측 단계', '',
              '| 경로 | 첫 MAE 경보 | 첫 SSIM 경보 | 첫 LPIPS 경보 | 첫 AI A clear | 첫 AI B clear |',
              '|---|---:|---:|---:|---:|---:|']
    timing = {(r['branch'], r['reviewer']): r for r in d['first_observed_stages']}
    for branch in dict.fromkeys(r['branch'] for r in d['first_observed_stages']):
        a, b = timing[(branch, 'a')], timing[(branch, 'b')]
        alarm = a['first_frozen_alarm_stage']
        lines.append(f'| {branch} | {alarm["mae"]} | {alarm["ssim"]} | {alarm["lpips"]} | {a["first_ai_clear_stage"]} | {b["first_ai_clear_stage"]} |')

    lines += ['', '## 해석 제한', '',
              '- 동일 인물의 단계는 서로 독립된 표본이 아니다.',
              '- 얼굴 영역에는 피부 외 구조와 위치 변화가 함께 반영된다.',
              '- 높은 세션 간 일치도는 사람 판단이나 외부 모델 일반화를 보장하지 않는다.', '',
              '## 재현 파일', '',
              '- `results.json`: 연결된 지표, 등급, 일치도와 경로별 최초 단계',
              '- `joined-stages.csv`: 단계별 지표와 두 AI 등급',
              '- `manifest.json`: 입력과 이미지 해시',
              '- `validation.json`: 무결성 검사 결과', '']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines).rstrip()+'\n')
    calc.save('validation.json', {'passed': True, 'tests_run': run.testsRun, 'log': stream.getvalue(),
                                  'results_sha256': calc.sha(ROOT/'results.json'),
                                  'manifest_sha256': calc.sha(ROOT/'manifest.json')})
    calc.save('artifact-hashes.json', {p.name: calc.sha(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name != 'artifact-hashes.json'})
    print(json.dumps({'tests': run.testsRun, 'passed': True, 'report': str(ROOT/'RESULTS.md')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
