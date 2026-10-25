"""Slide content and evidence references, independent of Google authentication."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/kimmireu0220/inha-capstone'
IMAGE_COMMIT = '2020a10'
PROMPT_IMAGE_COMMIT = '66723f7'
IDS = ['p1', 'capstone_real_design_v2', 'capstone_real_results_v2',
       'capstone_real_failure_v2', 'capstone_state_design_v2',
       'capstone_state_results_v2', 'capstone_state_limits_v2',
       'capstone_format_results_v1', 'p24', 'p25']
SOURCES = ['paper/manuscript.ko.md', 'paper/evidence.json',
           'paper/figures/figure-provenance.json',
           'experiments/request-contract-v3/results.json',
           'experiments/isolated-contract-v1/results.json',
           'experiments/contract-image-v3/summary.json',
           'experiments/contract-image-review-v1/summary.json',
           'experiments/keep-image-v1/summary.json',
           'experiments/compound-edit-v1/summary.json',
           'experiments/clause-normalization-v1/results.json',
           'experiments/paraphrase-contract-v1/results.json',
           'experiments/clause-factorial-v1/results.json',
           'experiments/clause-factorial-v1/summary.json',
           'experiments/clause-normalization-v1/plain-patch-comparison.json',
           'experiments/clause-normalization-v1/invariant-audit.json',
           'experiments/instruction-transfer-v1/results.json',
           'experiments/instruction-transfer-v1/summary.json',
           'experiments/instruction-transfer-v1/verification.json',
           'experiments/operation-scope-validation-v1/summary.json',
           'experiments/instruction-eligibility-validation-v1/summary.json',
           'experiments/single-extraction-validation-v1/summary.json',
           'experiments/single-extraction-validation-v1/verification.json',
           'experiments/instruction-eligibility-v1/development-replay.json',
           'experiments/instruction-eligibility-v1/invariant-audit.json',
           'paper/implementation-verification.json',
           'paper/initial-portrait-verification.json',
           'experiments/prompt-state-image-v1/summary.json',
           'experiments/prompt-state-image-v1/verification.json',
           'paper/figures/prompt-state-image-provenance.json']


def load(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec():
    """Editable text/table specifications. Numerical rows come from evidence."""
    s = load(SOURCES[3])['methods']
    def rows(data, methods):
        result = [['방법', '전체 상태 일치율', '최종 상태 일치율', '유지 위반 수']]
        for key, label in methods:
            r = data[key]
            result.append([label, f"{r['exact_turns']}/{r['turns']}",
                           f"{r['exact_final_dialogues']}/8", str(r['newly_corrupted_unchanged_slots'])])
        return result
    first, second = load(SOURCES[5])['by_mode'], load(SOURCES[6])['by_mode']
    compound = load(SOURCES[8])
    final = load('experiments/single-extraction-validation-v1/summary.json')['metrics']
    final_rows = [['방법', '전체 상태 일치율', '요청당 호출 수', '최종 상태 일치율']]
    for model, name in [('qwen3', 'Qwen3'), ('llama32', 'Llama')]:
        for method, label in [('eligible_normalization', '추출·재검토+검사'), ('single_extraction_checked', '한 번 추출+검사')]:
            data = final[model][method]
            final_rows.append([name+' '+label, f"{data['exact_turns']}/12", str(data['required_model_calls_per_request']), f"{data['exact_final_dialogues']}/3"])
    mixed_review = compound['groups']['review']['mixed']['exact_turns']
    mixed_guarded = compound['groups']['guarded']['mixed']['exact_turns']
    images = [['AI 항목별 충족률', '기준 방법', '유지·삭제 결합']]
    for data, label in [(first, '1차 3B'), (second, '사후 7B')]:
        images.append([label] + [f"{data[m]['goals_satisfied']}/{data[m]['goal_denominator']}" for m in ['baseline_restore', 'keep_remove']])
    image_summary = load('experiments/prompt-state-image-v1/summary.json')
    comparison_rows = [['입력 방식', '평균 토큰 수', '7B 목표 충족', '얼굴\n코사인↑']]
    for mode, label in [('full_history','전체 요청 이력'), ('unchecked_state','검사 전 현재 조건'), ('checked_state','지시 검사 후 현재 조건')]:
        comparison_rows.append([label, f"{image_summary['prompt_lengths'][mode]['tokens']:.2f}",
                                f"{image_summary['secondary_by_mode'][mode]['goals_satisfied']}/36",
                                f"{image_summary['by_mode'][mode]['identity_mean']:.6f}"])
    return [
        dict(title='반복 인물 이미지 편집에서\n지시 검사를 이용한 상태 갱신',
             body='변경 사항을 한 번 추출하고 지시를 검사하여 편집 조건을 저장\n\n김미르 · 장윤석\n지도교수 안남혁',
             foot='종합설계 연구 발표',
             notes='처음에는 편집 대화 전체를 언어 모델에 주고 최종 프롬프트를 작성했습니다. 이때 취소한 의상과 장신구 조건이 다시 남았습니다. 그래서 편집 조건을 항목별로 저장하고, 유지·삭제 지시를 확인한 뒤 프롬프트를 작성하도록 바꿨습니다. 복원할 대상과 유지할 대상이 섞이는 오류는 두 지시를 나누어 처리하도록 고쳤습니다.'),
        dict(title='반복 편집과 원본 기반 생성의 비교',
             body='합성 인물 6명에게 각각 같은 10단계 편집\n순차 편집의 얼굴 LPIPS 평균: 0.042116 → 0.364015\n\n위치 보정 MAE·SSIM·LPIPS: 최종 6쌍 모두 원본 기반에 유리\n원본에 적용할 현재 조건을 정확하고 간결하게 정리',
             foot='순차 편집: 직전 출력을 재편집 / 원본 기반: 최초 사진에 현재 조건 적용',
             notes='초기 실험은 합성 인물 여섯 명에게 장신구·의상·배경 편집 열 단계를 적용한 기록입니다. 같은 최종 요구에서 순차 최종과 원본 기반 출력을 비교했습니다. 원본에서 고정한 320×360 얼굴 영역의 위치를 NCC ±64픽셀, sigma 3으로 보정했습니다. MAE·LPIPS는 낮을수록, SSIM은 높을수록 원본과 가깝습니다. 세 지표 모두 여섯 쌍에서 원본 기반에 유리했고 위치 보정 전에는 각각 다섯 쌍이었습니다. sigma 1과 6에서도 여섯 쌍의 방향이 유지됐습니다. 원본과 최종 출력의 해시와 수치 재계산을 대조했습니다. 이 결과는 입력 사진 선택의 비교이며 긴 프롬프트가 얼굴 변화의 원인이라는 인과 증거와 구분합니다. 이후 한 번 추출 조건은 첫 응답만 사용하여 현재 상태를 갱신하고 프롬프트를 작성합니다. '+REPO+'/blob/main/experiments/nonhuman-followup-v1/RESULTS.md'),
        dict(title='유지 규칙과 삭제 규칙의 비교',
             intro='미리 정한 영어 대화 8개, 요청 32개. 같은 모델 응답 64개에 규칙 적용',
             table=rows(s, [('baseline_restore','기준 방법'),('keep_only','유지 규칙만'),('remove_only','삭제 규칙만'),('keep_remove','유지·삭제 결합')]),
             foot='전체 상태는 요청 처리 후, 최종 상태는 대화 종료 후 평가\n유지 위반 수는 직전까지 맞았고 그대로 둘 항목을 잘못 바꾼 횟수',
             notes='이 표는 추출·재검토 응답을 사용하는 초기 유지·삭제 구성요소 비교입니다. 전체 상태 일치율은 모든 항목이 정답과 일치한 요청의 비율입니다. 최종 상태 일치율은 마지막 요청 처리 후 모든 항목이 일치한 대화의 비율입니다. 27/32는 요청 32개 중 27개에서 여섯 항목 모두 맞았다는 뜻입니다. 세 번째 대화의 세 번째 요청에서는 삭제 규칙이 식물 삭제 누락을 막았습니다. 네 번째 요청에서는 유지 규칙이 배경을 잘못 바꾸는 것을 막았습니다. 두 규칙을 결합해야 두 요청 모두 정답과 일치했습니다. 일곱 번째 대화는 모든 방법에서 요청 네 개 중 하나만 맞았습니다. 맞은 항목 수는 표의 방법 순서대로 184, 185, 186, 187개이며 전체 항목 수는 192개입니다. 연구를 위해 만든 영어 대화로 검사했습니다. '+REPO+'/blob/main/experiments/request-contract-v3/RESULTS.md'),
        dict(title='두 모델에서 한 번 추출하는 방법의 결과',
             intro='새 합성 대화 3개, 요청 12개를 두 모델에 각각 적용',
             table=final_rows,
             foot='같은 최초 응답을 단순 JSON으로 적용하면 두 모델 모두 3/12\n호출 수는 방법 실행에 필요한 모델 호출 횟수',
             notes='후처리와 자료를 고정한 뒤 새 대화 세 개, 서로 다른 요청 열두 개로 검증했습니다. 표의 두 번 호출 조건은 추출·재검토 응답에 같은 지시 검사를 적용했고, 한 번 조건은 첫 응답만 사용했습니다. Qwen3는 각각 12/12, Llama는 각각 4/12와 12/12였습니다. 단순 JSON 최초 응답은 두 모델 모두 3/12였으므로 첫 응답 선택과 지시 검사 모두의 효과를 비교했습니다. 한 번 추출 조건은 두 모델 모두 항목별 72/72, 최종 상태 3/3, 추가 오류 0개였습니다. 전체 비교를 위한 실제 모델 호출은 모델별 24회, 총 48회입니다. 실험에서 보관한 재검토 응답은 한 번 추출 조건의 점수 계산에 사용하지 않았습니다. '+REPO+'/blob/main/experiments/single-extraction-validation-v1/RESULTS.md'),
        dict(title='실제 인물 R01: 식물 삭제와 배경 유지', person='R01',
             foot='원본: Monstera Production / Pexels. 의상·장신구·배경은 AI 편집 결과.',
             notes='두 방법의 편집 입력이 달랐던 두 쌍입니다. 세 번째 요청에서는 식물을 삭제하고 재킷은 유지하도록 했습니다. 네 번째 요청에서는 상의와 목걸이를 원본으로 돌리되 재킷과 연한 파란 배경은 유지하도록 했습니다. 각 이미지의 전체 영역을 보여 줍니다. Pexels 공개 사진을 사용했고 의상·장신구·배경은 AI로 편집했습니다. 원본 https://www.pexels.com/photo/confident-black-man-in-studio-6311573/\n'+REPO+'/blob/main/paper/figures/figure-provenance.json'),
        dict(title='전체 요청과 현재 조건으로 생성한 결과', comparison_images=True,
             foot='실제 인물 R02 · 같은 원본과 네 개 요청 · 조건부 지시와 인용문을 포함한 예',
             notes='왼쪽부터 요청 전체 이력, 검사 전 현재 조건, 지시 검사 후 현재 조건으로 원본 사진에서 각각 한 번 생성했습니다. 이 대화는 녹색 재킷과 흰 상의, 파란 핀, 원본 목걸이, 도서관과 돌 벤치를 요구합니다. 조건부 소품 삭제와 캡션 속 재킷 복원은 실행하지 않고 뒤의 직접 지시를 반영해야 합니다. 전체 평가는 대화 세 개와 인물 두 명의 18조건을 사용했습니다. 세 장은 조건부·인용 대화의 예시이며 집계에는 다른 대화도 모두 포함합니다. 원본 Monstera Production / Pexels photo 6311581. '+REPO+'/blob/main/experiments/prompt-state-image-v1/RESULTS.md'),
        dict(title='이미지 평가 점수와 판정 오류',
             intro='인물 사진 2장 × 요청 32개 × 두 방법 = 생성 조건 128개, 실제 이미지 66개',
             table=images,
             below='3B에서 늘어난 성공 항목 8개 중 6개는 판단 불가에서 바뀐 항목\n7B에서도 설명과 점수가 일치하지 않는 사례 발생',
             foot='방법별 64개 생성 조건에서 여섯 항목씩 평가\n비교 64쌍 중 입력이 다른 경우는 4쌍이며, 나머지 60쌍은 같은 이미지 사용',
             notes='항목별 충족률은 성공 판정 항목 수를 전체 항목 수로 나눈 값입니다. 서로 다른 이미지와 평가 목표의 조합은 68개입니다. 3B의 판단 불가는 기준 20개, 결합 13개였고 응답 형식 오류는 3개였습니다. 이를 확인한 뒤 같은 계열의 7B 모델로 전체를 다시 평가했습니다. 7B에서는 형식 오류와 판단 불가가 각각 0개였지만 설명과 점수의 불일치는 남았습니다. 두 모델이 공통으로 실패에서 성공으로 판정한 것은 R02의 네 번째 요청에서 배경 한 항목입니다. 얼굴 유사도 평균은 기준 '+f"{first['baseline_restore']['face_mean']:.6f}, 결합 {first['keep_remove']['face_mean']:.6f}"+'입니다. 입력이 다른 네 쌍 중 두 쌍은 높아지고 두 쌍은 낮아졌습니다. 이미지 결과와 평가 모델의 판정 차이를 함께 분석했습니다. '+REPO+'/blob/main/experiments/contract-image-review-v1/INTERPRETATION.md'),
        dict(title='표정·포즈와 다른 편집 지시를 함께 요청한 결과',
             body='요청 구성 4가지 × 조건 3가지 × 요청 4개 = 요청 48개\n표정만, 표정·포즈 조건은 모든 방법에서 16/16\n'+f'속성 지시 혼합은 재검토 {mixed_review}/16, 규칙 보정 {mixed_guarded}/16\n\n삭제를 원본 복원으로 해석한 오류를 바로잡음',
             foot='아홉 항목 모두 맞은 요청 수/전체 요청 수. 삭제 규칙만 적용해도 같은 결과',
             notes='최초 추출, 재검토, 재검토 뒤 규칙 보정을 비교했습니다. 최초 추출은 요청당 한 번, 나머지는 두 번 모델을 호출합니다. 기존 여섯 항목에 몸 방향·손동작·표정을 더했고, 어휘와 구현을 새로 고정했습니다. 포즈와 표정은 모든 방법에서 조건별 48항목 모두 맞았습니다. 다른 속성 지시까지 함께 요청한 조건에서는 최초 추출과 재검토가 각각 4/16, 규칙 보정이 16/16이었습니다. 모델은 두 번째 요청의 식물 삭제와 세 번째 요청의 목걸이 삭제를 원본 복원으로 잘못 해석했습니다. 이 오류가 이후 요청에도 남아 항목 오류 20개가 발생했습니다. 오류를 확인한 뒤 삭제 규칙만 적용해 다시 계산해도 전체 48개 요청이 맞았습니다. 정확한 요청으로 생성한 이미지 6장의 평가에는 응답 형식 오류 두 개와 몸 방향의 설명·점수 불일치 네 개가 있었습니다. '+REPO+'/blob/main/experiments/compound-edit-v1/RESULTS.md'),
        dict(title='프롬프트 길이와 생성 이미지 지표',
             intro='실제 인물 2명 × 대화 3개 × 입력 방식 3개 = 이미지 18장',
             table=comparison_rows,
             below='마지막 요청의 프롬프트 길이 39.87% 감소\n얼굴 LPIPS↓: 전체 이력 0.095158 / 검사 후 0.106698',
             below_y=373, below_size=18, below_h=75,
             foot='토큰: Qwen3 기준·보존 문구 포함 / 코사인↑·LPIPS↓ / 목표 평가: Qwen2.5-VL-7B',
             notes="전체 요청 이력·검사 전 현재 조건·지시 검사 후 현재 조건을 같은 원본 사진에서 생성했습니다. Qwen3 최초 응답의 세 대화를 실제 인물 두 명에게 적용한 18조건이며 새 언어 검증과 구분합니다. 프롬프트는 공통 보존 문구를 포함하여 고정 Qwen3 토크나이저로 측정했습니다. 첫 요청에서는 상태 표현이 더 길었고 마지막 요청에서 평균 39.87% 줄었습니다. 3B 결과는 {'full_history': (29, 6), 'unchecked_state': (18, 18), 'checked_state': (30, 6)}입니다. 각 쌍은 성공 항목 수와 판단 불가 수입니다. 3B 형식 오류와 잘못된 설명을 관찰한 뒤 7B로 전체 18장을 사후 대조했습니다. 7B의 판단 불가 수는 {'full_history': 0, 'unchecked_state': 2, 'checked_state': 0}입니다. 원문 점수는 교체하지 않았습니다. 얼굴 랜드마크를 기준으로 정렬한 112×112 얼굴에서 MAE·SSIM·LPIPS를 계산했습니다. 전체 이력과 비교하면 지시 검사 후 얼굴 코사인은 높았고 나머지 세 지표는 불리했습니다. 프롬프트 길이와 얼굴 품질의 일률적인 개선은 구분합니다. https://github.com/kimmireu0220/inha-capstone/blob/main/experiments/prompt-state-image-v1/RESULTS.md"),
        dict(title='연구 결과와 적용 범위',
             body='원본 사진에 현재 편집 조건을 적용\n새 요청 12개: 두 모델 모두 3/12에서 12/12\n상태 갱신에 필요한 모델 호출은 요청당 1회\n전체 이력을 현재 조건으로 정리해 입력 길이를 줄임\n얼굴 지표의 변화 방향은 측정 항목에 따라 다름',
             foot='명시한 영어 표현과 여섯 편집 항목의 결과',
             notes='복원 표현 검증은 새 대화 8개, 요청 32개입니다. Qwen3 기준 14/32와 개선 28/32, Llama 기준 7/32와 개선 17/32였습니다. 실행 대상 검사 검증은 새 대화 4개, 요청 16개입니다. Qwen3 기준 9/16, 복원 표현 개선 11/16, 실행 검사 16/16이었고 Llama는 세 조건 모두 0/16이었습니다. 개발 자료 32개에서 한 번 추출과 지시 검사는 Qwen3 32/32, Llama 27/32였고 두 번 호출한 검사 결합은 각각 32/32와 19/32였습니다. 이후 고정한 새 요청 12개에서는 두 모델 모두 한 번 추출과 지시 검사가 12/12였습니다. 두 번 호출한 검사 결합은 Qwen3 12/12, Llama 4/12였습니다. 제안 방법 실행에는 호출 한 번이 필요합니다. 실험에서는 비교를 위해 최초와 재검토 응답을 모두 기록했습니다. 세 검증의 실제 호출은 두 모델을 합쳐 각각 128회, 64회, 48회이며 분모는 각각 모델별 32, 16, 12개입니다.\nhttps://github.com/kimmireu0220/inha-capstone/blob/main/experiments/operation-scope-validation-v1/RESULTS.md\nhttps://github.com/kimmireu0220/inha-capstone/blob/main/experiments/instruction-eligibility-validation-v1/RESULTS.md\nhttps://github.com/kimmireu0220/inha-capstone/blob/main/experiments/single-extraction-validation-v1/RESULTS.md 코드 검사 1323개는 직접 구성한 상태 검사입니다. 초기 6인물 결과에서 원본 기반 구성을 선택한 뒤 현재 조건 정리와 후속 이미지 18장을 비교했습니다. 첫 응답을 사용해 재검토의 오류를 피하는 방식의 상태 정확도와 프롬프트 길이를 검증했습니다.')
    ]


def image_label(index):
    """One publication label shared by the writer and readback verifier."""
    return f"요청 {3+index//2}  {'기준 방법' if index%2==0 else '유지·삭제'}"


def image_sources(item):
    """Full source photographs with per-study immutable publication revisions."""
    if item.get('comparison_images'):
        provenance = load('paper/figures/prompt-state-image-provenance.json')
        labels = ['전체 요청 이력', '검사 전 현재 조건', '지시 검사 후 현재 조건']
        return [{**r, 'label': label, 'url': f'https://raw.githubusercontent.com/kimmireu0220/inha-capstone/{PROMPT_IMAGE_COMMIT}/'+r['source']}
                for r, label in zip(provenance['sources'], labels)]
    if 'person' in item:
        figure = next(f for f in load(SOURCES[2])['figures'] if item['person'] in f['figure'])
        return [{**r, 'label': image_label(j), 'url': f'https://raw.githubusercontent.com/kimmireu0220/inha-capstone/{IMAGE_COMMIT}/'+r['source']}
                for j, r in enumerate(figure['sources'])]
    return []
