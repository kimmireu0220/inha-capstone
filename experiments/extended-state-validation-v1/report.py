"""Recompute frozen results and paired dialogue-level uncertainty."""
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from run import ROOT, REPO, freeze, previous, save

sys.path.insert(0, str(REPO/'local-studio'))
from instruction_pipeline import process_request


METHODS = [('json_first_only', '첫 응답만 적용'),
           ('json_review_then_first', '재검토 응답 우선'),
           ('eligible_normalization', '추출·재검토+검사'),
           ('single_extraction_checked', '한 번 추출+검사')]


def paired_statistics(a, b, draws=20000, seed=20261025):
    """All rows in a dialogue stay together for estimation and testing."""
    difference = np.asarray(a, dtype=float)-np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(difference), size=(draws, len(difference)))
    boot = difference[indices].mean(axis=1)
    observed = abs(difference.mean())
    extreme = sum(abs(np.mean(difference*np.asarray(signs))) >= observed-1e-12
                  for signs in itertools.product([-1, 1], repeat=len(difference)))
    return dict(difference_percentage_points=float(difference.mean()*100),
                bootstrap_95_percentage_points=[float(x*100) for x in np.quantile(boot, [.025, .975])],
                permutation_p=extreme/(2**len(difference)),
                units=len(difference), bootstrap_draws=draws, seed=seed)


def holm(values):
    ordered = sorted(values, key=values.get)
    adjusted, floor = {}, 0
    for i, name in enumerate(ordered):
        floor = max(floor, min(1., (len(values)-i)*values[name]))
        adjusted[name] = floor
    return adjusted


def base_initial():
    from request_state import INITIAL
    return INITIAL


def main():
    frozen = json.loads((ROOT/'frozen.json').read_text())
    assert frozen == freeze(), 'Frozen inputs changed'
    benchmark = json.loads((ROOT/'benchmark.json').read_text())
    histories = benchmark['histories']
    metrics, comparisons, categories, failures, by_dialogue = {}, {}, {}, {}, {}
    for model in frozen['models']:
        transcripts = json.loads((ROOT/f'transcripts-{model}.json').read_text())
        results = json.loads((ROOT/f'results-{model}.json').read_text())
        attempts = json.loads((ROOT/f'attempts-{model}.json').read_text())
        assert len(transcripts) == 96
        assert all('first' in r and 'second' in r for r in transcripts.values())
        assert results['methods'] == previous.score(histories, transcripts)
        assert sum(a['status'] == 'completed' for a in attempts) == 192
        # Replay saved model outputs through the actual user-facing pipeline.
        proposed_rows = iter(results['methods']['single_extraction_checked']['rows'])
        for name, requests in histories.items():
            state = dict(base_initial())
            for i, item in enumerate(requests, 1):
                raw = transcripts[f'{name}-{i}']['first']
                class SavedExtractor:
                    calls = 0
                    def ask(self, system, request, max_tokens, examples):
                        self.calls += 1
                        assert request == item['request'] and max_tokens == 260
                        return raw
                extractor = SavedExtractor()
                replay = process_request(state, item['request'], extractor)
                assert extractor.calls == replay['model_calls'] == 1
                assert replay['state'] == next(proposed_rows)['observed']
                state = replay['state']
        metrics[model], categories[model], failures[model], by_dialogue[model] = {}, {}, {}, {}
        for method, _ in METHODS:
            data = results['methods'][method]
            metrics[model][method] = {k:v for k,v in data.items() if k != 'rows'}
            grouped = {name: [] for name in histories}
            cat = {}
            errors = []
            for row in data['rows']:
                name, index = row['dialogue'], row['turn']-1
                category = histories[name][index]['category']
                grouped[name].append(int(row['exact']))
                item = cat.setdefault(category, dict(correct=0, total=0))
                item['correct'] += int(row['exact'])
                item['total'] += 1
                if not row['exact']:
                    errors.append(dict(dialogue=name, request_index=index+1,
                        category=category, request=histories[name][index]['request'],
                        expected=row['expected'], observed=row['observed']))
            categories[model][method] = cat
            failures[model][method] = errors
            by_dialogue[model][method] = {name:sum(rows)/len(rows) for name,rows in grouped.items()}
        proposed = by_dialogue[model]['single_extraction_checked']
        comparisons[model] = {}
        for comparator, _ in METHODS[:-1]:
            baseline = by_dialogue[model][comparator]
            comparisons[model][comparator] = paired_statistics(
                [proposed[n] for n in histories], [baseline[n] for n in histories])
            proposed_rows = results['methods']['single_extraction_checked']['rows']
            comparator_rows = results['methods'][comparator]['rows']
            comparisons[model][comparator]['discordant_requests'] = dict(
                proposed_only=sum(a['exact'] and not b['exact'] for a,b in zip(proposed_rows, comparator_rows, strict=True)),
                comparator_only=sum(b['exact'] and not a['exact'] for a,b in zip(proposed_rows, comparator_rows, strict=True)))
    # The predeclared primary comparison is checking versus the same first response.
    adjusted = holm({m: comparisons[m]['json_first_only']['permutation_p'] for m in metrics})
    for model in metrics:
        comparisons[model]['json_first_only']['holm_p_two_models'] = adjusted[model]
    paths = ['benchmark.json','frozen.json','run.py','report.py','test_design.py','test_report.py','PROTOCOL.md']
    for model in metrics:
        paths += [f'transcripts-{model}.json',f'attempts-{model}.json',f'results-{model}.json']
    sources = {str((ROOT/p).relative_to(REPO)):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    sources['local-studio/instruction_pipeline.py'] = hashlib.sha256((REPO/'local-studio/instruction_pipeline.py').read_bytes()).hexdigest()
    summary = dict(analysis_libraries={'numpy':np.__version__}, production_pipeline_replays=192, replay_additional_model_calls=0, complete=True, requests=96, dialogues=12, requests_per_dialogue=8,
        template_families=4, completed_responses=384,
        model_attempts=sum(len(json.loads((ROOT/f'attempts-{m}.json').read_text())) for m in metrics),
        metrics=metrics, by_category=categories, by_dialogue=by_dialogue,
        paired_comparisons=comparisons, failures=failures)
    save(ROOT/'summary.json', summary)
    verification = dict(passed=True, source_sha256=sources,
         frozen_inputs_verified=frozen['sha256'], summary_sha256=hashlib.sha256((ROOT/'summary.json').read_bytes()).hexdigest(),
         requests=96, completed_responses=384)
    lines = ['# 96개 새 요청에 대한 고정 코드 검증', '',
             '합성 영어 대화 12개에 요청을 여덟 개씩 적용하였다. 네 가지 표현 틀에 속성 조합을 바꾼 자료이며, 동일한 96개 요청을 두 모델에 각각 입력하였다. 기존 방법과 모델 설정을 고정한 뒤 최초 추출·재검토 응답 384개를 모두 저장하였다.', '',
             '| 모델 | 방법 | 전체 상태 일치 | 항목별 일치 | 최종 상태 일치 |',
             '| --- | --- | --- | --- | --- |']
    for model, label in [('qwen3','Qwen3-4B'),('llama32','Llama-3.2-3B')]:
        for method, name in METHODS:
            d = metrics[model][method]
            lines.append(f"| {label} | {name} | {d['exact_turns']}/96 | {d['correct_slots']}/576 | {d['exact_final_dialogues']}/12 |")
    lines += ['', 'Llama의 오류 세 개는 같은 표현 틀의 마지막 요청에서 인용문 뒤에 나온 재킷 원본 복원을 놓친 사례이다. 모델이 반환한 녹색 변경은 거부했지만 복원을 적용하지 못해 직전 재킷 값이 남았다. 세 대화의 최종 상태에도 같은 오류가 반영되었다.', '', '## 대화 단위 대응 비교', '',
              '제안 방법과 첫 응답 단순 적용의 차이를 대화 단위로 분석하였다. 95% 구간은 대화 12개를 20000회 복원 추출한 백분위 구간이며, p값은 4096개 부호 조합의 양측 무작위화 검정이다. 두 모델의 주 비교에 Holm 보정을 적용하였다.', '',
              '| 모델 | 정확도 차이(%p) | 95% 구간(%p) | 보정 p값 |', '| --- | --- | --- | --- |']
    for model in metrics:
        d = comparisons[model]['json_first_only']; lo,hi=d['bootstrap_95_percentage_points']
        lines.append(f"| {model} | {d['difference_percentage_points']:.2f} | {lo:.2f}–{hi:.2f} | {d['holm_p_two_models']:.6f} |")
    lines += ['', '저장한 첫 응답 192개를 실제 instruction_pipeline.py에도 재생하여 실험 채점과 상태가 모두 일치함을 확인하였다. 재생에는 모델을 추가 호출하지 않았다.', '', '표현 틀을 공유하는 합성 자료이므로 대화 단위 구간은 이 자료 안에서의 변동을 나타낸다. 요청 유형별·대화별 결과와 모든 오류는 summary.json에 보존하였다. 이미지 품질 비교는 별도의 이미지 실험 결과를 따른다.', '']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines))
    sources[str((ROOT/'RESULTS.md').relative_to(REPO))] = hashlib.sha256((ROOT/'RESULTS.md').read_bytes()).hexdigest()
    save(ROOT/'verification.json', verification)
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
