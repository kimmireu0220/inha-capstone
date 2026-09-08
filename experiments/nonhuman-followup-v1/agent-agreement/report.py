"""Write the AI-agreement report and save an actual read-only test run."""
import importlib.util
import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('analysis_for_report', ROOT/'analyze.py')
calc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)


def pct(v):
    return 'null' if v is None else f'{100*v:.2f}%'


def decimal(v):
    return 'null' if v is None else f'{v:.6f}'


def main():
    test_spec = importlib.util.spec_from_file_location('integrity_tests', ROOT/'test_integrity.py')
    module = importlib.util.module_from_spec(test_spec)
    test_spec.loader.exec_module(module)
    stream = io.StringIO()
    run = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    validation = {'at_utc': datetime.now(timezone.utc).isoformat(), 'tests_run': run.testsRun,
                  'passed': run.wasSuccessful(), 'failures': len(run.failures), 'errors': len(run.errors),
                  'test_sha256': calc.sha(ROOT/'test_integrity.py'), 'results_sha256': calc.sha(ROOT/'results.json'),
                  'manifest_sha256': calc.sha(ROOT/'manifest.json'), 'log': stream.getvalue()}
    calc.save('validation.json', validation)
    assert run.wasSuccessful(), stream.getvalue()
    d = calc.read(ROOT/'results.json')
    inter = d['inter_rater_unique']
    lines = ['# 두 AI 관찰의 재현성과 동결 지표 일치', '',
             '같은 기반 모델의 독립 두 세션이 관찰한 인위적 피부 무늬 severity를 분석했다. 고유 83장 중 등급은 75장(90.36%), severity≥2 이진 판단은 79장(95.18%)에서 일치했다. P01을 제외한 순차 60단계에서 기존 LPIPS 경보의 AI별 precision은 모두 96.23%, recall은 100.00%와 98.08%였다. 이 수치는 AI 관찰과의 일치이며 사람 정답 기준 감지 성능은 아니다.', '',
             '## 표본 구성과 검증', '',
             '- 익명 패킷은 현행 최종 고유 출력 83개 + 원본-원본 대조 6개 + 숨긴 반복 8개 = 97개이며, 두 평가 파일 모두 정확히 97개 ID를 포함한다.',
             '- 공개 비교 PNG 97개에서 원본/후보 crop 픽셀이 해독표의 원본 이미지 crop과 모두 정확히 같음을 확인했다. 숨긴 반복은 같은 출력 해시의 최초 고유 항목에 연결했다.',
             '- 고유 출력 83개만 평가자 간 일치와 unique 상관의 분모로 썼다. 대조 6개·반복 8개는 성능·상관 본분모에서 제외했다. 현행 tail의 raw 전용 2장은 평가 패킷에 없어 제외했다.',
             '- 지표와의 단계별 연결은 현행 90개 최종 기록에 한정했다. 순차 감지 분석은 7경로 70단계(6인물), P01 제외 분석은 6경로 60단계(5인물)다. P03의 두 경로는 같은 인물의 반복이다.',
             '- 두 AI의 null은 각각 0/97개다. 따라서 평가자 간 유효 분모 83, 각 숨긴 반복 분모 8, 원본 대조 분모 6, 감지/상관 분모 70 또는 60에서 null 제외 수는 전부 0이다.',
             f'- source·원문·이미지 해시 및 수치 경계/0분산/null/0분모 검사를 포함해 {validation["tests_run"]}개 테스트를 통과했다. 평가 원문과 기존 지표·임계값은 수정하지 않았다.', '',
             '## 평가자 간 일치', '',
             '| 비교 | 결과 | 유효 분모 |', '|---|---:|---:|',
             f'| 등급 정확 일치 | {inter["ordinal_exact_count"]}/83 = {pct(inter["ordinal_exact_agreement"])} | 83 |',
             f'| 선형 가중 Cohen κ (주) | {decimal(inter["linear_weighted_kappa"]["value"])} | 83 |',
             f'| 제곱 가중 Cohen κ (보조) | {decimal(inter["quadratic_weighted_kappa"]["value"])} | 83 |',
             f'| severity≥2 이진 일치 | {inter["binary_agreement_count"]}/83 = {pct(inter["binary_agreement"])} | 83 |', '',
             '등급 교차표(행 AI A, 열 AI B):', '',
             '| A \\ B | 0 없음 | 1 약함 | 2 뚜렷함 | 3 심함 |', '|---|---:|---:|---:|---:|']
    for n, row in enumerate(inter['ordinal_matrix_rows_a_columns_b']):
        lines.append(f'| {n} | '+' | '.join(map(str, row))+' |')
    lines += ['', '8개 등급 불일치는 모두 한 등급 차이이며, 4개는 severity 1/2 경계를 넘는 이진 불일치다. 합의 라벨을 만들거나 불일치를 제거하지 않았다.', '',
              '| 원본 고유 ID | 경로·단계 | AI A | AI B |', '|---|---|---:|---:|']
    for r in inter['disagreements']:
        sources = ', '.join(f'{s["branch"]}:{s["stage"]}' for s in r['sources'])
        lines.append(f'| {r["id"]} | {sources} | {r["a"]} | {r["b"]} |')
    lines += ['', '## 숨긴 반복과 원본 대조', '',
              '| AI | 숨긴 반복 등급 일치 | 숨긴 반복 이진 일치 | 원본 대조 severity>0 | 원본 대조 severity≥2 |',
              '|---|---:|---:|---:|---:|']
    for reviewer in ('a', 'b'):
        r, c = d['within_rater_hidden_repeats'][reviewer], d['identity_false_positive'][reviewer]
        lines.append(f'| {reviewer.upper()} | {r["ordinal_exact_count"]}/{r["n_complete"]} ({pct(r["ordinal_exact_agreement"])}) | {r["binary_agreement_count"]}/{r["n_complete"]} ({pct(r["binary_agreement"])}) | {c["severity_gt0_count"]}/{c["n_complete"]} | {c["severity_ge2_count"]}/{c["n_complete"]} |')
    lines += ['', 'AI A의 한 반복 불일치는 P01 stage1의 severity 1→0이다. 두 AI 모두 뚜렷한 열화 여부는 8쌍에서 일치했다. 표본 8쌍과 원본 대조 6개는 작은 내부 검사이고 사람 평가와의 일치 또는 실제 정상 이미지 전체에 대한 false-positive rate를 추정하지 않는다. 여기서 identity는 동일 이미지 대조라는 뜻이며 이미지 간 동일인 식별은 수행하지 않았다.', '',
              '## 기존 고정 임계값과 AI 판단', '',
              '동결된 규칙은 MAE≥0.0288375, SSIM≤0.842874, LPIPS≥0.0555075이다. 각 규칙을 따로 비교했으며 조합하거나 재보정하지 않았다. 비교 기준은 각 AI의 severity≥2이고 severity 0/1은 clear 아님이다. TP/FP/TN/FN의 양성은 각각 지표 경보/AI clear다.', '']
    for cohort, title in [('sequential70', '전체 순차 70단계'), ('excluding_p01_60', 'P01 제외 순차 60단계')]:
        lines += [f'### {title}', '', '| AI | 지표 | TP | FP | TN | FN | precision | recall | specificity | 이진 일치 |',
                  '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for reviewer, metrics in d['frozen_threshold_comparison'][cohort].items():
            for metric, c in metrics.items():
                lines.append(f'| {reviewer.upper()} | {metric} | {c["tp"]} | {c["fp"]} | {c["tn"]} | {c["fn"]} | {pct(c["precision"])} | {pct(c["recall"])} | {pct(c["specificity"])} | {pct(c["binary_agreement"])} |')
        lines.append('')
    lines += ['P01은 기존 기준 설정에 사용한 인물이라 제외 분석을 별도로 보였다. 나머지 60단계도 같은 실험 설계·종속 경로에 속하며 새 독립 외부 검증 집합으로 부르지 않는다. 60단계의 AI clear 비율은 A 51/60=85.00%, B 52/60=86.67%다. 따라서 높은 recall만으로 충분하지 않고, 적은 음성 표본(A 9개/B 8개)에서 specificity와 FP를 함께 보아야 한다.', '',
              '세 지표는 서로 다른 경계 선택을 보인다. MAE는 60단계에서 두 AI 모두 FP=0이지만 FN=3/4이고, SSIM은 FN=0이지만 FP=4/3이다. LPIPS는 FP=2/2와 FN=0/1이다. 이것은 현재 자료의 비교이며 최적 감지기를 선택하기 위한 재학습은 하지 않았다.', '',
              'LPIPS와 AI binary가 달랐던 순차 단계:', '',
              '| 경로·단계 | AI | 고정 LPIPS | AI severity | 경보/관찰 관계 |', '|---|---|---:|---:|---|']
    for r in d['joined_stages']:
        if r['policy'] != 'sequential':
            continue
        for reviewer in ('a', 'b'):
            severity = r['ratings'][reviewer]['severity']
            if severity is None:
                continue
            alarm = calc.alarm('lpips', r['face']['fixed']['lpips'])
            if alarm != (severity >= 2):
                lines.append(f'| {r["branch"]}:{r["stage"]} | {reviewer.upper()} | {r["face"]["fixed"]["lpips"]:.9f} | {severity} | {"FP: 경보, AI 약함/없음" if alarm else "FN: 무경보, AI 뚜렷함"} |')
    lines += ['', 'P04 stage2의 LPIPS 0.054777376은 동결 임계값 0.0555075보다 조금 낮다. 이 항목은 AI A severity1, B severity2로 나뉜다. 첫 경보 시점의 정답을 한 단계로 강제하기 어려운 경계 사례다.', '',
              '## 처음 관측한 단계', '',
              '| 순차 경로 | 첫 MAE 경보 | 첫 SSIM 경보 | 첫 LPIPS 경보 | 첫 AI A clear | 첫 AI B clear |',
              '|---|---:|---:|---:|---:|---:|']
    timings = {(r['branch'], r['reviewer']): r for r in d['first_observed_stages']}
    for branch in dict.fromkeys(r['branch'] for r in d['first_observed_stages']):
        a, b = timings[(branch, 'a')], timings[(branch, 'b')]
        alarms = a['first_frozen_alarm_stage']
        lines.append(f'| {branch} | {alarms["mae"]} | {alarms["ssim"]} | {alarms["lpips"]} | {a["first_ai_clear_stage"]} | {b["first_ai_clear_stage"]} |')
    lines += ['', 'LPIPS 첫 경보와 AI A의 첫 clear는 7경로 중 5개가 같고 2개는 경보가 한 단계 먼저다. AI B와는 4개가 같고 2개는 경보가 한 단계 먼저, P04 한 경로는 한 단계 늦다. P01 제외 시 A 4/6, B 3/6이 같은 단계다. 모두 단계 순서에 관한 관측이고 실제 시간·날짜·관측되지 않은 시점을 추정하지 않았다.', '',
              '## 정합 전후 순위 상관: 탐색 결과', '',
              'Spearman rho는 AI severity와 연속 지표의 상관이다. SSIM은 1−SSIM으로 방향을 맞춰 모든 값이 클수록 원본 차이가 크다. 정합은 sigma3를 아래에 제시하며 sigma1/6 값도 results.json에 보존했다. 정합 지표에 기존 고정 ROI 임계값을 적용한 감지 성능은 계산하지 않았다.', '',
              '| 자료 | AI | 지표 | 고정 rho | sigma3 rho | 차이 | 유효 n |', '|---|---|---|---:|---:|---:|---:|']
    for cohort, reviewers in d['rank_correlations_exploratory'].items():
        for reviewer, metrics in reviewers.items():
            for metric, values in metrics.items():
                fixed, aligned = values['modes']['fixed'], values['modes']['3']
                lines.append(f'| {cohort} | {reviewer.upper()} | {values["orientation"]} | {decimal(fixed["rho"])} | {decimal(aligned["rho"])} | {decimal(values["delta_rho_sigma3_minus_fixed"])} | {fixed["n_complete"]} |')
    lines += ['', 'P01 제외 60단계에서 LPIPS rho는 A 0.800601→0.856718, B 0.773555→0.828666으로 높아졌다. 83개 고유 최종 출력에서도 A 0.753721→0.814303, B 0.733660→0.793337이었다. 반면 83개에서 MAE rho는 정합 뒤 A 0.650958→0.634920, B 0.636888→0.624716으로 낮아졌다. 정합이 모든 지표를 일관되게 개선한다는 증거는 아니다.', '',
              '이 pooled 상관은 단계 진행·인물·방법 차이에 영향을 받을 수 있다. 경로별 상관도 results.json에 보존했으며, 상관 증가에 p값이나 독립 표본 신뢰구간을 붙이지 않았다. 어떤 입력의 rank 또는 label이 모두 같으면 rho를 0으로 꾸미지 않고 null과 zero_rank_variance 이유를 저장하는 검사를 통과했다.', '',
              '## 현재 주장에 유익한 해석과 제한', '',
              '1. 두 AI 관찰은 clear 여부에서 95.18% 일치하며 원본 대조와 반복 검사에서 큰 내부 모순은 적었다. 단, 미세한 severity 0/1과 1/2 경계에는 불일치가 있고 합의 정답을 만들지 않았다.',
              '2. P01을 제외해도 동결 LPIPS 경보는 이 AI clear 판단과 높은 재현율을 보였지만, 60단계 중 양성이 51/52개여서 specificity와 경계 오류를 함께 보고해야 한다. 사람 기준 피부 열화 감지기가 검증됐다는 결론은 유보한다.',
              '3. 정합 뒤 LPIPS와 AI 등급의 순위 상관이 높아진 결과는 정합 기반 지표를 별도 데이터에서 검증할 근거다. 이번 정합 점수로 임계값을 다시 맞추거나 새 정책의 실현 성능을 주장하지 않는다.',
              '4. P03-r1/P03-r2, P04, P05의 초반 경계 사례를 향후 사람 평가에 포함할 이유가 있다. AI가 합의한 쉬운 사례만 고르는 절차는 사용하지 않았다.', '',
              '두 평가자는 같은 기반 모델의 독립 세션이며 다른 모델 두 종 또는 사람 두 명이 아니다. 방법·단계·지표를 가렸어도 모델 공통 편향과 동일한 320×360 고정 crop의 한계를 공유한다. 6인물 7개 순차 경로, 인물 내 반복 단계, P03 두 회, 정책 간 공유 이미지는 의존적이다. 높은 AI 합의·지표 상관은 사람 판단, 정체성 유지, 자연스러움 전체, 요구 충족, 외부 모델 일반화의 정답을 제공하지 않는다.', '',
              '사람 평가·새 detector 훈련·threshold tuning·정합 threshold 성능·합의 라벨·p값·bootstrap은 산출하지 않았다. 관측된 날짜별 성능이나 관측되지 않은 개입 시점도 추정하지 않았다.', '',
              '## 재현 파일', '',
              '- PROTOCOL.md: 결합·집계 전에 정한 분석 범위와 결측·0분산 처리.',
              '- manifest.json: 평가 원문/해독표/현재 지표/PNG/원본 해시, 동결 임계값, 환경.',
              '- results.json: 원문 그대로 연결한 83고유·90단계 데이터, 일치도·교차표·반복·대조·성능·상관·최초 시점.',
              '- joined-stages.csv: 90단계×두AI=180행의 원본 지표·등급·경보 연결.',
              '- test_integrity.py 및 validation.json: 16개 수치·무결성 검사와 실행 기록.',
              '- artifact-hashes.json: 이 디렉터리 납품 파일의 SHA256.', '',
              '프로젝트 루트에서 재실행:', '', '```sh',
              '.venv-metrics/bin/python experiments/nonhuman-followup-v1/agent-agreement/analyze.py',
              '.venv-metrics/bin/python experiments/nonhuman-followup-v1/agent-agreement/report.py', '```']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    calc.save('artifact-hashes.json', {p.name: calc.sha(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name != 'artifact-hashes.json'})
    print(json.dumps({'tests': run.testsRun, 'passed': run.wasSuccessful(), 'report': str(ROOT/'RESULTS.md')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
