"""Join independent observations without consensus labels or changing originals."""
import argparse,hashlib,importlib.util,json
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'joined-reviews'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,value):
    OUT.mkdir(exist_ok=True);(OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
spec=importlib.util.spec_from_file_location('agreement_functions',ROOT/'agent-agreement/analyze.py')
aa=importlib.util.module_from_spec(spec);spec.loader.exec_module(aa)
CRITERIA=('earrings','necklace','pin','blazer','shirt','background','no_text','lighting')
def main(face_only=False):
    packets=[('face','blind-face',97,83),('extension-face','blind-extension-face',33,25),('coverage-face','blind-coverage-face',3,3)]
    all_unique={};packet_stats={};sources={}
    for label,folder,total,count in packets:
        files=[ROOT/f'private/{label}-key.json',ROOT/f'{folder}/items.json']+[ROOT/f'reviews/{label}-{r}.json' for r in 'ab']
        sources.update({str(p):sha(p) for p in files})
        private=read(files[0]);public={x['id']:x for x in read(files[1])}
        reviews={r:read(ROOT/f'reviews/{label}-{r}.json') for r in 'ab'}
        ratings={r:{x['id']:x for x in reviews[r]['items']} for r in 'ab'}
        ids={x['id'] for x in private};assert len(ids)==len(private)==total
        assert set(public)==ids
        for r in 'ab':
            assert reviews[r]['human'] is False and len(reviews[r]['items'])==len(ratings[r])==total
            assert set(ratings[r])==ids
            assert all(aa.valid_severity(x['severity']) and x['same_person']=='not_assessed' for x in ratings[r].values())
        unique=[x for x in private if 'control' not in x and 'duplicate_of_source' not in x]
        assert len(unique)==count
        for x in private:
            with Image.open(public[x['id']]['image']) as im:pair=np.asarray(im.convert('RGB'))
            for key,left in [('reference',0),('path',336)]:
                with Image.open(x[key]) as im:expected=np.asarray(im.convert('RGB').crop(x['roi']))
                assert np.array_equal(pair[32:392,left:left+320],expected)
            assert sha(x['path'])==x['output_sha256'] and sha(x['reference'])==x['reference_sha256']
        for x in unique:
            key=x['reference_sha256']+':'+x['output_sha256'];assert key not in all_unique
            all_unique[key]=dict(**x,ratings={r:ratings[r][x['id']] for r in 'ab'},packet=label)
        controls=[x for x in private if 'control' in x]
        repeats=[x for x in private if 'duplicate_of_source' in x]
        bysha={x['output_sha256']:x for x in unique}
        packet_stats[label]=dict(agreement=aa.agreement(*[[ratings[r][x['id']]['severity'] for x in unique] for r in 'ab']),controls={r:dict(n=len(controls),grades=[ratings[r][x['id']]['severity'] for x in controls]) for r in 'ab'},repeats={r:aa.agreement([ratings[r][bysha[x['duplicate_of_source']]['id']]['severity'] for x in repeats],[ratings[r][x['id']]['severity'] for x in repeats]) for r in 'ab'})
    assert len(all_unique)==111
    current=read(ROOT.parent/'revised-tail-v1/progress.json')['branches'];cfg={b['name']:b for b in current}
    curves=read(ROOT.parent/'revised-tail-v1/curves.json')
    generation=read(ROOT/'generation/progress.json')
    paths={b['name']:dict(reference=b['reference'],policy=b['policy'],rows=[dict(stage=r['stage'],output=r['path']) for r in curves if r['branch']==b['name']]) for b in current}
    for b in generation['branches']:
        rows=b['rows']
        if b['policy']=='end-only':rows=[r for r in paths[b['person']]['rows'] if r['stage']<10]+rows
        paths[b['name']]=dict(reference=b['reference'],policy=b['policy'],rows=rows)
    branch_rows={};branch_summary={}
    for name,b in paths.items():
        rows=[]
        for r in b['rows']:
            key=sha(b['reference'])+':'+sha(r['output']);x=all_unique[key]
            rows.append(dict(stage=r['stage'],key=key,id=x['id'],grades={a:x['ratings'][a]['severity'] for a in 'ab'}))
        branch_rows[name]=rows
        branch_summary[name]=dict(n_observed=len(rows),complete=len(rows)==10,policy=b['policy'],reviewers={})
        for a in 'ab':
            grades=[r['grades'][a] for r in rows];valid=[g for g in grades if g is not None]
            branch_summary[name]['reviewers'][a]=dict(final_severity=grades[-1] if len(rows)==10 else None,observed_histogram=dict(Counter(str(g) for g in grades)),clear_count=sum(g>=2 for g in valid),n_valid=len(valid),first_clear_stage=next((r['stage'] for r in rows if r['grades'][a] is not None and r['grades'][a]>=2),None))
    assert sum(len(r) for r in branch_rows.values())==198
    metric_path=ROOT/'extension-metrics/results.json';metrics=read(metric_path)['rows'];sources[str(metric_path)]=sha(metric_path)
    end_ids=list(dict.fromkeys(rows[-1]['key'] for name,rows in branch_rows.items() if name.endswith('-end-only')))
    seq_ids=[rows[-1]['key'] for name,rows in branch_rows.items() if paths[name]['policy']=='sequential']
    assert len(end_ids)==6 and len(seq_ids)==7
    signal_groups={}
    for label,keys in [('all_unique_111',list(all_unique)),('sequential_final_7',seq_ids),('original_based_final_unique_6',end_ids)]:
        signal_groups[label]=dict(n=len(keys),observations=[dict(key=k,grades={r:all_unique[k]['ratings'][r]['severity'] for r in 'ab'},fixed=metrics[k]['face']['fixed']) for k in keys],comparison={r:{m:aa.confusion([aa.alarm(m,metrics[k]['face']['fixed'][m]) for k in keys],[all_unique[k]['ratings'][r]['severity'] for k in keys]) for m in aa.METRICS} for r in 'ab'})
    face=dict(unique_count=111,packet_stats=packet_stats,overall_agreement=aa.agreement(*[[x['ratings'][r]['severity'] for x in all_unique.values()] for r in 'ab']),unique_outputs=all_unique,branch_rows=branch_rows,branch_summary=branch_summary)
    save('face.json',face)
    save('signal-transfer.json',dict(exploratory_posthoc=True,note='Groups examined after observing independent ratings; descriptive discrepancy, not a newly tuned detector or human validation.',groups=signal_groups))
    if not face_only:
        key=read(ROOT/'private/requirements-key.json');public=read(ROOT/'blind-requirements/items.json');assert len(key)==len(public)==16
        raw={r:read(ROOT/f'reviews/requirements-{r}.json') for r in 'ab'}
        indexed={r:{x['id']:x for x in raw[r]['items']} for r in 'ab'}
        ids={x['id'] for x in key}
        public_index={x['id']:x for x in public}
        assert len(ids)==len(public_index)==16 and set(public_index)==ids
        for x in key:
            candidate=Path(public_index[x['id']]['candidate']);reference=Path(public_index[x['id']]['reference'])
            assert sha(candidate)==sha(x['path'])==x['output_sha256']
            assert sha(reference)==sha(x['reference'])==x['reference_sha256']
            sources[str(candidate)]=sha(candidate);sources[str(reference)]=sha(reference)
        for r in 'ab':
            assert raw[r]['human'] is False and set(indexed[r])==ids and len(raw[r]['items'])==16
            for x in indexed[r].values():
                assert set(x['criteria'])==set(CRITERIA)
                assert all(v['score'] is None or (type(v['score']) is int and v['score'] in range(3)) for v in x['criteria'].values())
                assert aa.valid_severity(x['overall_artificiality']['severity'])
        joined=[dict(**x,ratings={r:indexed[r][x['id']] for r in 'ab'}) for x in key]
        stats={r:{c:dict(Counter(str(indexed[r][x['id']]['criteria'][c]['score']) for x in key)) for c in CRITERIA} for r in 'ab'}
        strict={r:dict(n=16,all_eight_fulfilled=sum(all(indexed[r][x['id']]['criteria'][c]['score']==2 for c in CRITERIA) for x in key),any_unknown=sum(any(indexed[r][x['id']]['criteria'][c]['score'] is None for c in CRITERIA) for x in key)) for r in 'ab'}
        mismatches=[dict(id=x['id'],criterion=c,a=indexed['a'][x['id']]['criteria'][c]['score'],b=indexed['b'][x['id']]['criteria'][c]['score']) for x in key for c in CRITERIA if indexed['a'][x['id']]['criteria'][c]['score']!=indexed['b'][x['id']]['criteria'][c]['score']]
        save('requirements.json',dict(unique_count=16,branch_count=sum(len(x['sources']) for x in key),items=joined,criterion_distributions=stats,strict_all_fulfilled=strict,disagreements=mismatches,exact_agreement_including_unknown=dict(n=128,equal=128-len(mismatches)),note='Unknown is retained, not treated as failed; no consensus label.'))
        for p in [ROOT/'private/requirements-key.json',ROOT/'blind-requirements/INSTRUCTIONS.md',ROOT/'blind-requirements/items.json']+[ROOT/f'reviews/requirements-{r}.json' for r in 'ab']:sources[str(p)]=sha(p)
    for p in [ROOT/'generation/progress.json',ROOT.parent/'revised-tail-v1/curves.json',ROOT.parent/'revised-tail-v1/progress.json',ROOT/'agent-agreement/analyze.py',Path(__file__)]:sources[str(p)]=sha(p)
    save('validation.json',dict(passed=True,face_packets=3,face_observations_per_reviewer=133,unique_faces=111,observed_branch_stages=198,missing_final=['P05-once-triggered'],requirements_included=not face_only,checks=['exact_id_coverage','unique_id_and_hash','native_crop_pixel_equality','raw_hashes_unchanged','valid_severity_and_no_identity_inference','repeat_and_control_excluded','all_observed_branches_joined','missing_final_not_imputed','separate_AI_ratings','requirements_schema_if_available'],source_hashes=sources))
    print(json.dumps(dict(unique_faces=111,face_agreement=face['overall_agreement'],branches=branch_summary,requirements_included=not face_only),ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--face-only',action='store_true');main(p.parse_args().face_only)
