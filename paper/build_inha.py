from pathlib import Path
import argparse,re,json
from docx import Document
from docx.shared import Pt,Cm,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
R=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='Build the paper using the established Inha review layout.')
parser.add_argument('--output-dir',type=Path,default=R,
                    help='Use a private directory for draft layout review; defaults to paper/.')
parser.add_argument('--source-dir',type=Path,default=R,
                    help='Optional draft source directory; author metadata remains in paper/.')
args=parser.parse_args()
OUT=args.output_dir.resolve()
SOURCE=args.source_dir.resolve()
OUT.mkdir(parents=True,exist_ok=True)
s=(SOURCE/'manuscript.ko.md').read_text().strip()
abstract=(SOURCE/'abstract.en.txt').read_text().strip()
metadata=json.loads((SOURCE/'layout.json').read_text()) if (SOURCE/'layout.json').exists() else {}
auth=json.loads((R/'authors.json').read_text()) if (R/'authors.json').exists() else {'korean':'________________','english':'________________','advisor_korean':'________________','advisor_english':'________________'}
d=Document();sec=d.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7);sec.top_margin=Cm(2);sec.bottom_margin=Cm(2);sec.left_margin=Cm(2);sec.right_margin=Cm(2)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Caption']:
 st=d.styles[name];st.font.name='Times New Roman';st.font.size=Pt(10);st.font.color.rgb=RGBColor(0,0,0);rf=st._element.get_or_add_rPr().rFonts;rf.set(qn('w:eastAsia'),'AppleMyungjo')
 for k in list(rf.attrib):
  if 'Theme' in k:del rf.attrib[k]
 for el in list(st._element.iter(qn('w:pBdr'))):el.getparent().remove(el)
n=d.styles['Normal'].paragraph_format;n.line_spacing=Pt(13);n.space_after=Pt(3);n.first_line_indent=Cm(.3);n.widow_control=True
for name in ['Heading 1','Heading 2']:
 st=d.styles[name];st.font.name='Apple SD Gothic Neo';st._element.rPr.rFonts.set(qn('w:eastAsia'),'Apple SD Gothic Neo');st.font.bold=True;st.font.size=Pt(11 if name=='Heading 1' else 10);st.paragraph_format.first_line_indent=Pt(0);st.paragraph_format.space_before=Pt(10);st.paragraph_format.space_after=Pt(6)
d.styles['Heading 1'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
for name in ['Title','Subtitle']:d.styles[name].paragraph_format.first_line_indent=Pt(0)
d.styles['Title'].font.size=Pt(17);d.styles['Title']._element.rPr.rFonts.set(qn('w:eastAsia'),'Apple SD Gothic Neo');d.styles['Title'].font.bold=True
d.styles['Subtitle'].font.italic=False;d.styles['Subtitle'].font.size=Pt(14);d.styles['Subtitle'].font.bold=True

def center(text,style=None):
 p=d.add_paragraph(text,style);p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Pt(0);return p

center(s.splitlines()[0][2:],'Title').paragraph_format.line_spacing=Pt(24)
center(s.splitlines()[2],'Subtitle').paragraph_format.line_spacing=Pt(18)
center(auth['korean']).paragraph_format.space_before=Pt(12)
if auth['english'].strip('_ ,'):
 center('('+auth['english']+')')
center('지도교수: '+auth['advisor_korean']).paragraph_format.space_before=Pt(6)
center('('+auth['advisor_english']+')').paragraph_format.space_after=Pt(14)
ko=s.split('## 초록\n')[1].split('\n\n주요어:')[0].strip()
for label,txt in [('요약: ',ko),('Abstract: ',abstract),('Keywords: ',metadata.get('keywords','Iterative portrait editing, Facial preservation, Original-referenced regeneration, Final-request synthesis'))]:
 p=d.add_paragraph();p.paragraph_format.first_line_indent=Pt(0);p.add_run(label).bold=True;p.add_run(txt)
lines=s.split('## 1. 서론')[1];lines='## 1. 서론'+lines
lines=lines.splitlines();i=0;tn=0;roman=['I','II','III','IV','V','VI','VII']
caps=['합성 인물의 입력 정책 비교','실제 인물의 최종 목표와 얼굴 유사도','인물별 목표와 얼굴 유사도','편집 이력별 목표 충족','자동 상태 갱신의 목표 충족과 얼굴 유사도','새 대화의 인물별 비교','전체 대화 상태 추출을 포함한 추가 대조']
caps=metadata.get('table_captions',caps)
while i<len(lines):
 line=lines[i]
 if not line:i+=1;continue
 if line.startswith('|'):
  rows=[]
  while i<len(lines) and lines[i].startswith('|'):
   rr=[x.strip() for x in lines[i].strip('|').split('|')]
   if not all(re.fullmatch('[-: ]+',v) for v in rr):rows.append(rr)
   i+=1
  tn+=1
  p=d.add_paragraph(f'표 {tn}. {caps[tn-1]}','Caption');p.paragraph_format.keep_with_next=True;p.paragraph_format.first_line_indent=Pt(0);p.alignment=WD_ALIGN_PARAGRAPH.CENTER
  t=d.add_table(rows=0,cols=len(rows[0]));t.autofit=False
  width=17
  column_widths=[4.4]+[(width-4.4)/(len(rows[0])-1)]*(len(rows[0])-1)
  for col,col_width in zip(t.columns,column_widths):col.width=Cm(col_width)
  for j,row in enumerate(rows):
   cells=t.add_row().cells;pr=t.rows[-1]._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
   if j==0:pr.append(OxmlElement('w:tblHeader'))
   for column,(c,txt) in enumerate(zip(cells,row)):
    c.width=Cm(column_widths[column])
    c.text=txt
    for p in c.paragraphs:
     p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(3);p.paragraph_format.line_spacing=1
     p.paragraph_format.keep_with_next=j<len(rows)-1
     p.alignment=WD_ALIGN_PARAGRAPH.LEFT if column==0 else WD_ALIGN_PARAGRAPH.CENTER
     for run in p.runs:run.font.size=Pt(8);run.bold=j==0
    if j==0 or j==len(rows)-1:
     borders=OxmlElement('w:tcBorders');e=OxmlElement('w:bottom');e.set(qn('w:val'),'single');e.set(qn('w:sz'),'5');borders.append(e);c._tc.get_or_add_tcPr().append(borders)
  continue
 if line.startswith('!['):
  m=re.match(r'!\[(.*?)\]\((.*?)\)',line);shape=d.add_picture(str(SOURCE/m[2]),width=Cm(16.8));shape._inline.docPr.set('descr',m[1]);d.paragraphs[-1].paragraph_format.keep_with_next=True;d.paragraphs[-1].paragraph_format.line_spacing=1;d.add_paragraph(m[1],'Caption')
 elif line.startswith('### '):d.add_paragraph(re.sub(r'^\d+\.(\d+) ',r'\1. ',line[4:]),'Heading 2')
 elif line.startswith('## '):
  text=line[3:];text=re.sub(r'^(\d+)\.',lambda m:roman[int(m[1])-1]+'.',text);d.add_paragraph(text,'Heading 1')
 else:
  p=d.add_paragraph(line.replace('`',''));p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
  if line.startswith('['):p.paragraph_format.first_line_indent=Pt(0);p.paragraph_format.keep_together=True;p.alignment=WD_ALIGN_PARAGRAPH.LEFT
 i+=1
for sec in d.sections:
 f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.CENTER;f.paragraph_format.first_line_indent=Pt(0)
 if not f._p.find(qn('w:fldSimple')) is not None:
  e=OxmlElement('w:fldSimple');e.set(qn('w:instr'),'PAGE');f._p.append(e)
d.core_properties.title=s.splitlines()[0][2:];d.core_properties.author='' if '_' in auth['korean'] else auth['korean']
d.save(OUT/'manuscript.inha.docx')
author_line='저자: '+auth['korean']
if auth['english'].strip('_ ,'):
 author_line+=' ('+auth['english']+')'
(OUT/'manuscript.inha.md').write_text(s.replace('## 초록',author_line+'\n\n지도교수: '+auth['advisor_korean']+'\n\n## 초록').replace('## 1. 서론','## Abstract\n\n'+abstract+'\n\n## 1. 서론')+'\n')
print('Built Inha reference format')
