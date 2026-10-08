"""Update the existing Google deck from frozen evidence; dry-run by default.

Requires a freshly inspected snapshot. A revision lock prevents overwriting
concurrent edits. Raw snapshots stay in the ignored private build directory.
"""
import argparse
import hashlib
import json
from pathlib import Path

from googleapiclient.discovery import build
from update_google_slides import credentials, DEFAULT_CLIENT_FILE, PRESENTATION_ID

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
           'experiments/keep-image-v1/summary.json']


def load(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec():
    """Editable text/table specifications. Numerical rows come from evidence."""
    s = load(SOURCES[3])['methods']
    t = load(SOURCES[4])['methods']
    def rows(data, methods):
        result = [['방법', '정확한 턴', '최종 정답 대화', '유지 오류']]
        for key, label in methods:
            r = data[key]
            result.append([label, f"{r['exact_turns']}/{r['turns']}",
                           f"{r['exact_final_dialogues']}/8", str(r['newly_corrupted_unchanged_slots'])])
        return result
    first, second = load(SOURCES[5])['by_mode'], load(SOURCES[6])['by_mode']
    images = [['AI 목표 충족', '기준 방법', '유지·삭제 결합']]
    for data, label in [(first, '1차 3B'), (second, '사후 7B')]:
        images.append([label] + [f"{data[m]['goals_satisfied']}/{data[m]['goal_denominator']}" for m in ['baseline_restore', 'keep_remove']])
    return [
        dict(title='반복 인물 이미지 편집을 위한\n유지 및 삭제 지시의 상태 갱신 제약',
             body='변경 요청을 종합할 때 생기는 상태 오류를 줄이는 방법\n\n김미르 · 장윤석\n지도교수 안남혁',
             foot='종합설계 연구 발표',
             notes='같은 언어 모델 응답에 유지·삭제 규칙을 적용했을 때 편집 상태의 오류가 줄어드는지 살펴봤습니다. 모델이 변경 사항을 추출하고 재검토한 뒤, 유지하거나 삭제하라는 명시적 지시를 코드로 한 번 더 확인하는 방법입니다. 두 규칙이 각각 어떤 오류를 줄이는지 비교했습니다.'),
        dict(title='유지·삭제 지시의 상태 검사',
             body='1. 현재 요청에서 변경을 추출하고 한 번 재검토\n2. 각 방법의 이전 상태에 변경을 적용\n3. 유지할 항목을 보호하고, 명시한 삭제를 실행\n4. 완성된 상태를 원본 사진의 편집 요청으로 변환',
             foot='재킷·상의·핀·목걸이·배경·소품의 6항목을 저장한다. 추가 모델 호출은 없다.',
             notes='Qwen3-4B-4bit가 현재 요청에서 변경 사항을 추출하고 한 번 재검토합니다. 모든 방법은 이 두 응답을 공유하고 각자의 이전 상태에 적용합니다. 정답은 채점에만 사용했습니다. 유지 규칙은 항목 이름과 unchanged가 함께 있는 구절에서 직전 값을 보존합니다. 삭제 규칙은 remove가 명시된 재킷·핀·목걸이·소품의 값을 없음으로 바꿉니다. 상의와 배경은 삭제 대상에서 제외합니다. 원본 복원은 최초 사진의 상태로 돌리는 것이고 삭제는 대상을 없애는 것입니다. 인용, 조건부 표현, 대명사, 같은 항목의 후속 언급에는 규칙을 적용하지 않고 모델 결과를 사용합니다. 상태를 저장하는 구성은 ChatEdit를 참고했습니다. https://aclanthology.org/2023.emnlp-main.899/'),
        dict(title='S 검증: 유지와 삭제를 함께 적용한 효과',
             intro='추론 전에 확정한 영어 합성 대화 8개, 32턴. 같은 모델 응답 64개 사용',
             table=rows(s, [('baseline_restore','기준 방법'),('keep_only','유지 규칙만'),('remove_only','삭제 규칙만'),('keep_remove','유지·삭제 결합')]),
             foot='차이는 S3의 두 턴에서 발생. 정확한 턴은 6항목 모두 정답인 경우\n유지 오류: 직전까지 정확했고 유지해야 할 항목을 잘못 변경한 횟수',
             notes='한 번의 요청에 따라 상태를 갱신하는 단위를 턴이라고 합니다. 정확한 턴은 여섯 항목이 모두 맞은 경우이고, 최종 정답 대화는 마지막 턴의 여섯 항목이 모두 맞은 대화입니다. S3의 3턴에서는 삭제 규칙이 식물 삭제 누락을 막았고, 4턴에서는 유지 규칙이 불필요한 배경 변경을 막았습니다. 두 규칙을 결합했을 때만 두 턴 모두 정확했습니다. S7은 모든 방법에서 네 턴 중 한 턴만 맞았습니다. 정확한 항목은 표의 방법 순서대로 184, 185, 186, 187개이며 분모는 192개입니다. 대화는 연구용으로 만든 제한된 영어 문형입니다. '+REPO+'/blob/main/experiments/request-contract-v3/RESULTS.md'),
        dict(title='T 검증: 추가 규칙의 효과 확인',
             intro='추가 검증용 합성 대화 8개, 32턴. 코드를 수정하지 않고 적용',
             table=rows(t, [('baseline_restore','기준 방법'),('isolated_restore','항목별 적용'),('keep_remove','유지·삭제'),('isolated_keep_remove','항목별 적용 + 유지·삭제')]),
             foot='유지·삭제가 T7 마지막 턴을 바로잡았다. 항목별 적용을 더한 이점은 없었다.',
             notes='항목별 적용은 한 항목의 오류 때문에 다른 유효한 변경까지 취소되는 것을 막는 처리입니다. S 결과를 본 뒤 이 처리를 더해 재계산하자 32턴 모두 맞았습니다. 그래서 추가 효과가 새 대화에서도 나타나는지 T로 확인했습니다. T의 대화와 정답은 추론 전에 확정했습니다. 결과는 유지·삭제 규칙만 적용한 경우와 같아 추가 처리 없이 두 규칙을 사용하기로 했습니다. 정확한 항목은 표 순서대로 187, 187, 189, 189개이며 분모는 192개입니다. S와 T는 서로 다른 개발 단계에서 구성했으므로 결과를 따로 보고합니다. '+REPO+'/blob/main/experiments/isolated-contract-v1/RESULTS.md'),
        dict(title='실제 인물 R01: 식물 삭제와 배경 유지', person='R01',
             foot='원본: Monstera Production / Pexels. 의상·장신구·배경은 AI 편집 결과.',
             notes='R01에서 두 방법의 입력이 달랐던 두 쌍입니다. 3턴에서는 식물을 삭제하고 재킷을 유지하도록 요청했습니다. 4턴에서는 상의와 목걸이를 원본으로 돌리면서 재킷과 연한 파란 배경은 유지하도록 요청했습니다. 각 이미지의 전체 영역을 보여줍니다. 연구 참여자가 아닌 공개 사진을 사용했고 의상과 배경 등은 AI로 편집했습니다. 원본 https://www.pexels.com/photo/confident-black-man-in-studio-6311573/\n'+REPO+'/blob/main/paper/figures/figure-provenance.json'),
        dict(title='실제 인물 R02: 동일한 요청의 편집 결과', person='R02',
             foot='원본: Monstera Production / Pexels. 의상·장신구·배경은 AI 편집 결과.',
             notes='R02에도 R01과 같은 S3의 3·4턴 요청을 적용했습니다. 각 이미지의 전체 영역을 보여줍니다. 3B 모델은 3턴 기준 이미지를 평가할 때 JSON 대신 느낌표를 출력했고, 7B 모델은 식물에 관한 설명과 점수가 일치하지 않았습니다. 다음 장에서 이러한 평가 오류를 구분해 설명하겠습니다. 연구 참여자가 아닌 공개 사진을 사용했고 의상과 배경 등은 AI로 편집했습니다. 원본 https://www.pexels.com/photo/cheerful-black-woman-in-studio-6311581/\n'+REPO+'/blob/main/paper/figures/figure-provenance.json'),
        dict(title='이미지 평가 점수와 판정 오류',
             intro='실제 사진 2명 × 32턴 × 두 방법 = 128조건, 고유 생성 이미지 66개',
             table=images,
             below='3B에서 늘어난 8개 중 6개는 판단 불가가 성공으로 바뀐 항목\n7B에도 설명과 점수의 모순이 있어 품질 향상 판단에 한계',
             foot='목표 충족은 방법당 64조건 × 6항목으로 집계한다.\n64쌍 중 서로 다른 입력은 4쌍이며 나머지 60쌍은 같은 출력을 공유한다.',
             notes='이미지와 평가 목표의 조합은 68개입니다. 3B의 판단 불가는 기준 20개, 결합 13개였고, 응답 형식 오류는 3개였습니다. 이 오류를 본 뒤 같은 계열의 7B 모델로 전체를 다시 평가했습니다. 7B에는 형식 오류나 판단 불가가 없었지만 설명과 점수의 모순은 남았습니다. 두 모델이 공통으로 실패에서 성공으로 판정한 것은 R02 S3 4턴의 배경 한 항목입니다. 같은 계열 모델의 사후 평가이므로 판정이 일치한다고 정답으로 볼 수는 없습니다. 얼굴 코사인 평균은 기준 '+f"{first['baseline_restore']['face_mean']:.6f}, 결합 {first['keep_remove']['face_mean']:.6f}"+'입니다. 입력이 다른 네 쌍 중 두 쌍은 높아지고 두 쌍은 낮아져 얼굴 보존이 개선됐다고 판단하기 어렵습니다. '+REPO+'/blob/main/experiments/contract-image-review-v1/INTERPRETATION.md'),
        dict(title='앞선 실패에서 확인한 규칙의 범위',
             body='keep을 폭넓게 탐지한 규칙은 Q에서 12/32\n적용 문형을 좁혀도 마지막 상태가 정확한 대화는 감소\n\n이후 삭제 누락도 함께 검사하도록 수정\n조건부 표현과 대명사 등은 모델의 추출 결과를 사용',
             foot='앞선 P 이미지 평가의 점수 차이는 판단 불가 한 항목이 성공으로 바뀐 결과',
             notes='초기 개발 대화 P에서는 정확한 턴이 30/32에서 32/32로 늘었습니다. 하지만 keep을 폭넓게 탐지하면 off나 색 변경 요청을 유지로 잘못 처리했습니다. 새 대화 Q에서 기준은 27/32, 넓은 규칙은 12/32, 문형을 좁힌 규칙은 27/32였습니다. 문형을 좁혀도 마지막 상태가 정확한 대화는 6/8에서 5/8로 줄어 삭제 누락을 함께 검사하도록 수정했습니다. 이후 S에서 두 규칙의 효과를 비교했습니다. P 이미지 실험은 128조건에서 68개 이미지를 생성했고 목표 충족 수는 기준 354/384, 유지 규칙 355/384였습니다. 차이는 판단 불가 한 항목이 성공으로 바뀐 경우였습니다. '+REPO+'/blob/main/RESEARCH_INDEX.md'),
        dict(title='유지·삭제 규칙을 함께 적용한 결과',
             body='삭제 규칙은 식물 삭제 누락을 방지\n유지 규칙은 불필요한 배경 변경을 방지\n같은 모델 응답을 사용해 추가 호출 없이 적용\n\n효과를 확인한 범위는 제한된 영어 문형의 합성 대화',
             foot='이미지 품질은 AI 판정 오류로 결론이 제한됨. 얼굴 유사도는 4쌍 중 2쌍 상승·2쌍 하락',
             notes='정확한 턴은 S에서 27/32에서 29/32로, T에서 28/32에서 29/32로 늘었습니다. 차이는 S3와 T7에서 나타났습니다. S3에서는 삭제 규칙이 식물을 남기는 오류를 막고 유지 규칙이 배경을 잘못 바꾸는 오류를 막았습니다. 두 규칙은 서로 다른 오류를 처리했습니다. 실험에는 정해진 영어 문형의 합성 대화와 한 종류의 4B 추출 모델을 사용했습니다. 유지 규칙은 직전 값을 그대로 보존하므로 이전 상태에 있던 오류도 유지합니다.'),
        dict(title='논문과 재현 자료',
             body='논문 PDF 및 Word\nS·T 요청, 정답, 모델 응답과 실험 코드\n전체 생성 이미지와 AI 평가 원문\n개발 과정과 실험별 결과',
             foot='github.com/kimmireu0220/inha-capstone',
             notes='논문 '+REPO+'/blob/main/paper/manuscript.inha.pdf\nWord '+REPO+'/blob/main/paper/manuscript.inha.docx\n실험 색인 '+REPO+'/blob/main/RESEARCH_INDEX.md\n관련 연구 및 사진 출처 전체는 논문 참고문헌에 기재했다.')
    ]


def props(slide, x, y, w, h):
    return {'pageObjectId': slide, 'size': {'width': {'magnitude': w, 'unit': 'PT'}, 'height': {'magnitude': h, 'unit': 'PT'}},
            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': x, 'translateY': y, 'unit': 'PT'}}


def text_box(req, sid, key, text, x, y, w, h, size=21, bold=False, link=None):
    oid = sid + '_method_' + key
    req.append({'createShape': {'objectId': oid, 'shapeType': 'TEXT_BOX', 'elementProperties': props(sid,x,y,w,h)}})
    req.append({'insertText': {'objectId': oid, 'text': text}})
    style = {'fontFamily': 'Malgun Gothic', 'fontSize': {'magnitude': size,'unit':'PT'}, 'bold':bold,
             'foregroundColor': {'opaqueColor': {'rgbColor': {'red':0,'green':0,'blue':0}}}}
    if link:
        style['link'] = {'url': link}
    req.append({'updateTextStyle': {'objectId': oid, 'textRange': {'type':'ALL'}, 'style':style,'fields':','.join(style)}})
    req.append({'updateParagraphStyle': {'objectId':oid,'textRange':{'type':'ALL'},'style':{'lineSpacing':120,'spaceAbove':{'magnitude':0,'unit':'PT'},'spaceBelow':{'magnitude':12,'unit':'PT'}},'fields':'lineSpacing,spaceAbove,spaceBelow'}})


def table(req,sid,rows,widths):
    oid = sid+'_method_table'
    req.append({'createTable':{'objectId':oid,'rows':len(rows),'columns':len(rows[0]),'elementProperties':props(sid,70,161,820,48*len(rows))}})
    for j,width in enumerate(widths):
        req.append({'updateTableColumnProperties':{'objectId':oid,'columnIndices':[j],'tableColumnProperties':{'columnWidth':{'magnitude':width,'unit':'PT'}},'fields':'columnWidth'}})
    req.append({'updateTableRowProperties':{'objectId':oid,'tableRowProperties':{'minRowHeight':{'magnitude':48,'unit':'PT'}},'fields':'minRowHeight'}})
    req.append({'updateTableCellProperties':{'objectId':oid,'tableCellProperties':{'contentAlignment':'MIDDLE'},'fields':'contentAlignment'}})
    for i,row in enumerate(rows):
        for j,value in enumerate(row):
            cell={'rowIndex':i,'columnIndex':j}
            req.append({'insertText':{'objectId':oid,'cellLocation':cell,'text':value}})
            req.append({'updateTextStyle':{'objectId':oid,'cellLocation':cell,'textRange':{'type':'ALL'},'style':{'fontFamily':'Malgun Gothic','fontSize':{'magnitude':19,'unit':'PT'},'bold':i==0},'fields':'fontFamily,fontSize,bold'}})
            req.append({'updateParagraphStyle':{'objectId':oid,'cellLocation':cell,'textRange':{'type':'ALL'},'style':{'alignment':'START' if j==0 else 'CENTER','spaceAbove':{'magnitude':0,'unit':'PT'},'spaceBelow':{'magnitude':0,'unit':'PT'}},'fields':'alignment,spaceAbove,spaceBelow'}})
    req.append({'updateTableCellProperties':{'objectId':oid,'tableRange':{'location':{'rowIndex':0,'columnIndex':0},'rowSpan':1,'columnSpan':len(rows[0])},'tableCellProperties':{'tableCellBackgroundFill':{'solidFill':{'color':{'rgbColor':{'red':.94,'green':.94,'blue':.94}},'alpha':1}}},'fields':'tableCellBackgroundFill'}})


def requests(deck):
    slides={s['objectId']:s for s in deck['slides']}
    if not set(IDS).issubset(slides):
        raise ValueError('Expected existing slide IDs are missing; inspect the deck again.')
    req=[]
    for sid, slide in slides.items():
        if sid not in IDS:
            req.append({'deleteObject':{'objectId':sid}})
        else:
            for el in slide.get('pageElements',[]):
                req.append({'deleteObject':{'objectId':el['objectId']}})
    req.append({'updateSlidesPosition':{'slideObjectIds':IDS,'insertionIndex':0}})
    specs=spec()
    for number,(sid,item) in enumerate(zip(IDS,specs),1):
        text_box(req,sid,'title',item['title'],64,30,836,94 if number==1 else 60,28,True)
        text_box(req,sid,'foot',item['foot'],70,463,820,39,14)
        text_box(req,sid,'num',str(number),873,508,30,23,12)
        if 'body' in item:
            text_box(req,sid,'body',item['body'],70,173 if number==1 else 133,820,279,21)
        if 'intro' in item:
            text_box(req,sid,'intro',item['intro'],70,106,820,50,19)
        if 'table' in item:
            table(req,sid,item['table'],[340,175,175,130] if len(item['table'][0])==4 else [270,275,275])
        if 'below' in item:
            text_box(req,sid,'below',item['below'],70,337,820,111,21)
        if 'person' in item:
            person=item['person']
            figure=next(f for f in load(SOURCES[2])['figures'] if person in f['figure'])
            for j,source in enumerate(figure['sources']):
                text_box(req,sid,f'label{j}',f"{3+j//2}턴  {'기준 방법' if j%2==0 else '유지·삭제'}",70+j*211,103,204,33,18,True)
                # Google fits the complete original image inside the box, preserving aspect ratio.
                req.append({'createImage':{'objectId':sid+f'_method_image{j}', 'url':f'https://raw.githubusercontent.com/kimmireu0220/inha-capstone/{IMAGE_COMMIT}/'+source['source'],'elementProperties':props(sid,70+j*211,147,190,285)}})
        if number==10:
            text_box(req,sid,'link','논문 PDF 열기',70,377,300,40,20,False,REPO+'/blob/main/paper/manuscript.inha.pdf')
        note_id=slides[sid]['slideProperties']['notesPage']['notesProperties']['speakerNotesObjectId']
        req += [{'deleteText':{'objectId':note_id,'textRange':{'type':'ALL'}}}, {'insertText':{'objectId':note_id,'text':item['notes']}}]
    return req


def text_requests(deck):
    """Revise wording in place, retaining images, formatting and object IDs."""
    if [s['objectId'] for s in deck['slides']] != IDS:
        raise ValueError('Text-only edits require the inspected ten-slide structure.')
    req = []

    def replace(oid, text, location=None):
        target = {'objectId': oid}
        if location is not None:
            target['cellLocation'] = location
        req.extend([{'deleteText': {**target, 'textRange': {'type': 'ALL'}}},
                    {'insertText': {**target, 'text': text}}])

    for slide, item in zip(deck['slides'], spec()):
        sid = slide['objectId']
        elements = {e['objectId']: e for e in slide['pageElements']}
        for key in ['title', 'body', 'intro', 'below', 'foot']:
            if key in item:
                oid = sid + '_method_' + key
                if 'shape' not in elements.get(oid, {}):
                    raise ValueError(f'Missing text object: {oid}')
                replace(oid, item[key])
        if 'table' in item:
            oid = sid + '_method_table'
            existing = elements.get(oid, {}).get('table', {}).get('tableRows', [])
            if len(existing) != len(item['table']) or any(len(r['tableCells']) != len(item['table'][0]) for r in existing):
                raise ValueError(f'Table dimensions changed: {oid}')
            for row, values in enumerate(item['table']):
                for column, value in enumerate(values):
                    replace(oid, value, {'rowIndex': row, 'columnIndex': column})
        if 'person' in item:
            for j in range(4):
                oid = sid + f'_method_label{j}'
                if oid not in elements:
                    raise ValueError(f'Missing image label: {oid}')
                replace(oid, f"{3+j//2}턴  {'기준 방법' if j%2==0 else '유지·삭제'}")
        note_id = slide['slideProperties']['notesPage']['notesProperties']['speakerNotesObjectId']
        replace(note_id, item['notes'])
    return req


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--text-only',action='store_true',help='Keep the existing objects and update wording only.')
    args=p.parse_args()
    old=json.loads(args.snapshot.read_text())
    if old['presentationId'] != PRESENTATION_ID:
        raise SystemExit('Snapshot belongs to another deck.')
    req=text_requests(old) if args.text_only else requests(old)
    print(f"Plan: {len(old['slides'])} slides to {len(IDS)}, {len(req)} requests")
    if not args.apply:
        return
    service=build('slides','v1',credentials=credentials(DEFAULT_CLIENT_FILE))
    live=service.presentations().get(presentationId=PRESENTATION_ID).execute()
    if live['revisionId'] != old['revisionId']:
        raise SystemExit('Live revision differs from inspected snapshot. No changes made.')
    service.presentations().batchUpdate(presentationId=PRESENTATION_ID,body={'writeControl':{'requiredRevisionId':live['revisionId']},'requests':req}).execute()
    print('Applied. Fetch and visually inspect every native preview before recording completion.')


if __name__=='__main__':
    main()
