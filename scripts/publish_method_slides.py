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
        result = [['방법', '정확한 턴', '최종 상태 정확', '새 훼손']]
        for key, label in methods:
            r = data[key]
            result.append([label, f"{r['exact_turns']}/{r['turns']}",
                           f"{r['exact_final_dialogues']}/8", str(r['newly_corrupted_unchanged_slots'])])
        return result
    first, second = load(SOURCES[5])['by_mode'], load(SOURCES[6])['by_mode']
    images = [['AI 목표 충족', '공통 기준', '유지·삭제 결합']]
    for data, label in [(first, '1차 3B'), (second, '사후 7B')]:
        images.append([label] + [f"{data[m]['goals_satisfied']}/{data[m]['goal_denominator']}" for m in ['baseline_restore', 'keep_remove']])
    return [
        dict(title='반복 인물 이미지 편집을 위한\n유지 및 삭제 지시의 상태 갱신 제약',
             body='변경 요청을 종합할 때 생기는 상태 오류를 줄이는 방법\n\n김미르 · 장윤석\n지도교수 안남혁',
             foot='종합설계 연구 발표',
             notes='연구 질문은 같은 언어 모델 응답을 사용할 때 유지와 삭제 지시를 별도로 검사하면 상태 갱신 오류가 줄어드는가이다. 기여는 제한 문형의 요청 검사 방법과 두 구성요소가 필요한 오류 사례의 검증이다. 얼굴 보존이나 전반적 이미지 품질 개선을 확정한 연구로 설명하지 않는다.'),
        dict(title='유지·삭제 지시의 상태 검사',
             body='1. 현재 요청에서 변경을 추출하고 한 번 재검토\n2. 각 방법의 이전 상태에 변경을 적용\n3. 유지할 항목을 보호하고, 명시한 삭제를 실행\n4. 완성된 상태를 원본 사진의 편집 요청으로 변환',
             foot='재킷·상의·핀·목걸이·배경·소품의 6항목을 저장한다. 추가 모델 호출은 없다.',
             notes='Qwen3-4B-4bit가 현재 요청만 읽고 추출·재검토 두 번을 수행한다. 모든 방법은 같은 응답을 공유하지만 각자의 이전 상태를 갱신한다. 정답은 채점에만 사용한다. unchanged와 지원 항목명이 명시된 구절의 직전 값을 보호하고, 명시적인 remove 구절은 제거 가능한 항목을 없음으로 설정한다. 원본 복원과 삭제는 구별한다. 상의·배경 삭제는 지원하지 않는다. 인용·조건부·대명사·뒤의 동일 항목 언급 등에서는 개입을 유보한다. ChatEdit 상태 추적 구조를 따르되 후처리 검사에 초점을 둔다. https://aclanthology.org/2023.emnlp-main.899/'),
        dict(title='S 검증: 유지와 삭제를 함께 적용한 효과',
             intro='미리 고정한 합성 대화 8개, 32턴. 동일한 모델 응답 64개를 공유',
             table=rows(s, [('baseline_restore','공통 기준'),('keep_only','유지 보호만'),('remove_only','삭제 실행만'),('keep_remove','유지·삭제 결합')]),
             foot='개선은 S3의 두 턴에 집중됐다. 정확한 턴은 6항목 모두 정답인 경우다.\n새 훼손: 바꿀 필요가 없는 정확한 항목을 이번 갱신에서 틀리게 바꾼 수',
             notes='논문 표 1. 새 훼손은 직전까지 맞았고 이번 요청에서도 유지돼야 할 항목을 틀리게 바꾼 수다. S3 3턴에서는 식물 삭제 누락을 삭제 규칙이 막았고 4턴에서는 배경 원본 복원 오류를 유지 규칙이 막았다. 유지 단독은 이전 삭제 누락이 남고 삭제 단독은 다음 턴의 배경 훼손이 남아 결합만 두 턴 모두 정확했다. S7은 모든 방법이 1/4로 실패했다. 항목 정확 수는 184,185,186,187/192. 개발자가 작성한 제한 영어 문형이며 외부 사용자 대화가 아니다. '+REPO+'/blob/main/experiments/request-contract-v3/RESULTS.md'),
        dict(title='T 검증: 추가 규칙의 효과 확인',
             intro='새로 고정한 합성 대화 8개, 32턴. S와 표본 수를 합산하지 않음',
             table=rows(t, [('baseline_restore','공통 기준'),('isolated_restore','항목별 적용'),('keep_remove','유지·삭제'),('isolated_keep_remove','항목별 적용 + 유지·삭제')]),
             foot='유지·삭제가 T7 마지막 턴을 바로잡았다. 항목별 적용을 더한 이점은 없었다.',
             notes='논문 표 2. 항목별 적용은 잘못된 항목 때문에 다른 유효 변경까지 버리는 오류를 줄이려는 후보다. S 사후 재계산의 32/32는 개발 결과로만 보존했다. 코드를 수정하지 않고 새 T에 적용한 결과, 항목별 적용 추가 이점이 없어서 단순한 유지·삭제를 선택했다. 항목 정확은 187,187,189,189/192. '+REPO+'/blob/main/experiments/isolated-contract-v1/RESULTS.md'),
        dict(title='실제 인물 R01: 식물 삭제와 배경 유지', person='R01',
             foot='원본: Monstera Production / Pexels. 의상·장신구·배경은 AI 편집 결과.',
             notes='입력이 달랐던 R01의 두 비교 쌍 전체. 3턴에서 식물 삭제와 재킷 유지, 4턴에서 상의·목걸이 원본 복원과 재킷·연한 파란 배경 유지를 요청했다. 원본 출력은 자르거나 보정하지 않았다. 사진 속 인물의 실제 행동이나 연구 참여를 나타내지 않는다. 원본 https://www.pexels.com/photo/confident-black-man-in-studio-6311573/\n'+REPO+'/blob/main/paper/figures/figure-provenance.json'),
        dict(title='실제 인물 R02: 동일한 요청의 편집 결과', person='R02',
             foot='원본: Monstera Production / Pexels. 의상·장신구·배경은 AI 편집 결과.',
             notes='입력이 달랐던 R02의 두 비교 쌍 전체. R01과 동일한 S3 3·4턴. 3B는 3턴 기준 출력에서 JSON 파싱에 실패했다. 7B는 같은 출력의 식물 설명과 점수가 모순되었다. 그림의 사례 설명과 AI 점수를 구분한다. 원본 출력은 자르거나 보정하지 않았다. 사진 속 인물의 실제 행동이나 연구 참여를 나타내지 않는다. 원본 https://www.pexels.com/photo/cheerful-black-woman-in-studio-6311581/\n'+REPO+'/blob/main/paper/figures/figure-provenance.json'),
        dict(title='이미지 평가: 점수 증가의 해석 범위',
             intro='실제 사진 2명 × 32턴 × 두 방법 = 128조건, 고유 생성 이미지 66개',
             table=images,
             below='3B 증가 8개 중 6개는 판단 불가가 성공으로 바뀐 항목\n7B에서도 설명 모순이 남아 이미지 품질 개선은 미확정',
             foot='목표 충족은 방법당 64조건 × 6항목으로 집계한다.\n64쌍 중 서로 다른 입력은 4쌍이며 나머지 60쌍은 같은 출력을 공유한다.',
             notes='논문 표 3~5. Qwen2.5-VL-3B-4bit 1차와 같은 계열 7B-4bit 사후 민감도 분석. 출력·목표를 함께 구분한 고유 AI 평가 입력은 68개다. 3B 판단 불가 20/13, 7B 0/0. 3B 파싱 실패 3개, 7B 0개. 7B는 1차 오류를 본 뒤 계획했으므로 독립 정답 검증으로 해석하지 않는다. 두 평가가 공통으로 실패에서 성공으로 판정한 것은 R02 S3 4턴 배경 한 항목이다. 얼굴 코사인 평균 '+f"{first['baseline_restore']['face_mean']:.6f}, {first['keep_remove']['face_mean']:.6f}"+'이며 서로 다른 네 쌍은 두 쌍 상승·두 쌍 하락이다. 얼굴 개선 또는 비열등성 증거가 아니다. 내부 생성 모델 리비전과 시드는 노출되지 않았다. '+REPO+'/blob/main/experiments/contract-image-review-v1/INTERPRETATION.md'),
        dict(title='앞선 실패에서 확인한 규칙의 범위',
             body='넓은 유지 규칙은 Q 검증에서 12/32로 하락\n문형을 좁힌 유지 단독도 최종 대화 정확 수가 감소\n\n삭제 누락까지 함께 검사하도록 방법을 수정\n조건부·대명사·지원 범위 밖 표현은 일반 추출에 맡김',
             foot='앞선 P 이미지 점수 차이는 판단 불가 한 항목의 변화였다. 실패 원문도 보존했다.',
             notes='P 텍스트에서 30/32 대 32/32였지만 넓은 keep 규칙은 off와 색 변경 등의 경계에서 실패했다. Q 공통 기준 27/32, 넓은 유지 12/32, 좁은 유지 27/32. 좁은 유지의 최종 대화는 기준 6/8에서 5/8로 낮았다. 이후 유지·삭제 결합을 개발하고 S에서 고정 검증했다. P 이미지 128조건·68개 고유 출력은 354/384 대 355/384이며 판단 불가 한 항목이 성공으로 바뀌었을 뿐 실패에서 성공 전환은 없었다. '+REPO+'/blob/main/RESEARCH_INDEX.md'),
        dict(title='결론: 명시적 지시를 분리해 검사하는 효과',
             body='유지 보호와 삭제 실행이 서로 다른 상태 오류를 줄임\n같은 모델 응답을 사용하고 추가 호출 없이 적용\n\n검증 범위는 제한된 영어 문형과 소수의 합성 대화\n실제 사진 2명의 결과만으로 일반적인 품질 향상은 미확정',
             foot='얼굴 유사도는 입력이 다른 4쌍 중 2쌍 상승·2쌍 하락. 얼굴 보존 개선도 미확정.',
             notes='S 정확 턴 27/32 대 29/32, T 28/32 대 29/32. 각각의 향상은 S3와 T7에 집중됐다. 연구용 합성 대화와 단일 4B 추출 모델에 한정된다. 과거 상태가 잘못됐다면 유지 규칙도 잘못된 값을 보존할 수 있다. AI 평가와 얼굴 계산 지표의 한계를 명시한다. 새로운 독립 사용자 자료나 다른 추출 모델에서의 일반화는 검증되지 않았다. 본 연구는 비교에서 그치지 않고 검사 방법을 구현하고 구성요소별 오류를 검증했지만 광범위한 효과나 논문 채택을 보장하지 않는다.'),
        dict(title='논문과 재현 자료',
             body='논문 PDF 및 Word\nS·T 요청, 정답, 모델 응답과 고정 코드\n전체 생성 이미지와 AI 평가 원문\n개발 과정의 실패 후보와 실험 색인',
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
                text_box(req,sid,f'label{j}',f"{3+j//2}턴  {'공통 기준' if j%2==0 else '유지·삭제'}",70+j*211,103,204,33,18,True)
                # Google fits the complete original image inside the box, preserving aspect ratio.
                req.append({'createImage':{'objectId':sid+f'_method_image{j}', 'url':f'https://raw.githubusercontent.com/kimmireu0220/inha-capstone/{IMAGE_COMMIT}/'+source['source'],'elementProperties':props(sid,70+j*211,147,190,285)}})
        if number==10:
            text_box(req,sid,'link','논문 PDF 열기',70,377,300,40,20,False,REPO+'/blob/main/paper/manuscript.inha.pdf')
        note_id=slides[sid]['slideProperties']['notesPage']['notesProperties']['speakerNotesObjectId']
        req += [{'deleteText':{'objectId':note_id,'textRange':{'type':'ALL'}}}, {'insertText':{'objectId':note_id,'text':item['notes']}}]
    return req


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    old=json.loads(args.snapshot.read_text())
    if old['presentationId'] != PRESENTATION_ID:
        raise SystemExit('Snapshot belongs to another deck.')
    req=requests(old)
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
