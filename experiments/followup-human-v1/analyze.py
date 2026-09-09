"""Analyze the user's real pilot submission; never creates human responses."""
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
PRIVATE=ROOT/'private'
SID='c6bf07cc-0eec-4af4-8f12-81cea09f2ae9'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def table(h,rows):return '\n'.join(['| '+' | '.join(h)+' |','| '+' | '.join(['---']*len(h))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    PRIVATE.mkdir(exist_ok=True)
    snapshot=PRIVATE/'submission.json'
    if not snapshot.exists():
        found=[]
        for p in (REPO/'evaluation/.wrangler').rglob('*.sqlite'):
            db=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True)
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='submissions'").fetchone():
                row=db.execute('SELECT payload,received_at FROM submissions WHERE id=?',(SID,)).fetchone()
                if row:found.append({'payload':json.loads(row[0]),'received_at':row[1]})
            db.close()
        assert len(found)==1
        save(snapshot,found[0])
    record=json.loads(snapshot.read_text());d=record['payload']
    assert d['id']==SID and d['schema']=='followup-batch-sequential-human-v1'
    keypath=PRIVATE/'mapping.json'
    if not keypath.exists():keypath.write_bytes((REPO/'evaluation/private/followup-key.json').read_bytes())
    mapping={x['id']:x for x in json.loads(keypath.read_text())}
    assert set(d['order'])==set(mapping) and len(d['order'])==12 and len(d['answers'])==24
    metrics={};plans={}
    for study in ('edit-order-v1','edit-replication-v1'):
        p=ROOT.parent/study
        metrics[study]={r['id']:r for r in json.loads((p/'results.json').read_text())['rows']}
        plans[study]={j['id']:j for j in json.loads((p/'plan.json').read_text())['jobs']}
    rows=[];times=[]
    for cid in d['order']:
        m=mapping[cid];r=metrics[m['study']][m['source_id']];job=plans[m['study']][m['source_id']]
        assert d['imageHashes'][cid]==m['hashes'] and d['displayRegions'][cid]==m['roi']
        out=REPO/('experiments/'+job['output'].split('/experiments/',1)[1]);assert sha(out)==m['hashes']['candidate']
        row={k:m[k] for k in ('person','arm','repeat','study','source_id')}
        for kind,allowed in [('face',{'0','1','2','3','unknown'}),('preservation',{'0','1','2','unknown'})]:
            a=d['answers'][cid+'-'+kind];assert a['value'] in allowed
            row[kind]=None if a['value']=='unknown' else int(a['value'])
            times.append((datetime.fromisoformat(a['updatedAt'].replace('Z','+00:00')),cid+'-'+kind))
        for mode in ('fixed','1','3','6'):
            for scope,keys in [('face',('mae','ssim','lpips')),('skin',('mae','ssim','highpass_mae'))]:
                for k in keys:row[scope+'_'+k+'_'+mode]=r['original'][scope][mode][k]
        rows.append(row)
    assert {(r['person'],r['arm'],r['repeat']) for r in rows}=={(p,a,n) for p in ('P04','P05','P06') for a in ('batch','SBP') for n in (1,2)}
    groups={}
    for arm in ('batch','SBP'):
        selected=[r for r in rows if r['arm']==arm]
        groups[arm]={k:{'counts':dict(Counter('unknown' if r[k] is None else str(r[k]) for r in selected)), 'mean':float(np.mean([r[k] for r in selected if r[k] is not None]))} for k in ('face','preservation')}
    pairs=[]
    for p in ('P04','P05','P06'):
        for n in (1,2):
            a=next(r for r in rows if r['person']==p and r['repeat']==n and r['arm']=='batch');b=next(r for r in rows if r['person']==p and r['repeat']==n and r['arm']=='SBP')
            pairs.append({'person':p,'repeat':n,'batch_face':a['face'],'sequential_face':b['face'],'batch_preservation':a['preservation'],'sequential_preservation':b['preservation']})
    correlations=[]
    for target in ('face','preservation'):
        for mode in ('fixed','1','3','6'):
            for scope,k in [('face','mae'),('face','ssim'),('face','lpips'),('skin','mae'),('skin','ssim'),('skin','highpass_mae')]:
                selected=[r for r in rows if r[target] is not None]
                rho=float(spearmanr([r[target] for r in selected],[r[scope+'_'+k+'_'+mode] for r in selected]).statistic)
                correlations.append({'human_item':target,'metric':scope+'/'+k,'mode':mode,'n':len(selected),'spearman_rho':rho})
    times.sort();short=[{'earlier':a[1],'later':b[1],'seconds':(b[0]-a[0]).total_seconds()} for a,b in zip(times,times[1:]) if (b[0]-a[0]).total_seconds()<.1]
    save(PRIVATE/'decoded.json',rows);save(PRIVATE/'timing-diagnostic.json',{'short_intervals_under_100ms':short,'note':'Updated-at timestamps are not viewing durations; no responses excluded.'})
    with (PRIVATE/'decoded.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'respondents':1,'images':12,'answers':24,'groups':groups,'pairs':pairs,'correlations':correlations,'short_updated_at_intervals_under_100ms':len(short),'exclusions':0,'exposure':'initiating researcher previously shown results and hypotheses; pilot only','inter_rater_reliability':'not_estimable_one_rater'}
    save(ROOT/'summary.json',summary)
    save(ROOT/'verification.json',{'passed':True,'submission_sha256':sha(snapshot),'mapping_sha256':sha(keypath),'source_results_sha256':{s:sha(ROOT.parent/s/'results.json') for s in metrics},'image_hashes_and_roi_matched':True,'complete_balanced_cells':True,'analysis_sha256':sha(Path(__file__))})
    counts=[]
    for arm,label in [('batch','일괄'),('SBP','순차')]:
        g=groups[arm];counts.append([label,*[g['face']['counts'].get(str(i),0) for i in range(4)],*[g['preservation']['counts'].get(str(i),0) for i in (2,1,0)]])
    ct=table(['방법','열화 없음','약함','뚜렷함','심함','얼굴 유지','일부 유지','미유지'],counts)
    pt=table(['인물','반복','일괄 열화','순차 열화','일괄 보존','순차 보존'],[[p[k] for k in ('person','repeat','batch_face','sequential_face','batch_preservation','sequential_preservation')] for p in pairs])
    corr=table(['사람 항목','자동 지표','Spearman ρ'],[[x['human_item'],x['metric'],f"{x['spearman_rho']:.3f}"] for x in correlations if x['mode']=='fixed'])
    text=f'''# 후속12개 출력 — 사람1명 예비 평가

2026-09-09. 사용자가 실제 제출한 얼굴 열화12개·얼굴 보존12개 응답을 분석했다. 최초 원본 P04/P05/P06 × 일괄/SBP × 두 반복의 최종 출력이다. 이전16개 출력의 R01 평가와 합산하지 않았다.

## 이번 응답에서 얻은 결론

인물·반복을 맞춘6쌍 중 일괄 편집의 피부 열화가 더 낮은 경우4쌍, 같은 경우2쌍이었다. 얼굴 보존은 일괄이 더 높은 경우5쌍, 같은 경우1쌍이었다. 반대 방향은 없었다. 일괄6개는 모두 얼굴 유지, 순차6개는 유지1개·미유지5개였다. 이번 한 평가자의 판단은 원본 기반 일괄 편집이 얼굴 보존에 유리하다는 관측을 지지한다.

피부 열화와 고정 얼굴 MAE의 순위상관은−0.023으로 거의 대응하지 않았다. LPIPS는+0.565, SSIM은−0.374였다. 얼굴 보존과는 LPIPS−0.710, SSIM+0.661이었다. 따라서 모든 자동 지표가 사람 판단과 일치한다고 결론 내릴 수 없으며, 이12개에서 LPIPS가 상대적으로 더 잘 대응했다는 기술 결과다. 이 응답에 맞춘 지표 선택의 외부 검증은 없다.

## 방법별 분포

{ct}

열화는0=없음,1=약함,2=뚜렷함,3=심함. 보존은2=유지,1=일부 유지,0=미유지. 판단 어려움은 별도 처리하며 결측을0으로 바꾸지 않는다. [기술 집계](summary.json)에 평균도 남겼지만 순서형 척도이므로 등급 분포를 우선한다.

## 인물·반복별 비교

{pt}

동일 반복 번호는 같은 생성 seed를 사용한 짝이 아니다. 동일 인물·실험 블록 안의 방법 비교다. 6쌍을6명의 독립 인물처럼 다루지 않는다.

## 자동 지표와의 기술적 상관

{corr}

열화는 높은 점수가 나쁘고 보존은 높은 점수가 좋다. MAE·LPIPS와 SSIM의 방향도 반대이므로 상관의 부호를 고려해야 한다. 반복 출력·동일 인물·두 방법이 섞인12관측의 기술 상관이며 유의성 검정이나 예측 성능 검증이 아니다. 두 방법 간 차이만으로 상관이 커질 수 있다. NCCsigma1/3/6 상관도 summary.json에 보존했다. 사람 등급과 지표는 척도가 달라 임의 임계값으로 일치율을 만들지 않았다. 독립 AI 등급은 이12개에 없으므로 새 AI 등급 일치율도 계산하지 않았다.

## 해석의 한계와 응답 기록

평가자는 연구 진행자이며 이미 결과 이미지와 연구 결론을 전달받았다. 화면에서 방법명을 숨겼더라도 완전한 블라인드 독립 검증이 아니다. 사람1명이므로 평가자 간 일관성은 계산할 수 없다. 비얼굴 편집 요구 성공·전체 이미지 자연스러움은 별도 문항으로 평가하지 않았다.

응답 갱신 시각 사이100ms 미만 간격이 {len(short)}건 있었다. 갱신 시각은 실제 관찰 시간을 측정한 값이 아니며 빠른 클릭·수정 등 이유를 확정할 수 없다. 자동 다음 문항 이동을 사용한 설문이다. 이 기록을 이유로 응답을 제외하거나 교체하지 않았다. 원문과 세부 시간 기록은 private 폴더에 보관한다.

## 검증과 재현

제출 스키마,24개 응답,12개 후보,3×2×2 구성, 표시 ROI와 이미지 해시 및 실험 출력 연결을 검증했다. [검증 기록](verification.json). 원본 제출과 ID 해독표·개별 응답은 Git에서 제외된 private 폴더에 별도로 보존했다. 로컬 DB의 응답을 수정하지 않았다.

`.venv-metrics/bin/python experiments/followup-human-v1/analyze.py`

비공개 원본이 있는 환경에서만 재현할 수 있다. 위 명령은 저장된 실제 응답을 읽으며 사람 평가를 생성하지 않는다.
'''
    if (ROOT/'RECHECKED_RESULTS.md').exists():
        text=text.replace('2026-09-09.', '> 이후 두 문항을 재평가했다. 최신 값은 [재평가 반영 결과](RECHECKED_RESULTS.md)를 참고한다. 아래는 보존된 최초 분석이다.\n\n2026-09-09.', 1)
    (ROOT/'RESULTS.md').write_text(text)
    print(ct);print(pt);print(corr);print('short intervals',len(short))

if __name__=='__main__':main()
