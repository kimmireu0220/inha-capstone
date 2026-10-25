"""Slide content and evidence references, independent of Google authentication."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/kimmireu0220/inha-capstone'
IMAGE_COMMIT = '2020a10'
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
           'paper/implementation-verification.json']


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
    return [
        dict(title='반복 인물 이미지 편집에서\n지시 검사를 이용한 상태 갱신',
             body='변경 사항을 한 번 추출하고 지시를 검사하여 편집 조건을 저장\n\n김미르 · 장윤석\n지도교수 안남혁',
             foot='종합설계 연구 발표',
             notes='처음에는 편집 대화 전체를 언어 모델에 주고 최종 프롬프트를 작성했습니다. 이때 취소한 의상과 장신구 조건이 다시 남았습니다. 그래서 편집 조건을 항목별로 저장하고, 유지·삭제 지시를 확인한 뒤 프롬프트를 작성하도록 바꿨습니다. 복원할 대상과 유지할 대상이 섞이는 오류는 두 지시를 나누어 처리하도록 고쳤습니다.'),
        dict(title='요청을 편집 조건으로 정리하는 과정',
             body='1. 현재 요청에서 변경 사항을 한 번 추출\n2. 복원·유지·삭제 지시가 가리키는 항목을 구분\n3. 실행할 지시와 부정·조건·인용 범위를 검사\n4. 상태를 갱신하고 이미지 편집 프롬프트 작성',
             foot='재킷·상의·핀·목걸이·배경·소품의 여섯 항목을 저장한다. 같은 모델 응답으로 방법을 비교한다.',
             notes='편집 상태는 지금까지의 요청에 따라 항목마다 저장한 조건입니다. 제안 방법은 현재 요청에서 변경 사항을 한 번 추출합니다. 같은 첫 응답에 지시 구절 정규화와 실행 대상 검사를 적용하고, 직전까지 저장한 상태를 이어서 갱신합니다. 비교 실험에서는 재검토 응답도 저장했지만 한 번 추출 조건은 첫 응답만 사용했습니다. 유지 지시는 직전 값을 보존하고 삭제 지시는 값을 없음으로 바꿉니다. 원본 복원은 최초 사진의 상태로 돌리는 것입니다. 뜻이 같은 지시를 정해진 문장 형태로 바꾸는 처리를 정규화라고 합니다. 정답은 결과를 채점할 때만 사용했습니다. 항목별 상태를 저장하는 구성은 ChatEdit를 참고했습니다. https://aclanthology.org/2023.emnlp-main.899/'),
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
        dict(title='실제 인물 R02: 같은 요청의 편집 결과', person='R02',
             foot='원본: Monstera Production / Pexels. 의상·장신구·배경은 AI 편집 결과.',
             notes='R02에도 같은 대화의 세 번째와 네 번째 요청을 적용했습니다. 3B 모델은 세 번째 요청의 기준 이미지를 평가할 때 JSON 대신 느낌표를 출력했습니다. 7B 모델에서도 식물에 대한 설명과 점수가 일치하지 않았습니다. 다음 장에서 평가 점수와 오류를 함께 설명합니다. 원본 https://www.pexels.com/photo/cheerful-black-woman-in-studio-6311581/\n'+REPO+'/blob/main/paper/figures/figure-provenance.json'),
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
        dict(title='재검토 오류와 지시 검사',
             body='최초 추출은 여섯 항목을 맞게 반환\nLlama 재검토가 목걸이 삭제만 반환한 사례\n\n복원·유지 대상과 현재 실행할 지시를 검사\n첫 응답을 사용해 재검토의 오류를 피함',
             foot='명시한 영어 표현과 여섯 상태 항목을 사용하는 방법',
             notes='Llama의 새 요청 16개 검증에서는 초기 설정 네 개의 최초 응답이 모두 정확했지만 재검토가 목걸이 삭제 등 일부 항목만 반환했습니다. 이후 상태에도 오류가 남아 두 번 호출한 실행 대상 검사 방법은 0/16이었습니다. 첫 응답을 단순 적용한 결과는 8/16이었습니다. 이 결과를 보존하고 한 번 추출하는 방법을 새 요청 12개로 검증했습니다. 복원 표현은 표준 지시로 바꾸고 부정·조건·캡션 속 지시에만 해당하는 변경을 막습니다. 같은 항목이 뒤의 직접 지시에 나타나면 그 지시를 적용합니다. 코드 검사 1323개는 구성한 상태 검사이며 저장한 응답 24개의 재생은 실제 실행 코드와 실험 구현을 연결한 검사입니다. 범위는 AI로 구성한 합성 영어 요청과 여섯 상태 항목입니다. https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct'),
        dict(title='구성요소 검증과 최종 결과',
             body='복원 표현 개선 32개: Qwen3 14/32에서 28/32\nLlama 7/32에서 17/32\n\n실행 대상 검사 16개: Qwen3 16/16, Llama 0/16\n한 번 추출과 지시 검사 12개: 두 모델 모두 12/12\n요청당 호출 1회, 단순 최초 응답은 각각 3/12',
             foot='각 검증은 서로 다른 새 합성 요청을 사용. 명시한 영어 문형의 결과.\n같은 요청을 두 모델에 각각 입력하고 모델별로 집계',
             notes='복원 표현 검증은 새 대화 8개, 요청 32개입니다. Qwen3 기준 14/32와 개선 28/32, Llama 기준 7/32와 개선 17/32였습니다. 실행 대상 검사 검증은 새 대화 4개, 요청 16개입니다. Qwen3 기준 9/16, 복원 표현 개선 11/16, 실행 검사 16/16이었고 Llama는 세 조건 모두 0/16이었습니다. 개발 자료 32개에서 한 번 추출과 지시 검사는 Qwen3 32/32, Llama 27/32였고 두 번 호출한 검사 결합은 각각 32/32와 19/32였습니다. 이후 고정한 새 요청 12개에서는 두 모델 모두 한 번 추출과 지시 검사가 12/12였습니다. 두 번 호출한 검사 결합은 Qwen3 12/12, Llama 4/12였습니다. 제안 방법 실행에는 호출 한 번이 필요합니다. 실험에서는 비교를 위해 최초와 재검토 응답을 모두 기록했습니다. 세 검증의 실제 호출은 두 모델을 합쳐 각각 128회, 64회, 48회이며 분모는 각각 모델별 32, 16, 12개입니다.\nhttps://github.com/kimmireu0220/inha-capstone/blob/main/experiments/operation-scope-validation-v1/RESULTS.md\nhttps://github.com/kimmireu0220/inha-capstone/blob/main/experiments/instruction-eligibility-validation-v1/RESULTS.md\nhttps://github.com/kimmireu0220/inha-capstone/blob/main/experiments/single-extraction-validation-v1/RESULTS.md')
    ]


def image_label(index):
    """One publication label shared by the writer and readback verifier."""
    return f"요청 {3+index//2}  {'기준 방법' if index%2==0 else '유지·삭제'}"
