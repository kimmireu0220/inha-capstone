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
           'experiments/clause-normalization-v1/invariant-audit.json']


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
    mixed_review = compound['groups']['review']['mixed']['exact_turns']
    mixed_guarded = compound['groups']['guarded']['mixed']['exact_turns']
    images = [['AI 항목별 충족률', '기준 방법', '유지·삭제 결합']]
    for data, label in [(first, '1차 3B'), (second, '사후 7B')]:
        images.append([label] + [f"{data[m]['goals_satisfied']}/{data[m]['goal_denominator']}" for m in ['baseline_restore', 'keep_remove']])
    return [
        dict(title='반복 인물 이미지 편집을 위한\n유지 및 삭제 지시의 상태 갱신 제약',
             body='변경 요청을 종합할 때 생기는 상태 오류를 줄이는 방법\n\n김미르 · 장윤석\n지도교수 안남혁',
             foot='종합설계 연구 발표',
             notes='처음에는 편집 대화 전체를 합쳐 최종 프롬프트를 작성했습니다. 취소한 장신구와 의상 조건이 다시 남는 사례가 있어 항목별 상태를 갱신한 뒤 프롬프트로 변환하는 구조로 나누었습니다. 같은 언어 모델 응답에 유지·삭제 규칙을 적용해 효과를 비교했고, 표현 변화에서 발견한 복원·유지 구절 경계 오류를 정규화로 보완했습니다.'),
        dict(title='유지·삭제 지시의 상태 검사',
             body='1. 현재 요청에서 변경을 추출하고 한 번 재검토\n2. 복원·유지 구절을 구분하고 이전 상태에 적용\n3. 유지할 항목을 보호하고, 명시한 삭제를 실행\n4. 완성된 상태를 원본 사진의 편집 요청으로 변환',
             foot='재킷·상의·핀·목걸이·배경·소품의 6항목을 저장한다. 모든 방법이 같은 두 모델 응답을 사용한다.',
             notes='Qwen3-4B-4bit가 현재 요청에서 변경 사항을 추출하고 한 번 재검토합니다. 모든 방법은 이 두 응답을 공유하고 각자의 이전 상태에 적용합니다. 편집 상태는 지금까지의 요청을 반영한 항목별 요구 값입니다. 정답은 채점에만 사용했습니다. 유지 규칙은 항목 이름과 unchanged가 함께 있는 구절에서 직전 값을 보존합니다. 삭제 규칙은 remove가 명시된 재킷·핀·목걸이·소품의 값을 없음으로 바꿉니다. 상의와 배경은 삭제 대상에서 제외합니다. 원본 복원은 최초 사진의 상태로 돌리는 것이고 삭제는 대상을 없애는 것입니다. 인용, 조건부 표현, 대명사, 같은 항목의 후속 언급에는 모델의 추출·재검토 결과를 사용합니다. 상태를 저장하는 구성은 ChatEdit를 참고했습니다. https://aclanthology.org/2023.emnlp-main.899/'),
        dict(title='유지·삭제 규칙 비교 실험',
             intro='추론 전에 확정한 영어 합성 대화 8개, 32턴. 같은 모델 응답 64개 사용',
             table=rows(s, [('baseline_restore','기준 방법'),('keep_only','유지 규칙만'),('remove_only','삭제 규칙만'),('keep_remove','유지·삭제 결합')]),
             foot='일치율은 일치 건수/평가 건수. 전체 상태는 매 요청 후, 최종 상태는 대화 종료 후 평가\n유지 위반 수: 직전까지 맞았고 보존해야 하는 항목을 잘못 변경한 횟수',
             notes='한 번의 요청에 따라 상태를 갱신하는 단위를 턴이라고 합니다. 전체 상태 일치율은 모든 항목이 정답과 일치한 요청의 비율입니다. 최종 상태 일치율은 마지막 요청 처리 후 모든 항목이 일치한 대화의 비율입니다. 27/32는 요청 32회 중 27회에서 여섯 항목 모두 일치했다는 뜻입니다. 표의 유지 위반 수는 유지 지시 위반 횟수를 뜻합니다. 세 번째 대화의 3턴에서는 삭제 규칙이 식물 삭제 누락을 막았고, 4턴에서는 유지 규칙이 불필요한 배경 변경을 막았습니다. 두 규칙을 결합했을 때 두 요청 후의 상태 기록이 모두 정답과 일치했습니다. 일곱 번째 대화는 모든 방법에서 네 턴 중 한 턴만 맞았습니다. 정답과 일치한 항목 수는 표의 방법 순서대로 184, 185, 186, 187개이며 분모는 192개입니다. 대화는 연구용으로 만든 제한된 영어 문형입니다. '+REPO+'/blob/main/experiments/request-contract-v3/RESULTS.md'),
        dict(title='새 대화에서의 재검증 실험',
             intro='추가 검증용 합성 대화 8개, 32턴. 앞선 실험의 코드를 그대로 적용',
             table=rows(t, [('baseline_restore','기준 방법'),('isolated_restore','항목별 적용'),('keep_remove','유지·삭제'),('isolated_keep_remove','항목별 적용 + 유지·삭제')]),
             foot='유지·삭제가 일곱 번째 대화의 마지막 턴을 바로잡았다. 항목별 적용을 더한 결과도 같았다.',
             notes='항목별 적용은 한 항목의 오류 때문에 다른 유효한 변경까지 취소되는 것을 막는 처리입니다. 규칙 비교 실험 결과를 본 뒤 이 처리를 더해 재계산하자 32턴 모두 맞았습니다. 그래서 추가 효과가 새 대화에서도 나타나는지 재검증했습니다. 새 대화와 정답은 추론 전에 확정했습니다. 결과는 유지·삭제 규칙만 적용한 경우와 같아 추가 처리 없이 두 규칙을 사용하기로 했습니다. 정답과 일치한 항목 수는 표 순서대로 187, 187, 189, 189개이며 분모는 192개입니다. 규칙 비교와 재검증은 서로 다른 개발 단계에서 구성했으므로 결과를 따로 보고합니다. '+REPO+'/blob/main/experiments/isolated-contract-v1/RESULTS.md'),
        dict(title='실제 인물 R01: 식물 삭제와 배경 유지', person='R01',
             foot='원본: Monstera Production / Pexels. 의상·장신구·배경은 AI 편집 결과.',
             notes='R01에서 두 방법의 입력이 달랐던 두 쌍입니다. 3턴에서는 식물을 삭제하고 재킷을 유지하도록 요청했습니다. 4턴에서는 상의와 목걸이를 원본으로 돌리면서 재킷과 연한 파란 배경은 유지하도록 요청했습니다. 각 이미지의 전체 영역을 보여줍니다. Pexels의 공개 사진을 사용했고 의상과 배경 등은 AI로 편집했습니다. 원본 https://www.pexels.com/photo/confident-black-man-in-studio-6311573/\n'+REPO+'/blob/main/paper/figures/figure-provenance.json'),
        dict(title='실제 인물 R02: 동일한 요청의 편집 결과', person='R02',
             foot='원본: Monstera Production / Pexels. 의상·장신구·배경은 AI 편집 결과.',
             notes='R02에도 R01과 같은 세 번째 대화의 3·4턴 요청을 적용했습니다. 각 이미지의 전체 영역을 보여줍니다. 3B 모델은 3턴 기준 이미지를 평가할 때 JSON 대신 느낌표를 출력했고, 7B 모델은 식물에 관한 설명과 점수가 일치하지 않았습니다. 다음 장에서 이러한 평가 오류를 구분해 설명하겠습니다. Pexels의 공개 사진을 사용했고 의상과 배경 등은 AI로 편집했습니다. 원본 https://www.pexels.com/photo/cheerful-black-woman-in-studio-6311581/\n'+REPO+'/blob/main/paper/figures/figure-provenance.json'),
        dict(title='이미지 평가 점수와 판정 오류',
             intro='인물 사진 2장 × 32회 요청 × 두 방법 = 128개 생성 조건, 생성 이미지 66개',
             table=images,
             below='3B에서 늘어난 8개 중 6개는 판단 불가가 성공으로 바뀐 항목\n7B에서도 설명과 점수가 일치하지 않는 사례 발생',
             foot='항목별 충족률은 성공 판정 항목 수/전체 항목 수. 방법당 64조건 × 6항목이다.\n64쌍 중 서로 다른 입력은 4쌍이며 나머지 60쌍은 같은 출력을 공유한다.',
             notes='이미지와 평가 목표의 조합은 68개입니다. 3B의 판단 불가는 기준 20개, 결합 13개였고, 응답 형식 오류는 3개였습니다. 이 오류를 본 뒤 같은 계열의 7B 모델로 전체를 다시 평가했습니다. 7B의 형식 오류와 판단 불가는 각각 0개였고 설명과 점수의 모순은 남았습니다. 두 모델이 공통으로 실패에서 성공으로 판정한 것은 세 번째 대화의 R02 4턴의 배경 한 항목입니다. 이 재평가는 같은 계열의 두 모델 사이에서 판정이 얼마나 일치하는지 살펴본 것입니다. 얼굴 유사도 평균은 기준 '+f"{first['baseline_restore']['face_mean']:.6f}, 결합 {first['keep_remove']['face_mean']:.6f}"+'입니다. 입력이 다른 네 쌍 중 두 쌍은 높아지고 두 쌍은 낮아졌습니다. 나머지 60쌍은 같은 출력을 공유하므로 평균 차이는 이 네 쌍에서 발생했습니다. '+REPO+'/blob/main/experiments/contract-image-review-v1/INTERPRETATION.md'),
        dict(title='포즈·표정과 속성 지시를 함께 처리한 결과',
             body='4가지 요청 구성 × 3조건 × 4회 요청 = 48회 요청\n표정만, 표정·포즈 조건은 세 방법 모두 16/16\n'+f'속성 지시 혼합은 재검토 {mixed_review}/16, 규칙 보정 {mixed_guarded}/16\n\n삭제를 원본 복원으로 해석한 오류를 바로잡음',
             foot='수치는 9항목 모두 일치한 요청 수/전체 요청 수. 삭제 규칙만 적용해도 같은 결과',
             notes='최초 추출, 한 차례 재검토, 재검토 뒤 규칙 보정을 비교했습니다. 최초 추출은 턴당 한 번, 나머지는 두 번 호출합니다. 상태는 기존 속성에 몸 방향·손동작·표정을 추가한 아홉 항목이며 어휘와 구현을 새로 고정했습니다. 전체 상태 일치율은 아홉 항목 모두 정답과 일치한 요청의 비율입니다. 어휘와 구현이 달라 결과는 앞선 두 실험과 별도로 집계했습니다. 세 방법 모두 포즈·표정은 조건별 48항목이 정확했습니다. 혼합 조건에서 최초 추출과 재검토는 각각 4/16, 규칙 보정은 16/16이었습니다. 모델은 2턴 식물 삭제와 3턴 목걸이 삭제를 원본 복원으로 잘못 해석했습니다. 이 오류가 다음 상태에 남아 전체 항목 오류는 20개였습니다. 삭제 규칙만 적용한 사후 재계산도 48/48로, 유지·복원 규칙을 더한 경우와 같았습니다. 정답 요청으로 생성한 별도 이미지 6장의 평가에서는 응답 두 개의 형식 오류와 네 개의 몸 방향 점수·설명 모순이 나타났습니다. 앞선 개발 실험 결과도 연구 색인에 보존했습니다. '+REPO+'/blob/main/experiments/compound-edit-v1/RESULTS.md'),
        dict(title='지시 구절을 나누어 처리한 추가 검증',
             body='표현을 바꾼 32개 요청에서 기존 방법은 25/32\n원본 복원과 유지 구절을 구분하는 정규화 추가\n\n코드 고정 후 새 대화 4개, 요청 16개 검사\n'+f"기준 {normalized['baseline_restore']['exact_turns']}/16, 기존 유지·삭제 {normalized['keep_remove']['exact_turns']}/16\n정규화 {normalized['normalized_atomic']['exact_turns']}/16, 항목별 적용과 결합해도 같은 결과",
             foot='개선은 4대화 중 3대화에서 발생. 기준이 맞았던 요청의 새 오류는 0건\n측정 대상은 상태 기록이며, 제한된 영어 구절의 합성 대화를 사용',
             notes='기존 재검증과 목표를 공유하는 32개 요청의 표현을 바꾸자 기존 방법들은 모두 25/32였습니다. 모델은 셔츠와 목걸이만 원본으로 지정했지만 후처리가 뒤의 leaving 구절까지 복원하여 재킷과 배경도 원본으로 바꾸는 문제가 나타났습니다. 복원과 유지 구절을 구분하고 지원 표현을 정규화했습니다. 이 개발 자료 재계산은 정규화 29/32, 항목별 적용 27/32, 결합 32/32였습니다. 이후 코드를 고정하고 새 대화 네 개를 추론했습니다. 기준 9/16, 기존 유지·삭제 10/16, 정규화 16/16, 항목별 적용 10/16, 결합 16/16으로 새 대화의 개선은 정규화로 설명됩니다. 세 대화에서 개선됐고 일부 요청 차이는 앞선 오류의 누적입니다. 모델은 정규화 전 요청을 받아 두 응답을 공유하며 추가 호출은 없습니다. '+REPO+'/blob/main/experiments/clause-normalization-v1/RESULTS.md\n앞선 복합 요청의 오류를 분석한 뒤 수행한 짧은 대조는 최초 추출·재검토 모두 7/8이었습니다. 이 8개 요청의 결과를 별도로 집계했습니다. 모든 검사는 제한된 영어 문형과 한 종류의 추출 모델을 사용했습니다.'),
        dict(title='문장 구조 대조와 결론',
             body='같은 목표 3구성 × 4문장 구조 × 요청 3회\n'+f"기준 {structural['baseline_restore']['exact_turns']}/36, 기존 유지·삭제 {structural['keep_remove']['exact_turns']}/36\n단순 JSON 적용 {plain['exact_turns']}/36, 정규화 {structural['normalized_atomic']['exact_turns']}/36\n\n복원·유지 구절을 구분하여 상태 갱신 오류를 줄임",
             foot='서로 다른 요청 문장은 18개. 세 목표 구성의 대응 검사\ngithub.com/kimmireu0220/inha-capstone',
             notes='표준 분리 구절, leaving 연결, preserving 연결, bring back과 부정형 유지 표현을 비교했습니다. 복원·유지가 함께 있는 두 번째 요청에서 기존 유지·삭제는 문장 구조 순서대로 3/3, 3/3, 0/3, 1/3이며 정규화는 모두 3/3이었습니다. 전체 상태 일치는 기준 18/36, 기존 유지·삭제 26/36, 정규화 36/36입니다. 항목별 적용만 사용하면 26/36, 정규화와 결합하면 36/36입니다. 단순 JSON 적용을 사후 재계산하니 최초 응답과 재검토 우선 방식 모두 28/36이었습니다. 이 비교는 요청당 한 번 또는 두 번의 모델 호출을 사용하며 정규화에는 추가 호출이 없습니다. 같은 초기 설정과 후속 요청을 네 구조에서 반복했으므로 서로 다른 요청 문장은 18개입니다. 반복 요청의 응답 쌍은 모두 같았습니다. 세 가지 목표 구성에서 구조를 바꾼 결과이며 사용자 12명의 관측이 아닙니다. 지원하는 영어 구절의 상태 갱신을 측정했습니다. 정답 응답을 구성한 별도 코드 검사 963개도 통과했으며 실제 모델 실험과 구분합니다.\n문장 구조 결과 '+REPO+'/blob/main/experiments/clause-factorial-v1/RESULTS.md\n논문 '+REPO+'/blob/main/paper/manuscript.inha.pdf\nWord '+REPO+'/blob/main/paper/manuscript.inha.docx\n실험 색인 '+REPO+'/blob/main/RESEARCH_INDEX.md')
    ]
