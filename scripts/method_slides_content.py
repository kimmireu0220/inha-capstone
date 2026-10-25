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
           'experiments/instruction-transfer-v1/verification.json']


def load(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec():
    """Editable text/table specifications. Numerical rows come from evidence."""
    s = load(SOURCES[3])['methods']
    t = load(SOURCES[4])['methods']
    def rows(data, methods):
        result = [['방법', '전체 상태 일치율', '최종 상태 일치율', '유지 위반 수']]
        for key, label in methods:
            r = data[key]
            result.append([label, f"{r['exact_turns']}/{r['turns']}",
                           f"{r['exact_final_dialogues']}/8", str(r['newly_corrupted_unchanged_slots'])])
        return result
    first, second = load(SOURCES[5])['by_mode'], load(SOURCES[6])['by_mode']
    compound = load(SOURCES[8])
    normalized = load(SOURCES[9])['methods']
    structural = load(SOURCES[11])['methods']
    plain = load(SOURCES[13])['studies']['clause-factorial-v1']['review_then_first']
    transfer = load('experiments/instruction-transfer-v1/results.json')['methods']
    transfer_groups = load('experiments/instruction-transfer-v1/summary.json')['groups']['normalized_atomic']
    mixed_review = compound['groups']['review']['mixed']['exact_turns']
    mixed_guarded = compound['groups']['guarded']['mixed']['exact_turns']
    images = [['AI 항목별 충족률', '기준 방법', '유지·삭제 결합']]
    for data, label in [(first, '1차 3B'), (second, '사후 7B')]:
        images.append([label] + [f"{data[m]['goals_satisfied']}/{data[m]['goal_denominator']}" for m in ['baseline_restore', 'keep_remove']])
    return [
        dict(title='반복 인물 이미지 편집을 위한\n유지 및 삭제 지시 처리 방법',
             body='여러 번의 편집 요청을 하나의 프롬프트로 정리하는 방법\n\n김미르 · 장윤석\n지도교수 안남혁',
             foot='종합설계 연구 발표',
             notes='처음에는 편집 대화 전체를 언어 모델에 주고 최종 프롬프트를 작성했습니다. 이때 취소한 의상과 장신구 조건이 다시 남았습니다. 그래서 편집 조건을 항목별로 저장하고, 유지·삭제 지시를 확인한 뒤 프롬프트를 작성하도록 바꿨습니다. 복원할 대상과 유지할 대상이 섞이는 오류는 두 지시를 나누어 처리하도록 고쳤습니다.'),
        dict(title='요청을 편집 조건으로 정리하는 과정',
             body='1. 현재 요청에서 변경할 내용을 추출하고 재검토\n2. 복원할 대상과 유지할 대상을 구분\n3. 저장된 조건을 갱신하고 유지·삭제 지시를 확인\n4. 확인한 조건으로 원본 사진의 편집 프롬프트 작성',
             foot='재킷·상의·핀·목걸이·배경·소품의 여섯 항목을 저장한다. 같은 모델 응답으로 방법을 비교한다.',
             notes='편집 상태는 지금까지의 요청에 따라 항목마다 저장한 조건입니다. Qwen3-4B-4bit가 현재 요청에서 변경할 내용을 추출하고 한 번 재검토합니다. 모든 방법에 같은 두 응답을 사용하고, 각 방법이 직전까지 저장한 상태를 이어서 갱신합니다. 유지 지시는 직전 값을 보존하고 삭제 지시는 값을 없음으로 바꿉니다. 원본 복원은 최초 사진의 상태로 돌리는 것입니다. 뜻이 같은 지시를 정해진 문장 형태로 바꾸는 처리를 정규화라고 합니다. 정답은 결과를 채점할 때만 사용했습니다. 항목별 상태를 저장하는 구성은 ChatEdit를 참고했습니다. https://aclanthology.org/2023.emnlp-main.899/'),
        dict(title='유지 규칙과 삭제 규칙의 비교',
             intro='미리 정한 영어 대화 8개, 요청 32개. 같은 모델 응답 64개에 규칙 적용',
             table=rows(s, [('baseline_restore','기준 방법'),('keep_only','유지 규칙만'),('remove_only','삭제 규칙만'),('keep_remove','유지·삭제 결합')]),
             foot='전체 상태는 요청 처리 후, 최종 상태는 대화 종료 후 평가\n유지 위반 수는 직전까지 맞았고 그대로 둘 항목을 잘못 바꾼 횟수',
             notes='전체 상태 일치율은 모든 항목이 정답과 일치한 요청의 비율입니다. 최종 상태 일치율은 마지막 요청 처리 후 모든 항목이 일치한 대화의 비율입니다. 27/32는 요청 32개 중 27개에서 여섯 항목 모두 맞았다는 뜻입니다. 세 번째 대화의 세 번째 요청에서는 삭제 규칙이 식물 삭제 누락을 막았습니다. 네 번째 요청에서는 유지 규칙이 배경을 잘못 바꾸는 것을 막았습니다. 두 규칙을 결합해야 두 요청 모두 정답과 일치했습니다. 일곱 번째 대화는 모든 방법에서 요청 네 개 중 하나만 맞았습니다. 맞은 항목 수는 표의 방법 순서대로 184, 185, 186, 187개이며 전체 항목 수는 192개입니다. 연구를 위해 만든 영어 대화로 검사했습니다. '+REPO+'/blob/main/experiments/request-contract-v3/RESULTS.md'),
        dict(title='새 대화에서 다시 검사한 결과',
             intro='영어 대화 8개, 요청 32개를 새로 작성하고 기존 코드를 그대로 적용',
             table=rows(t, [('baseline_restore','기준 방법'),('isolated_restore','항목별 적용'),('keep_remove','유지·삭제'),('isolated_keep_remove','항목별 적용 + 유지·삭제')]),
             foot='유지·삭제 규칙이 일곱 번째 대화의 마지막 요청을 바로잡았다. 항목별 적용을 더해도 결과는 같았다.',
             notes='항목별 적용은 한 항목이 틀려도 다른 유효한 변경은 반영하는 처리입니다. 앞선 실험 결과를 확인한 뒤 이 처리를 더해 다시 계산하자 32개 요청 모두 맞았습니다. 같은 효과가 새 대화에서도 나타나는지 확인하기 위해 코드와 요청을 먼저 확정한 뒤 모델을 실행했습니다. 새 대화에서는 유지·삭제 규칙만 적용한 경우와 항목별 적용을 더한 경우의 결과가 같았습니다. 맞은 항목 수는 표 순서대로 187, 187, 189, 189개이며 전체 항목 수는 192개입니다. 두 실험의 결과는 따로 집계했습니다. '+REPO+'/blob/main/experiments/isolated-contract-v1/RESULTS.md'),
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
        dict(title='표현이 달라졌을 때의 처리',
             body='표현을 바꾼 요청 32개에서 기존 방법은 25/32\n복원할 대상과 유지할 대상이 섞이는 오류 확인\n\n개선 코드를 고정한 뒤 새 대화 4개, 요청 16개 검사\n'+f"기준 {normalized['baseline_restore']['exact_turns']}/16, 기존 유지·삭제 {normalized['keep_remove']['exact_turns']}/16\n정규화 {normalized['normalized_atomic']['exact_turns']}/16, 항목별 적용을 더해도 같은 결과",
             foot='개선은 대화 네 개 중 세 개에서 발생. 기준이 맞은 요청을 추가로 틀린 경우는 0개\n검사에는 규칙이 처리하도록 정한 영어 표현을 사용',
             notes='표현을 바꾸자 모델이 맞게 답해도 복원 지시가 뒤의 유지 대상까지 적용되는 오류가 나타났습니다. 두 지시를 구분하고 같은 뜻의 표현을 정해진 형태로 바꿨습니다. 개발 자료 재계산은 정규화 29/32, 항목별 적용 27/32, 결합 32/32였습니다. 이후 코드를 고정하고 새 대화로 검사한 결과는 기준 9/16, 기존 유지·삭제 10/16, 정규화 16/16, 항목별 적용 10/16, 결합 16/16이었습니다. 개선은 세 대화에서 나타났으며 일부 차이는 앞선 오류가 이후 요청에도 남은 결과입니다. '+REPO+'/blob/main/experiments/clause-normalization-v1/RESULTS.md\n복합 요청의 오류를 분석한 뒤 수행한 짧은 대조는 최초 추출·재검토 모두 7/8이었습니다. 이 8개 요청의 결과를 별도로 집계했습니다.'),
        dict(title='문장 구조 비교와 추가 검증 결과',
             body=f"기준 {structural['baseline_restore']['exact_turns']}/36, 기존 유지·삭제 {structural['keep_remove']['exact_turns']}/36\n단순 JSON 적용 {plain['exact_turns']}/36, 정규화 {structural['normalized_atomic']['exact_turns']}/36\n\n추가 요청 48개: 기준 {transfer['baseline_restore']['exact_turns']}/48, 정규화 {transfer['normalized_atomic']['exact_turns']}/48\n새 조합 {transfer_groups['recombined']['target_exact']}/8, 지시 수정 {transfer_groups['revision']['target_exact']}/8, 새 표현 {transfer_groups['unseen']['target_exact']}/8\n지원 표현의 적용 대상을 구분해 오류를 줄임",
             foot='문장 구조 비교의 요청 문장은 18개. 추가 검증은 32개.\n표현 유형별 수치는 두 번째와 세 번째 요청 8개의 결과',
             notes='표준 분리 구절, leaving 연결, preserving 연결, bring back과 부정형 유지 표현을 비교했습니다. 복원과 유지가 함께 있는 요청에서 기존 유지·삭제는 구조 순서대로 3/3, 3/3, 0/3, 1/3이었고 정규화는 모두 3/3이었습니다. 전체 요청에서 기준은 18/36, 기존 유지·삭제는 26/36, 정규화는 36/36입니다. 항목별 적용을 더해도 정규화와 같은 결과였습니다. 저장된 응답에 단순 JSON 적용 방법을 비교하니 최초 응답과 재검토 우선 방식 모두 28/36이었습니다. 대화 12개는 세 편집 조건을 네 구조로 반복한 것이며 서로 다른 요청 문장은 18개입니다. 같은 초기 설정과 후속 요청의 응답 쌍은 모두 같았습니다. 별도의 코드 검사에서는 직접 구성한 정답 응답 963개를 사용했고, 대화 실험에서는 실제 모델 응답을 사용했습니다. 추가 검증은 코드와 요청을 고정한 뒤 네 편집 조건을 세 표현 유형으로 비교한 대화 12개, 요청 48개입니다. 실제 모델 호출은 96회이고 서로 다른 요청 문장은 32개입니다. 기준 24/48, 기존 유지·삭제 27/48, 정규화 36/48, 항목별 적용 27/48, 결합 36/48, JSON 최초 응답과 재검토 우선은 각각 15/48입니다. 정규화의 최종 상태 일치율은 8/12이고 추가 오류는 0개였습니다. 기존 어휘의 새 조합과 앞 지시 수정은 각각 8/8이지만 규칙에 없는 표현은 0/8입니다. 새로운 복원 표현을 모델이 유지로 추출하였고 재검토와 규칙도 고치지 못했습니다. 최초 복원 오류 네 건과 그 오류가 남은 후속 요청 네 건이 0/8에 포함됩니다. https://github.com/kimmireu0220/inha-capstone/blob/main/experiments/instruction-transfer-v1/RESULTS.md\n문장 구조 결과 '+REPO+'/blob/main/experiments/clause-factorial-v1/RESULTS.md\n논문 '+REPO+'/blob/main/paper/manuscript.inha.pdf\nWord '+REPO+'/blob/main/paper/manuscript.inha.docx\n실험 색인 '+REPO+'/blob/main/RESEARCH_INDEX.md')
    ]


def image_label(index):
    """One publication label shared by the writer and readback verifier."""
    return f"요청 {3+index//2}  {'기준 방법' if index%2==0 else '유지·삭제'}"
