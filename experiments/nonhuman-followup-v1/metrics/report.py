"""Build a reviewable report solely from this analysis's saved numeric results."""
import hashlib
import importlib.util
import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def main():
    spec = importlib.util.spec_from_file_location('integrity', ROOT/'test_integrity.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stream = io.StringIO()
    run = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    validation = {'at_utc': datetime.now(timezone.utc).isoformat(), 'tests_run': run.testsRun,
                  'passed': run.wasSuccessful(), 'failures': len(run.failures), 'errors': len(run.errors),
                  'test_sha256': sha(ROOT/'test_integrity.py'), 'results_sha256': sha(ROOT/'results.json'),
                  'manifest_sha256': sha(ROOT/'manifest.json'), 'log': stream.getvalue()}
    save('validation.json', validation)
    assert run.wasSuccessful(), stream.getvalue()
    d = json.loads((ROOT/'results.json').read_text())
    m = json.loads((ROOT/'manifest.json').read_text())
    rows, summary = d['rows'], d['summary']
    p04 = ['P04', 'P04-fixed3', 'P04-triggered']
    display = {'P04': 'sequential', 'P04-fixed3': 'fixed3', 'P04-triggered': 'triggered'}
    lines = ['# 현행 출력의 정합·피부 ROI 민감도 결과', '',
             '현행 revised-tail-v1 출력으로 재계산한 사후 진단이다. P04 LPIPS 평균·최종의 triggered < fixed3 < sequential 순서는 고정 및 sigma1/3/6 정합에서 유지되었으나, MAE·SSIM의 일부 순위는 전처리와 ROI에 따라 달라졌다. 얼굴·피부 영역과 위치 보정 설정별로 원본과의 차이를 비교했다.', '',
             '## 자료 및 재현성', '',
             f'- 현행 8개 편집 과정의 80단계 최종 기록, 고유 최종 {m["unique_final_outputs"]}장, 현행 9–10단계 raw 전용 2장을 합쳐 고유 {d["unique_outputs"]}장이다. P04 3정책은 고유 {d["unique_p04_outputs"]}장이다. 인물은 6명이며 P04의 세 정책은 같은 원본을 공유한다.',
             '- inputs/progress/curves의 현재 경로·해시를 상호 대조했다. 분석에는 현행 목록의 출력만 사용했다.',
             '- 고정 MAE·SSIM·LPIPS 80단계 재현의 최대 절대오차는 모두 정확히 0.0이다. 원본·입력 문서·출력 이미지 해시가 실행 전후 일치했다.',
             f'- 저장 산출물 독립 검사 {validation["tests_run"]}개 통과. 원본 기반 코드 대조군 11종을 정합 sigma 3개마다 확인했다. LPIPS 가중치 및 라이브러리 버전은 manifest.json에 기록했다.',
             '- prior runner를 import하면 생길 수 있는 옛 경로·cache 쓰기를 피하고, 기존 순수 수식을 이 디렉터리의 함수로 재사용했다. 보존된 이미지에 자동 지표를 계산했다.', '',
             '## 전체 편집 과정: 얼굴 ROI LPIPS', '',
             'sigma3는 사전에 정한 주 분석이다. 평균은 편집 과정별 10개 최종 단계를 같은 가중치로 집계한다.', '',
             '| 편집 과정 | 고정 평균 | 정합 평균 | 고정 최종 | 정합 최종 |',
             '|---|---:|---:|---:|---:|']
    for b, values in summary.items():
        face = values['face']
        lines.append(f'| {b} | {face["fixed"]["mean"]["lpips"]:.6f} | {face["3"]["mean"]["lpips"]:.6f} | {face["fixed"]["final"]["lpips"]:.6f} | {face["3"]["final"]["lpips"]:.6f} |')
    decreases = sum(r['face']['3']['lpips'] < r['face']['fixed']['lpips'] for r in rows.values())
    increases = sum(r['face']['3']['lpips'] > r['face']['fixed']['lpips'] for r in rows.values())
    lines += ['', f'sigma3 정합 뒤 LPIPS는 {decreases}장 감소, {increases}장 증가, {len(rows)-decreases-increases}장 동일했다. 대응 위치는 NCC로 선택하며 LPIPS 변화 방향은 이미지에 따라 달라진다.', '',
              'P05 최종은 dx=42, dy=31, NCC=0.61957이며 LPIPS가 0.531565→0.613747로 증가한다. 같은 sigma3 정합에서 MAE는 0.241228→0.228410, SSIM은 0.244444→0.248801로 반대 방향이다. 위치 보정의 영향은 지표별로 달랐다.', '',
              '## P04 세 정책: 정합 얼굴 ROI', '',
              '| 정책 | 평균 MAE ↓ | 평균 SSIM ↑ | 평균 LPIPS ↓ | 최종 MAE ↓ | 최종 SSIM ↑ | 최종 LPIPS ↓ |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for b in p04:
        v = summary[b]['face']['3']
        lines.append('| '+display[b]+' | '+' | '.join(f'{v[e][k]:.6f}' for e in ('mean', 'final') for k in ('mae', 'ssim', 'lpips'))+' |')
    lines += ['', '얼굴 LPIPS에서 fixed3 대비 triggered의 평균 점수 차이는 고정 0.072402에서 sigma3 정합 0.023246으로 좁아졌다. 최종 차이도 0.037576→0.027722다. 순서는 안정적이지만 수치상 차이의 크기는 위치 보정에 민감하다.', '',
              '## P04 피부 내부 세 ROI', '',
              '원본에서 고정했던 이마와 양 볼 영역 총 6,800픽셀을 사용한다. 얼굴 ROI 115,200픽셀의 약 5.90%이며, 원본에서 선택한 세 영역을 모든 출력에 적용했다. sigma3 결과는 다음과 같다.', '',
              '| 정책 | 평균 MAE ↓ | 평균 SSIM ↑ | 평균 highpass MAE ↓ | 최종 MAE ↓ | 최종 SSIM ↑ | 최종 highpass MAE ↓ |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for b in p04:
        v = summary[b]['skin']['3']
        lines.append('| '+display[b]+' | '+' | '.join(f'{v[e][k]:.6f}' for e in ('mean', 'final') for k in ('mae', 'ssim', 'highpass_mae'))+' |')
    lines += ['', '세 영역 합산 피부 MAE와 highpass MAE의 평균·최종 순서는 고정 및 모든 정합 sigma에서 triggered < fixed3 < sequential로 유지되었다. 피부 SSIM 평균도 triggered > fixed3 > sequential이 유지되었다. 피부 SSIM 최종은 sigma6에서 fixed3가 triggered보다 높아졌다.', '',
              '## 설정·ROI에 따른 순위 변화', '',
              '정합 sigma 사이 이동 추정의 최대 축별 범위는 3px이고, >3px 휴리스틱 플래그는 0/75장이다. 탐색 경계 도달도 sigma1/3/6 모두 0/75장이다. 아래에서 지표 순위의 설정 민감도를 함께 비교했다.', '',
              '5개 영역 정의(얼굴, 피부 합계, 이마, 양 볼) × 2종 집계(평균/최종) × 3지표 = 30개 비교군 중 9개는 고정/정합 설정에 따라 순서가 달라졌고, 그중 7개는 정합 sigma1/3/6 사이에서도 달라졌다. 각 비교군은 같은 출력을 공유하는 기술통계다.', '',
              '| 최종 지표 | 고정 fixed3 / triggered | sigma1 | sigma3 | sigma6 |',
              '|---|---:|---:|---:|---:|']
    for scope, metric in [('face', 'mae'), ('face', 'ssim'), ('face', 'lpips'), ('skin', 'ssim')]:
        pairs = [f'{summary["P04-fixed3"][scope][mode]["final"][metric]:.6f} / {summary["P04-triggered"][scope][mode]["final"][metric]:.6f}' for mode in ('fixed', '1', '3', '6')]
        lines.append(f'| {scope} {metric} | '+' | '.join(pairs)+' |')
    lines += ['', 'triggered 최종 이동은 sigma1 (−1,−1), sigma3 (−1,−2), sigma6 (−2,−4)이다. fixed3 최종은 (1,2), (1,1), (0,0)이다. 1–3픽셀 차이가 피부 SSIM 최종 순위까지 바꾼다. 이동 추정과 지표 순위의 안정성을 함께 확인해야 한다.', '',
              'ROI를 바꾸어도 순위가 달라진다. sigma3 평균에서 넓은 얼굴 ROI의 MAE·SSIM은 sequential이 fixed3보다 원본에 가깝지만(0.063885 < 0.064136; 0.717924 > 0.713740), 피부 합계는 fixed3가 더 가깝다(0.023254 < 0.038857; 0.760676 > 0.723416). 피부 전용 주장을 넓은 얼굴 ROI 점수 하나로 대신하기 어렵다는 진단이다.', '',
              '전체 120개 순위 행은 results.json의 p04_rankings에 보존했다. 설정별 순위와 차이의 크기를 함께 제시한다.', '',
              '## 이미 실행된 tail 개입의 전후 수치', '',
              '현행 9–10단계에서 실제 rebase가 실행된 세 쌍만 비교했다. 양수 ΔLPIPS=raw−final은 final 점수가 낮다는 뜻이다. 각 수치는 한 번 실행된 출력 쌍의 차이다.', '',
              '| 편집 과정·단계 | raw 고정 LPIPS | final 고정 LPIPS | Δ 고정 | Δ sigma1 | Δ sigma3 | Δ sigma6 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for r in d['tail_interventions']:
        raw, final = rows[r['raw_id']], rows[r['final_id']]
        deltas = [r['face_raw_minus_final'][s]['lpips'] for s in ('fixed', '1', '3', '6')]
        lines.append(f'| {r["branch"]} stage{r["stage"]} | {raw["face"]["fixed"]["lpips"]:.6f} | {final["face"]["fixed"]["lpips"]:.6f} | '+' | '.join(f'{v:+.6f}' for v in deltas)+' |')
    lines += ['', 'triggered stage9의 rebase 결과는 raw보다 얼굴 MAE·SSIM·LPIPS 및 피부 합산 MAE·SSIM·highpass MAE가 고정/모든 정합 설정에서 모두 원본에서 멀어졌다. 이 사례는 얼굴 ROI의 이동 혼입만으로 해당 지표 악화를 설명하기 어렵다는 근거다. 피부 품질은 별도 관찰과 함께 해석한다.', '',
              '## 코드 대조군', '',
              '| 조건 | sigma3 피부 MAE | 피부 SSIM | 피부 highpass MAE | 얼굴 LPIPS |',
              '|---|---:|---:|---:|---:|']
    for c in d['controls']:
        sk = c['skin']['3']
        lines.append(f'| {c["name"]} | {sk["mae"]:.8f} | {sk["ssim"]:.6f} | {sk["highpass_mae"]:.8f} | {c["face"]["3"]["lpips"]:.6f} |')
    lines += ['', '동일성·알려진 이동·먼 주변 교체의 대응 ROI는 MAE=0, SSIM=1, LPIPS=0을 회복했다. 밝기 +0.03은 피부 MAE≈0.03을 남기지만 highpass MAE≈1.61×10⁻⁸로 거의 제거된다. 밝기 +0.10은 clipping 영향이 남아 highpass MAE≈0.000512이다. 사인 무늬의 진폭 증가에 highpass가 단조 반응하지만 흐림에도 반응한다. 이 대조군으로 이동·밝기·무늬에 대한 수식의 반응을 확인했다.', '',
              '## 결과 해석', '',
              '1. 현행 편집 과정에서 자동 원본 유사도 결과의 전처리·ROI 민감도를 전 출력 대상으로 감사했다. LPIPS의 P04 정책 순서는 이번 네 설정에서 유지되지만 효과 크기와 일부 MAE/SSIM 순위는 달라진다.',
              '2. 정합 위치의 설정 범위가 작고 탐색 경계에 닿지 않아도 지표 순위는 바뀔 수 있다. 변환 안정성과 지표 안정성을 별도로 보고할 이유가 있다.',
              '3. 넓은 얼굴 ROI와 작은 피부 내부 표본은 다른 측정 대상이다. 얼굴 유사도와 피부 영역 지표를 함께 보고한다.',
              '4. 이미 실행된 triggered stage9 개입의 원본 유사도 악화는 이번 정합·ROI 변형 전부에서 유지된다. 이 사례는 개입 전후 지표 변화 분석에 포함했다.', '',
              '정합은 정수 평행이동만 고려하며 회전·스케일·표정·조명·형상 변화를 남긴다. 원본의 정상 피부결과 주름도 잔여 오차에 포함된다. 피부 표본은 P04 한 인물이다. 저장된 출력의 지표를 재계산했으며, 정책 실행은 당시 사용한 고정 영역 임계값을 따른다.', '',
              '## 파일과 재실행', '',
              '- PROTOCOL.md: 계산 전에 고정한 범위와 수식.',
              '- manifest.json: 현행 입력, 코드, 이미지 및 LPIPS 가중치 해시와 환경.',
              '- results.json: 75장 전체의 위치·얼굴/피부 지표, 80단계 매핑, 120개 순위, tail 개입 쌍, 대조군.',
              '- curves.csv: 80단계 × 4정합 설정의 얼굴 지표와 P04 피부 합계/개별 영역 지표.',
              '- test_integrity.py 및 validation.json: 읽기 전용 재현성 검사와 실행 기록.',
              '- artifact-hashes.json: 이 디렉터리의 최종 납품 파일 해시.', '',
              '프로젝트 루트에서 실행:', '',
              '```sh',
              '.venv-metrics/bin/python experiments/nonhuman-followup-v1/metrics/analyze.py',
              '.venv-metrics/bin/python experiments/nonhuman-followup-v1/metrics/report.py',
              '```', '',
              '재실행 시 이 디렉터리의 분석 산출물을 갱신한다.']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    save('artifact-hashes.json', {p.name: sha(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name != 'artifact-hashes.json'})
    print(json.dumps({'tests_passed': run.wasSuccessful(), 'tests_run': run.testsRun,
                      'report': str(ROOT/'RESULTS.md'), 'unique_outputs': d['unique_outputs']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
