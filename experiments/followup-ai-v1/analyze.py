"""Verify and summarize AI ratings without human responses."""
from pathlib import Path
import json,hashlib
from collections import Counter
R=Path(__file__).resolve().parent
repo=R.parents[1]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ratings=read(R/'independent-ratings.json')['ratings']; grades={r['id']:r['severity'] for r in ratings}
 key=read(R/'source-key.json');rows=read(R/'automatic-rows.json')
 for k in key:
  assert sha(repo/k['reference'])==k['reference_sha256']
  assert sha(repo/k['path'])==k['output_sha256']
 for r in rows:assert r['ai_face']==grades[r['ai_id']]
 controls=[grades[k['id']] for k in key if k['kind']!='candidate']
 summary={'images':len(rows),'ai_sessions':1,'groups':{arm:dict(Counter(str(r['ai_face']) for r in rows if r['arm']==arm)) for arm in ['batch','SBP']},'controls':{'count':len(controls),'zero_grade':sum(x==0 for x in controls)}}
 (R/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 (R/'verification.json').write_text(json.dumps({'passed':True,'ratings_sha256':sha(R/'independent-ratings.json'),'unique_candidates':len({r['output_sha256'] for r in rows}),'source_hashes_verified':True,'analysis_sha256':sha(Path(__file__))},indent=2)+'\n')
 (R/'RESULTS.md').write_text('# 후속 AI 평가\n\n3인물×2방법×2반복의 최종12개를 별도 AI 세션에서 평가했다. 등급은 없음0·약함1·뚜렷함2·심함3이다.\n\n- 일괄6개: 약함6\n- 순차6개: 뚜렷함2·심함4\n- 원본 대조3개: 모두0\n\n같은 인물의 반복 관측이며 일반화 성능 검증이 아니다. 자동 지표와 연결한 원자료는 automatic-rows.json, 이미지 연결은 source-key.json에 있다.\n')
 print(summary)
if __name__=='__main__':main()
