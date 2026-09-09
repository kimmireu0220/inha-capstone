"""Apply the two explicitly requested reassessments in a separate derived analysis."""
import copy
import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from scipy.stats import spearmanr
from analyze import ROOT, REPO, PRIVATE, SID, save, sha, table

RID='e265712f-2e8c-44f4-8f04-6fae749832df'
EXPECTED={'03ab8e563fdaf444-face','28b61976b7c73505-face'}

def main():
    dest=PRIVATE/'recheck-submission.json'
    if not dest.exists():
        found=[]
        for p in (REPO/'evaluation/.wrangler').rglob('*.sqlite'):
            db=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True)
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='submissions'").fetchone():
                r=db.execute('SELECT payload,received_at FROM submissions WHERE id=?',(RID,)).fetchone()
                if r:found.append({'payload':json.loads(r[0]),'received_at':r[1]})
            db.close()
        assert len(found)==1
        save(dest,found[0])
    d=json.loads(dest.read_text())['payload']
    original=json.loads((PRIVATE/'submission.json').read_text())['payload']
    assert d['id']==RID and d['correctsSubmission']==SID and d['schema']=='followup-face-recheck-v1'
    assert set(d['answers'])==EXPECTED and {i+'-face' for i in d['order']}==EXPECTED
    mapping={x['id']:x for x in json.loads((PRIVATE/'mapping.json').read_text())}
    rows=copy.deepcopy(json.loads((PRIVATE/'decoded.json').read_text()));changes=[]
    for aid,a in d['answers'].items():
        cid=aid.removesuffix('-face');m=mapping[cid]
        assert d['imageHashes'][cid]==original['imageHashes'][cid]==m['hashes']
        assert d['displayRegions'][cid]==original['displayRegions'][cid]==m['roi']
        assert a['value'] in {'0','1','2','3','unknown'}
        row=next(x for x in rows if x['study']==m['study'] and x['source_id']==m['source_id'])
        new=None if a['value']=='unknown' else int(a['value'])
        changes.append({'person':row['person'],'arm':row['arm'],'repeat':row['repeat'],'old_face':row['face'],'new_face':new});row['face']=new
    oldrows=json.loads((PRIVATE/'decoded.json').read_text())
    assert sum(a!=b for a,b in zip(rows,oldrows))==2
    assert all(a['preservation']==b['preservation'] for a,b in zip(rows,oldrows))
    groups={arm:{kind:dict(Counter('unknown' if r[kind] is None else str(r[kind]) for r in rows if r['arm']==arm)) for kind in ('face','preservation')} for arm in ('batch','SBP')}
    comparisons={k:Counter() for k in ('face','preservation')}
    for person in ('P04','P05','P06'):
        for repeat in (1,2):
            a=next(r for r in rows if r['person']==person and r['repeat']==repeat and r['arm']=='batch')
            b=next(r for r in rows if r['person']==person and r['repeat']==repeat and r['arm']=='SBP')
            for k in comparisons:
                v=(a[k]-b[k])*(1 if k=='face' else -1)
                comparisons[k]['batch_better' if v<0 else 'tie' if v==0 else 'sequential_better']+=1
    correlations=[]
    for target in ('face','preservation'):
        for mode in ('fixed','1','3','6'):
            for scope,k in [('face','mae'),('face','ssim'),('face','lpips'),('skin','mae'),('skin','ssim'),('skin','highpass_mae')]:
                selected=[r for r in rows if r[target] is not None]
                correlations.append({'human_item':target,'metric':scope+'/'+k,'mode':mode,'spearman_rho':float(spearmanr([r[target] for r in selected],[r[scope+'_'+k+'_'+mode] for r in selected]).statistic)})
    stamps=sorted(datetime.fromisoformat(a['updatedAt'].replace('Z','+00:00')) for a in d['answers'].values())
    summary={'respondents':1,'images':12,'effective_answers':24,'reassessed_answers':2,'changes':changes,'groups':groups,'paired_comparisons':comparisons,'correlations':correlations,'recheck_answer_timestamp_gap_seconds':(stamps[1]-stamps[0]).total_seconds(),'note':'Same respondent reassessment after original results were discussed. Original answers retained; not new independent observations.'}
    save(PRIVATE/'decoded-rechecked.json',rows);save(ROOT/'rechecked-summary.json',summary)
    save(ROOT/'recheck-verification.json',{'passed':True,'original_submission_sha256':sha(PRIVATE/'submission.json'),'recheck_submission_sha256':sha(dest),'original_decoded_sha256':sha(PRIVATE/'decoded.json'),'changed_face_answers':2,'preservation_unchanged':True,'image_hash_and_roi_match':True,'analysis_sha256':sha(Path(__file__))})
    ct=table(['방법','열화 없음','약함','뚜렷함','심함','얼굴 유지','일부 유지','미유지'],[[name,*[groups[arm]['face'].get(str(i),0) for i in range(4)],*[groups[arm]['preservation'].get(str(i),0) for i in (2,1,0)]] for arm,name in [('batch','일괄'),('SBP','순차')]])
    corr=table(['사람 항목','자동 지표','Spearman ρ'],[[x['human_item'],x['metric'],f"{x['spearman_rho']:.3f}"] for x in correlations if x['mode']=='fixed'])
    text=f'''# 두 문항 재평가 반영 결과

2026-09-09. 사용자가 빠른 연속 응답의 두 문항을 다시 평가했다. 두 답 모두 피부 열화0(없음)에서1(약함)로 바뀌었다. 재평가의 응답 갱신 시각 간격은{summary['recheck_answer_timestamp_gap_seconds']:.2f}초다. 시각 간격은 관찰 시간 측정값은 아니다.

최초 원문과 [최초 분석](RESULTS.md)을 보존하고 이 별도 분석에서 두 답만 반영했다. 같은 사람의 재평가이므로 독립 평가자나 이미지 수를 늘려 세지 않는다. 분석 대상은 여전히12개 이미지·24개 항목이며 얼굴 보존12개 답은 바뀌지 않았다.

## 갱신한 분포

{ct}

동일 인물·반복6쌍에서 피부 열화는 일괄이 더 낮음4쌍·동일2쌍, 얼굴 보존은 일괄이 더 높음5쌍·동일1쌍이다. 재평가 전후에 이 비교 방향은 같다. 단, 개별 등급 분포와 상관계수는 아래 갱신값을 사용한다.

## 갱신한 기술적 상관

{corr}

12관측은 동일 인물의 반복과 두 방법을 포함한다. 유의성·예측 성능 검증이 아니며 지표에 임계값을 맞추지 않았다. 전체 설정의 값은 [집계](rechecked-summary.json)에 있다.

## 해석과 검증

한 평가자가 기존 결과·가설과 최초 분석을 전달받은 뒤 재평가했다. 독립 블라인드 검증이나 평가자 간 신뢰도 측정으로 해석할 수 없다. 재평가를 선택한 이유는 빠른 응답 시각 기록이며 좋은 결과를 얻기 위해 문항을 고른 것이 아니다. 원본 응답을 삭제하거나 DB에서 덮어쓰지 않았다.

재평가가 최초 접수와 연결되는지, 두 문항의 이미지 해시·ROI가 같은지, 두 얼굴 등급만 바뀌고 보존 답이 유지되는지 검사했다. [검증](recheck-verification.json). 원문은 Git 제외 private 폴더에 보존했다.

재현: `.venv-metrics/bin/python experiments/followup-human-v1/recheck.py`
'''
    (ROOT/'RECHECKED_RESULTS.md').write_text(text)
    print(ct);print(corr)

if __name__=='__main__':main()
