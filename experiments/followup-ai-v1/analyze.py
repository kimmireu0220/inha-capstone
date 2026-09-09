"""Join separately collected AI grades to hash-matched corrected human data."""
import hashlib,json
from pathlib import Path
from collections import Counter
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d): p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
    rf=ROOT/'independent-ratings.json'; ratings=read(rf)['ratings']; frozen=sha(rf)
    key=read(ROOT/'private/key.json'); packet=read(ROOT/'packet-verification.json')
    assert len(ratings)==len({r['id'] for r in ratings})==15
    assert {r['id'] for r in ratings}=={r['id'] for r in key}
    assert all(r['severity'] in (0,1,2,3,None) for r in ratings)
    for p,h in packet['plate_sha256'].items(): assert sha(ROOT/p)==h
    hp=REPO/'experiments/followup-human-v1/private'
    mapping={r['id']:r for r in read(hp/'mapping.json')}
    human={(r['study'],r['source_id']):r for r in read(hp/'decoded-rechecked.json')}
    grades={r['id']:r for r in ratings}; rows=[]; controls=[]
    for k in key:
        assert sha(Path(k['reference']))==k['reference_sha256']
        assert sha(Path(k['path']))==k['output_sha256']
        if k['kind']!='candidate':
            assert k['reference_sha256']==k['output_sha256']
            controls.append(grades[k['id']]); continue
        m=mapping[k['source_id']]
        assert m['hashes']['candidate']==k['output_sha256'] and m['hashes']['reference']==k['reference_sha256'] and m['roi']==k['roi']
        rows.append({**human[(m['study'],m['source_id'])], 'ai_id':k['id'],'ai_face':grades[k['id']]['severity'],'output_sha256':k['output_sha256']})
    assert len(rows)==len({r['output_sha256'] for r in rows})==12
    complete=[r for r in rows if r['ai_face'] is not None and r['face'] is not None]
    confusion=[[sum(r['face']==i and r['ai_face']==j for r in complete) for j in range(4)] for i in range(4)]
    corr={k:float(spearmanr([r['ai_face'] for r in complete],[r[k] for r in complete]).statistic) for k in ['face']+[k for k in rows[0] if k.startswith(('face_','skin_'))]}
    summary={'images':12,'ai_sessions':1,'human_respondents':1,'ai_human_results_provided':False,'ai_same_person_assessed':False,'complete_pairs':len(complete),'exact_agreement':sum(r['ai_face']==r['face'] for r in complete),'within_one_grade':sum(abs(r['ai_face']-r['face'])<=1 for r in complete),'confusion_rows_human_columns_ai':confusion,'groups':{a:{'ai':dict(Counter(str(r['ai_face']) for r in rows if r['arm']==a)),'human':dict(Counter(str(r['face']) for r in rows if r['arm']==a))} for a in ['batch','SBP']},'spearman_ai':corr,'controls':{'count':len(controls),'zero_grade':sum(r['severity']==0 for r in controls)}}
    save(ROOT/'private/joined.json',rows); save(ROOT/'summary.json',summary)
    assert sha(rf)==frozen
    save(ROOT/'verification.json',{'passed':True,'ratings_sha256':frozen,'human_corrected_sha256':sha(hp/'decoded-rechecked.json'),'packet_sha256':sha(ROOT/'packet-verification.json'),'analysis_sha256':sha(Path(__file__)),'final_protocol_sha256':sha(ROOT/'PROTOCOL.md'),'unique_hash_matched_candidates':12,'plate_and_source_hashes_verified':True,'roi_matches_human':True})
    table='\n'.join('| '+a+' | '+str(summary['groups'][a]['ai'])+' | '+str(summary['groups'][a]['human'])+' |' for a in ['batch','SBP'])
    (ROOT/'RESULTS.md').write_text(f'''# 후속12개 AI·사람·자동 지표 연결

대화 이력을 전달하지 않은 별도 에이전트가 익명 비교판과 0~3점 기준만 받아 평가했다. 사람 답·방법명·자동 지표를 제공하지 않았다. 본 대화에서 작성 중이던 점수는 사용하지 않았다. AI 등급 저장 후 이미지 SHA-256과 얼굴 ROI를 확인해 두 문항 재평가를 반영한 사람 응답 및 MAE·SSIM·LPIPS에 연결했다.

| 방법 | AI 등급 분포 | 사람 등급 분포 |
| --- | --- | --- |
{table}

AI 판단 어려움은 {12-len(complete)}개이며 해당 문항은 등급 비교에서 제외했다. 얼굴 열화 등급의 정확 일치는 {summary['exact_agreement']}/{len(complete)}, 한 등급 이내는 {summary['within_one_grade']}/{len(complete)}다. AI와 사람 등급의 Spearman ρ는 {corr['face']:.3f}다. 원본 대 원본 대조 {len(controls)}개 중 {summary['controls']['zero_grade']}개를 0점으로 평가했고 본 표본12개에 합산하지 않았다. 자동 지표별 상관과 혼동행렬은 [집계](summary.json)에 있다.

기존 설문16개는 AI 두 세션·자동 지표·사람 평가가 있고, 후속 설문12개는 이번 별도 AI 한 세션·자동 지표·사람 한 명의 평가가 모두 연결됐다. 새 생성98개 전체를 평가한 것은 아니며 나머지86개는 자동 지표 범위다. 얼굴 보존 설문은 피부 열화와 별도 항목이고 AI는 동일인 판정을 하지 않았다.

사람 평가는 결과 노출이 있는 한 명의 예비 응답이다. 별도 AI의 입력에서 사람 답을 가렸어도 사람 평가 자체가 독립 블라인드 평가가 되지는 않는다. 3개 인물의 반복12관측이므로 일치율과 상관은 기술 통계이며 일반화 성능 검증이 아니다.

[AI 원점수](independent-ratings.json) · [검증](verification.json). 재현: `.venv-metrics/bin/python experiments/followup-ai-v1/analyze.py`. 비공개 사람 원문이 필요하다.
''')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
