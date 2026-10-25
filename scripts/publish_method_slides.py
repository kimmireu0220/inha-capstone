"""Update the existing Google deck from frozen evidence; dry-run by default.

Requires a freshly inspected snapshot. A revision lock prevents overwriting
concurrent edits. Raw snapshots stay in the ignored private build directory.
"""
import argparse
import json
from pathlib import Path

from googleapiclient.discovery import build
from update_google_slides import credentials, DEFAULT_CLIENT_FILE, PRESENTATION_ID

from method_slides_content import ROOT, REPO, IMAGE_COMMIT, IDS, SOURCES, load, sha, spec, image_label, image_sources


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
            text_box(req,sid,'below',item['below'],70,item.get('below_y',337),820,item.get('below_h',111),item.get('below_size',21))
        sources = image_sources(item)
        if sources:
            step = 844 / len(sources)
            for j, source in enumerate(sources):
                text_box(req,sid,f'label{j}',source['label'],70+j*step,103,step-7,33,18,True)
                # Fit the complete original photograph without cropping.
                req.append({'createImage':{'objectId':sid+f'_method_image{j}', 'url':source['url'],'elementProperties':props(sid,70+j*step,147,step-21,285)}})
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
        for j, source in enumerate(image_sources(item)):
            oid = sid + f'_method_label{j}'
            if oid not in elements:
                raise ValueError(f'Missing image label: {oid}')
            replace(oid, source['label'])
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
