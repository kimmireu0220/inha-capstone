"""Report the terminal collection with explicit missing endpoints and costs."""
import importlib.util
import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('extension_calcs',ROOT/'analyze.py')
calc=importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)


def number(v): return 'null' if v is None else f'{v:.6f}'


def main():
    spec=importlib.util.spec_from_file_location('extension_integrity',ROOT/'test_integrity.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stream=io.StringIO()
    run=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    validation={'at_utc':datetime.now(timezone.utc).isoformat(),'tests_run':run.testsRun,'passed':run.wasSuccessful(),
                'failures':len(run.failures),'errors':len(run.errors),'log':stream.getvalue(),
                'test_sha256':calc.sha(ROOT/'test_integrity.py'),'results_sha256':calc.sha(ROOT/'results.json'),
                'manifest_sha256':calc.sha(ROOT/'manifest.json')}
    calc.save('validation.json',validation)
    assert run.wasSuccessful(),stream.getvalue()
    d=calc.read(ROOT/'results.json')
    m=calc.read(ROOT/'manifest.json')
    s=d['summary']
    p04=['P04','P04-once-triggered','P04-fixed3','P04-triggered','P04-end-only','P04-always-original']
    lines=['# 추가 정책 출력의 지표·지속성·비용 비교','',
           '추가 수집은 신규25개 성공과1개 실패로 종료했고, 20경로 중19경로의10단계와 P05 once-triggered의1–8단계를 분석했다. 최초 재생성 뒤 P04·P05·P06 모두 다음 한 번의 편집에서 동결 LPIPS 경보가 다시 나타났다. 일부 최종 순위는 고정/정합 지표에 따라 바뀌며, P04 always-original 기준선은 every-triggered와3–10단계 출력을 공유하면서 논리 호출 수가10회 대18회다. 이 결과는 원본 유사도·운영상 비용의 기술통계다.','',
           '## 수집 종료와 재현성','',
           '- 최초 계획 신규27호출 중25출력 성공, P05 once stage9 실패1회, stage10은 입력 부재로 미실행. 따라서 신규 시도26회이며 collection_complete=true, full_design_complete=false다.',
           '- 실패 기록은 출력 단계 moderation_blocked/category other다. 재시도·프롬프트 변경·실패 이유 추가 추정은 하지 않았다. 실패 PNG가 존재하지 않음을 확인했다.',
           '- 기존85고유 지표 + 신규25고유 + 현재 추가 경로가 재사용하는 P04 once stage6 raw/P05 초기rebase/P06 초기rebase 3개 =113고유 이미지다. 기존85개 결과는 그대로 보존했다.',
           '- 20정책 경로에 총198개 관측 deliverable이 있다. 19개 최종 경로는16고유 최종 이미지를 공유한다. P03 두 end 경로와 P04 세 정책의 공유 최종을 독립 반복으로 세지 않는다.',
           f'- 기존 metrics/analyze.py의 순수 measure 함수를 직접 재사용했고 LPIPS state_dict 해시를 일치시켰다. 현재 generation/progress의 모든 고정 지표를1e-6 이내로 재현했다. 읽기 전용 및 수치 검사{run.testsRun}개 통과.',
           '- 매 호출의 입력·출력 해시, stage/state/prompt, attempt1을 검사하고 원본/추가 raw 출력 불변을 확인했다. 모든 산출물은 extension-metrics/에 저장했다. 사람·AI 평가 원문과 라벨은 읽지 않았다.','',
           '## 전체 경로: 고정/정합 LPIPS','',
           '정합은 기존 NCC±64/sigma3이며 sigma1/6도 JSON에 보존했다. 평균은10개 최종 deliverable의 동일 가중 평균이다. P05 once의 실패 후 미관측 단계는 채우지 않아10단계 평균과 최종은 null이다.','',
           '| 경로 | 관측 단계 | 완결 논리 호출 | 고정10단계 평균 | 고정 최종 | 정합10단계 평균 | 정합 최종 |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for name,v in s.items():
        scores=[number(v['face'][mode][endpoint]['lpips'] if v['face'][mode][endpoint] is not None else None) for mode in ('fixed','3') for endpoint in ('mean','final')]
        lines.append(f'| {name} | {v["deliverable_stages"]} | {v["logical_calls"] if v["logical_calls"] is not None else "null"} | '+' | '.join(scores)+' |')
    partial=s['P05-once-triggered']
    lines += ['',f'P05 once의 관측1–8단계 평균은 고정 {partial["face"]["fixed"]["observed_mean"]["lpips"]:.6f}, 정합 {partial["face"]["3"]["observed_mean"]["lpips"]:.6f}다. 마지막 관측8단계는 고정 {partial["face"]["fixed"]["last_observed"]["lpips"]:.6f}, 정합 {partial["face"]["3"]["last_observed"]["lpips"]:.6f}다. 이것을10단계 최종/평균과 직접 비교하지 않는다. 성공호출9회, 실패 포함시도10회, 완결 시 계획11회이며 계획11회를 관측비용으로 표시하지 않았다.','',
              '## 최초 reset 후 경보 재등장','',
              '동결 임계값은 고정 ROI LPIPS≥0.0555075다. 정합 지표에 이 임계값을 적용하지 않았다.','',
              '| once 경로 | 최초 reset 단계 | reset 직후 LPIPS | 처음 이후 raw 경보 단계 | raw LPIPS | reset 후 편집 수 |',
              '|---|---:|---:|---:|---:|---:|']
    for person in ('P04','P05','P06'):
        r=d['first_reset_recurrence'][person+'-once-triggered']
        lines.append(f'| {person} | {r["reset_stage"]} | {r["reset_final_fixed_lpips"]:.6f} | {r["first_later_raw_alarm_stage"]} | {r["first_later_raw_alarm_lpips"]:.6f} | {r["edits_after_reset_until_first_alarm"]} |')
    lines += ['', '세 초기 reset 모두 경보 임계값 아래로 내려갔지만 바로 다음 편집에서 다시 경보가 나타났다. P04 fixed3/every-triggered의 첫 reset와 다음 raw는 once와 동일한 파일을 공유하므로 세 번의 독립 재현으로 세지 않는다. P05의 재경보3단계는9단계 실패 이전에 직접 관측했으므로 부분 경로에서도 보고할 수 있다.', '',
              'end-only는10단계 뒤 편집이 없어 이후 재경보 시점은 미관측(null)이다. always-original은 이전 결과를 이어 편집하지 않으므로 같은 재경보 지연 개념을 적용하지 않는다. 경보 재등장은 피부 열화의 정답 시점이나 인간 판단이 아니다.','',
              '## P04 정책 비교와 비용','',
              '| 정책 | 논리 호출 | 평균 고정 MAE | 평균 고정 SSIM | 평균 고정 LPIPS | 평균 정합 LPIPS |',
              '|---|---:|---:|---:|---:|---:|']
    for name in p04:
        v=s[name];fixed=v['face']['fixed']['mean'];aligned=v['face']['3']['mean']
        lines.append(f'| {name} | {v["logical_calls"]} | {fixed["mae"]:.6f} | {fixed["ssim"]:.6f} | {fixed["lpips"]:.6f} | {aligned["lpips"]:.6f} |')
    lines += ['', 'always-original은 매 단계 최초 원본에 현재 요구를 한 번 적용한다. every-triggered는 순차 raw를 먼저 만든 뒤 경보가 나면 최초 원본에서 다시 생성한다. P04의3–10단계 최종 출력은 두 방법이 정확히 공유한다. 따라서 always-original10회와 every-triggered18회의 차이는 이 설계의 요청 수 차이이고, 두 방법의 공유8개 출력을 독립 품질 표본으로 비교하면 안 된다.', '',
              'always-original의 평균 고정 LPIPS 0.104210과 every-triggered의0.106101 차이는 서로 다른1–2단계에서만 온다. 정합 평균도0.090963/0.092580으로 가깝다. 이 자료에서는 감지 경보를 거쳐야 원본 유사도에 유리하다고 주장할 근거가 없고, 더 단순한 기준선을 반드시 함께 보고할 이유가 있다. 요구 충족·편집 의도 보존·사람 평가 없이 최적 정책으로 판정하지 않는다.','',
              'P04 once 최종 LPIPS는 고정에서 순차보다 크다(0.569457 > 0.450226). sigma3 정합에서는 반대로 작다(0.304659 < 0.312155). P06 once 최종도 고정0.391652 > 순차0.383100, 정합0.389573 < 순차0.390048로 매우 작은 역전이 있다. 한 번의 개입이 최종 피부 품질을 개선/악화했다고 한 지표만으로 확정하기 어렵다.','',
              '## P04 피부 내부3영역: sigma3','',
              '이마와 양 볼의 기존 원본 ROI를 유지했다. MAE/highpass는 영역 픽셀수, SSIM은 유효 중심 픽셀수로 가중한다.','',
              '| 정책 | 평균 피부 MAE | 평균 피부 SSIM | 평균 highpass MAE | 최종 피부 MAE | 최종 피부 SSIM | 최종 highpass MAE |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for name in p04:
        v=s[name]['skin']['3']
        lines.append('| '+name+' | '+' | '.join(f'{v[e][metric]:.6f}' for e in ('mean','final') for metric in ('mae','ssim','highpass_mae'))+' |')
    lines += ['', 'P04 once의 sigma3 최종 얼굴 LPIPS는 순차보다 조금 작지만 피부 표본 MAE는0.085133 대0.068484로 크고 SSIM은0.573201 대0.596945로 작다. 넓은 얼굴 ROI와 작은 피부 표본의 비교 대상이 달라 최종 우열이 지표/ROI에 의존한다. 각 피부 ROI 및 sigma1/6 결과도 summary/rows에 보존했다.','',
              '## 마지막 재생성과 direct-one-shot','',
              'end-only deliverable 곡선은 순차1–9단계 + 마지막 원본 재생성10단계다. workflow는 원래 순차10단계 호출도 소비한 뒤 재생성하므로11회다. 같은 최종 출력은 최종 요구를 처음부터 모두 알 때 원본에 직접 적용하는1회 결과로도 쓸 수 있으나, 그1회는 순차 수정 workflow를 수행한 비용이 아니다.','',
              '| 원본/경로 | 순차 고정 최종 | end/direct 고정 최종 | 순차 정합 최종 | end/direct 정합 최종 | workflow / direct 호출 |',
              '|---|---:|---:|---:|---:|---:|']
    for person,direct in d['direct_one_shot'].items():
        before=s[person]['face'];after=s[person+'-end-only']['face']
        lines.append(f'| {person} | {before["fixed"]["final"]["lpips"]:.6f} | {after["fixed"]["final"]["lpips"]:.6f} | {before["3"]["final"]["lpips"]:.6f} | {after["3"]["final"]["lpips"]:.6f} | 11 / 1 |')
    lines += ['', 'P03-r1/r2의 end/direct 최종은 같은 원본·같은 요구에서 나온 한 장이다. P04의 end/always-original/every-triggered 최종도 같은 한 장이다. 이 공유는 정해진 재사용 규칙으로 생겼으며 독립 반복이나 우연한 재현을 뜻하지 않는다.', '',
              'P01 마지막 재생성은 고정 LPIPS가0.270484→0.276156으로 커지지만 정합은0.261778→0.170199로 작아진다. P05 마지막 재생성은 고정0.235683에서 sigma3 정합0.577223으로 커지며(dx=39, dy=−1, NCC=0.592770), 순차 대비 차이도 정합 뒤 크게 줄어든다. NCC가 선택한 위치는 LPIPS를 최소화하는 위치가 아니며 형상·배경·밝기 변화가 남는다.','',
              '## 정합 진단과 해석 제한','',
              f'신규25개에서 sigma1/3/6 탐색 경계 도달은 각각 {d["new_output_registration"]["boundary_hits"]["1"]}/{d["new_output_registration"]["boundary_hits"]["3"]}/{d["new_output_registration"]["boundary_hits"]["6"]}개다. sigma 사이 축별 이동 범위>3px는1개(P03 end)이며 최대4px다. 이는 설정 민감도이고 실제 정합 정확도나 피부 판단의 신뢰도 검증은 아니다.', '',
              '첫 재생성의 낮은 고정 LPIPS가 이어지는 편집에서 지속되지 않는 현상은 세 원본에서 관측되었다. 그러나 이후 품질·경보의 변화는 단일 출력 경로이며, 개입의 인과 효과나 확률적 일반화 성능을 추정하지 않는다. P05 실패로 once3개 중2개만10단계 완결되었으므로 완료 사례만 이용해 once 평균 성능을 일반화하지 않는다.', '',
              '모든 원본은6인물이고 P03 두 반복·경로 내 단계·정책 간 공유 출력은 의존적이다. 얼굴 ROI에는 피부 외 구조가 포함되며, P04 피부 ROI는 수동 표본 세 영역이다. 낮은 원본 차이는 자연스러움·요구 충족·정체성 유지의 정답이 아니다. 이번 분석에서는 평가 원문/라벨을 사용하지 않았고 정합 임계값 적용·임계값 재보정·새 detector 학습·p값·관측되지 않은 단계 추정을 하지 않았다.','',
              '## 파일과 실행','',
              '- manifest.json:25성공/1실패와113고유 지표의 원본·호출·수식·환경 해시.',
              '- results.json:113고유의 전 설정 지표,20경로198단계, 정책 평균/최종/관측부분값, 호출 ledger, 재경보, direct-one-shot.',
              '- curves.csv:198관측 단계×4설정=792행의 얼굴 지표.',
              '- metric-cache.json / cache-status.json:처음 저장된 출력의 증분 계산 cache와 수집 snapshot.',
              '- test_integrity.py / validation.json:16개 검증과 실행 로그.',
              '- artifact-hashes.json:이 디렉터리 납품 파일 SHA256.','',
              '프로젝트 루트에서 확정된 수집을 재현:', '', '```sh',
              '.venv-metrics/bin/python experiments/nonhuman-followup-v1/extension-metrics/analyze.py --finalize',
              '.venv-metrics/bin/python experiments/nonhuman-followup-v1/extension-metrics/report.py','```']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    calc.save('artifact-hashes.json',{p.name:calc.sha(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name!='artifact-hashes.json'})
    print(json.dumps({'tests':run.testsRun,'passed':run.wasSuccessful(),'report':str(ROOT/'RESULTS.md')},ensure_ascii=False))


if __name__=='__main__':main()
