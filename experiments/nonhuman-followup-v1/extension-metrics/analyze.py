"""Incremental exact metric reuse; finalize only after generation completion.

No import of generation/run.py and no reads of human or AI rating files.
"""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
EXP = PARENT.parent
GEN = PARENT/'generation'
CURRENT = EXP/'revised-tail-v1'
BASE = PARENT/'metrics'
spec = importlib.util.spec_from_file_location('frozen_pure_metrics', BASE/'analyze.py')
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)
THRESHOLD = .0555075


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def request_key(input_path, prompt):
    return hashlib.sha256((sha(input_path)+'\n'+prompt).encode()).hexdigest()


def row_key(reference, output):
    return sha(reference)+':'+sha(output)


def first_recurrence(stage_rows, reset_stage):
    reset = next(r for r in stage_rows if r['stage'] == reset_stage)
    later = [r for r in stage_rows if r['stage'] > reset_stage]
    observed = next((r for r in later if r['raw_fixed_lpips'] >= THRESHOLD), None)
    return {'reset_stage': reset_stage, 'reset_final_fixed_lpips': reset['final_fixed_lpips'],
            'reset_below_frozen_threshold': reset['final_fixed_lpips'] < THRESHOLD,
            'first_later_raw_alarm_stage': observed['stage'] if observed else None,
            'edits_after_reset_until_first_alarm': observed['stage']-reset_stage if observed else None,
            'first_later_raw_alarm_lpips': observed['raw_fixed_lpips'] if observed else None,
            'later_stages_observed': len(later),
            'status': 'observed' if observed else ('no_later_stage' if not later else 'not_observed_in_remaining_stages')}


def main(finalize=False):
    inputs = read(CURRENT/'inputs.json')
    current = read(CURRENT/'progress.json')
    curves = read(CURRENT/'curves.json')
    generation = read(GEN/'progress.json')
    old = read(BASE/'results.json')
    old_manifest = read(BASE/'manifest.json')
    configs = {b['name']: b for b in inputs}
    current_branches = {b['name']: b for b in current['branches']}
    stages = [read(EXP/'trigger-validation-v1/P04'/f'step-{n}.call.json') for n in range(1,9)] + read(CURRENT/'prompts.json')
    rebase_prefix = read(EXP/'trigger-validation-v1/rebase-template.json')['prefix']
    expected_state = {r['stage']: r['state'] for r in stages}
    expected_edit_prompt = {r['stage']: r['prompt'] for r in stages}
    expected_rebase_prompt = {n: rebase_prefix+'\n'.join('- '+v for v in state.values()) for n,state in expected_state.items()}
    stable_sources = [Path(__file__), ROOT/'PROTOCOL.md', BASE/'analyze.py', BASE/'results.json', BASE/'manifest.json',
                      CURRENT/'inputs.json', CURRENT/'progress.json', CURRENT/'curves.json', CURRENT/'prompts.json',
                      GEN/'run.py', EXP/'trigger-validation-v1/rebase-template.json']
    stable_sources += [EXP/'trigger-validation-v1/P04'/f'step-{n}.call.json' for n in range(1,9)]
    sources = {str(p): sha(p) for p in stable_sources}
    image_hashes, call_audit = {}, {}
    for b in inputs:
        assert sha(b['reference']) == b['reference_sha256']
        image_hashes[b['reference']] = b['reference_sha256']
    records = copy.deepcopy(old['rows'])
    for r in records.values():
        for p in r['paths']:
            assert sha(p) == r['sha256']
            image_hashes[p] = r['sha256']
    formula_hash = sha(BASE/'analyze.py')
    cache = read(ROOT/'metric-cache.json') if (ROOT/'metric-cache.json').exists() else {'formula_sha256': formula_hash, 'rows': {}}
    assert cache['formula_sha256'] == formula_hash
    records.update(cache['rows'])
    new_calls = sorted((GEN/'generated').glob('*.call.json'))
    failures = [read(p) for p in sorted((GEN/'failures').glob('*.json'))]
    assert len(new_calls) <= 27
    if finalize:
        assert generation['collection_complete'] is True and generation['full_design_complete'] is False
        assert generation['new_calls'] == len(new_calls) == 25 and generation['new_failed_calls'] == len(failures) == 1
        assert set(generation['terminal_failures']) == {'P05-once-triggered'}
        assert {p.name.removesuffix('.call.json') for p in new_calls} == {p.stem for p in (GEN/'generated').glob('*.png')}
        sources[str(GEN/'progress.json')] = sha(GEN/'progress.json')
        for failure in failures:
            failure_path=GEN/'failures'/f'{failure["id"]}.json'
            sources[str(failure_path)]=sha(failure_path)
            assert failure['status']=='failed' and failure['attempt']==1 and failure['retried'] is False
            assert failure['branches']==['P05-once-triggered'] and failure['stage']==9
            assert failure['input_sha256']==sha(failure['input'])
            assert failure['id']==request_key(failure['input'],failure['prompt'])
            assert failure['prompt']==expected_edit_prompt[9] and failure['state']==expected_state[9]
            assert not Path(failure['output']).exists()
            image_hashes[failure['input']]=sha(failure['input'])

    def validate_call(path, expected_input=None, stage=None, kind=None):
        path = Path(path)
        sidecar = path.with_suffix('.call.json')
        r = read(sidecar)
        assert r['output'] == str(path), sidecar
        assert 'pocket' not in r['prompt'].lower(), sidecar
        assert r.get('attempt', 1) == 1
        if expected_input is not None:
            assert sha(r['input']) == sha(expected_input), (sidecar, expected_input)
        n = stage if stage is not None else r['stage']
        assert r['stage'] == n and r['state'] == expected_state[n]
        if kind is not None:
            assert r['prompt'] == (expected_edit_prompt[n] if kind == 'edit' else expected_rebase_prompt[n]), sidecar
        digest_in, digest_out = sha(r['input']), sha(path)
        if 'input_sha256' in r:
            assert digest_in == r['input_sha256']
        if 'output_sha256' in r:
            assert digest_out == r['output_sha256']
        image_hashes[r['input']], image_hashes[str(path)] = digest_in, digest_out
        sources[str(sidecar)] = sha(sidecar)
        call_audit[str(sidecar)] = {'output': str(path), 'input': r['input'], 'input_sha256': digest_in,
                                    'output_sha256': digest_out, 'request_key': request_key(r['input'], r['prompt']),
                                    'stage': n, 'kind_checked': kind, 'attempt': r.get('attempt', 1)}
        return r, str(sidecar)

    network = None
    refs = {}
    newly_measured = []

    def ensure_metric(person, output, usage):
        nonlocal network
        b = configs[person]
        key = row_key(b['reference'], output)
        digest = sha(output)
        image_hashes[str(output)] = digest
        if key not in records:
            if network is None:
                mm.torch.set_num_threads(2)
                mm.torch.manual_seed(0)
                mm.torch.use_deterministic_algorithms(True)
                network = mm.lpips.LPIPS(net='alex', version='0.1', verbose=False).cpu().eval()
                h = hashlib.sha256()
                for name, value in sorted(network.state_dict().items()):
                    h.update(name.encode()); h.update(str(tuple(value.shape)).encode()); h.update(value.cpu().numpy().tobytes())
                assert h.hexdigest() == old_manifest['lpips_state_dict_sha256']
                cache['lpips_state_dict_sha256'] = h.hexdigest()
            if b['reference_sha256'] not in refs:
                refs[b['reference_sha256']] = mm.image(b['reference'])
            measured = mm.measure(mm.image(output), refs[b['reference_sha256']], b['roi'], network, person.startswith('P04'))
            records[key] = {'sha256': digest, 'reference_sha256': b['reference_sha256'], 'reference': b['reference'],
                            'roi': b['roi'], 'paths': [str(output)], 'uses': [usage], **measured}
            cache['rows'][key] = records[key]
            newly_measured.append(key)
            save('metric-cache.json', cache)
            print(f'measured {person} {Path(output).name[:12]} fixed_lpips={measured["face"]["fixed"]["lpips"]:.6f}', flush=True)
        else:
            assert records[key]['roi'] == b['roi'] and records[key]['sha256'] == digest
        return key

    new_ids = []
    for call_path in new_calls:
        call = read(call_path)
        assert call['kind'] in ('edit', 'rebase') and call['attempt'] == 1
        assert call['id'] == call_path.name.removesuffix('.call.json') == request_key(call['input'], call['prompt'])
        validate_call(call['output'], stage=call['stage'], kind=call['kind'])
        people = {name.removesuffix('-once-triggered').removesuffix('-end-only').removesuffix('-always-original') for name in call['branches']}
        assert len({configs[p]['reference_sha256'] for p in people}) == 1
        person = sorted(people)[0]
        new_ids.append(ensure_metric(person, call['output'], {'branches': call['branches'], 'stage': call['stage'], 'source': 'new_first_output'}))
    auxiliary_ids = []
    for branch in generation['branches']:
        for r in branch['rows']:
            key = row_key(branch['reference'], r['output'])
            if key not in old['rows'] and key not in new_ids:
                auxiliary_ids.append(ensure_metric(branch['person'], r['output'], {'branch': branch['name'], 'stage': r['stage'], 'source': 'current_extension_reused_output'}))
    save('cache-status.json', {'provisional': not finalize, 'generation_calls_seen': len(new_calls),
                              'new_output_ids': new_ids, 'auxiliary_reused_ids': sorted(set(auxiliary_ids)),
                              'measured_this_run': len(newly_measured), 'cached_additional_images': len(cache['rows']),
                              'source_hashes_snapshot': sources, 'raw_image_hashes': image_hashes,
                              'generation_complete_snapshot': generation['complete']})
    if not finalize:
        print(json.dumps({'provisional': True, 'new_calls_seen': len(new_calls), 'cache_count': len(cache['rows'])})); return

    branch_rows = {}
    for b in inputs:
        selected = sorted([r for r in curves if r['branch'] == b['name']], key=lambda r:r['stage'])
        rebases = b.get('prefix_rebases', []) + [r['stage'] for r in current_branches[b['name']]['rows'] if r['rebased']]
        branch_rows[b['name']] = {'name': b['name'], 'person': b['name'] if b['policy']=='sequential' else 'P04',
             'policy': b['policy'], 'reference': b['reference'], 'roi': b['roi'], 'reset_stages': rebases,
             'rows': [{'stage': r['stage'], 'output': r['path'], 'metrics': r['metrics'], 'rebased': r['stage'] in rebases} for r in selected],
             'logical_calls': 10+len(rebases)}
    for b in generation['branches']:
        value = copy.deepcopy(b)
        if b['policy'] == 'end-only':
            value['rows'] = copy.deepcopy(branch_rows[b['person']]['rows'][:9])+value['rows']
        value['reset_stages'] = [r['stage'] for r in value['rows'] if r['rebased']]
        branch_rows[b['name']] = value
    assert len(branch_rows) == 20
    expected_cost = {'sequential':10, 'fixed3':13, 'triggered':18, 'once-triggered':11, 'always-original':10, 'end-only':11}
    summary, trajectories, recurrence, ledgers, extra_raw_hashes = {}, [], {}, {}, {}
    for name, b in branch_rows.items():
        complete_branch='stopped' not in b
        assert [r['stage'] for r in b['rows']] == list(range(1, 11 if complete_branch else 9))
        assert b.get('logical_calls',b.get('planned_logical_calls')) == expected_cost[b['policy']]
        if not complete_branch:
            assert name=='P05-once-triggered' and b['stopped']['stage']==9
        previous, ledger, scored = b['reference'], [], []
        for r in b['rows']:
            n, final = r['stage'], r['output']
            raw = final
            if r['rebased'] and b['policy'] != 'always-original':
                if b['policy'] == 'once-triggered':
                    raw = branch_rows[b['person']]['rows'][n-1]['output']
                elif b['policy'] == 'end-only':
                    raw = branch_rows[b['person']]['rows'][9]['output']
                elif n >= 9:
                    raw = next(x['raw'] for x in current_branches[name]['rows'] if x['stage'] == n)
                else:
                    decision_path = EXP/'policy-pilot-v1'/f'{b["policy"]}-stage-{n}-decision.json'
                    decision = read(decision_path)
                    sources[str(decision_path)] = sha(decision_path)
                    assert decision['stage'] == n and decision['policy'] == b['policy'] and decision['rebase']
                    assert sha(decision['input']) == sha(previous)
                    raw = decision['raw']['path']
                _, raw_call = validate_call(raw, expected_input=previous, stage=n, kind='edit')
                ledger.append({'stage':n, 'role':'raw_before_reset', 'call':raw_call})
                _, final_call = validate_call(final, expected_input=b['reference'], stage=n, kind='rebase')
            elif b['policy'] == 'always-original':
                _, final_call = validate_call(final, expected_input=b['reference'], stage=n, kind='rebase')
            else:
                _, final_call = validate_call(final, expected_input=previous, stage=n, kind='edit')
            ledger.append({'stage':n, 'role':'delivered', 'call':final_call})
            key = ensure_metric(b['person'], final, {'branch':name, 'stage':n, 'source':'delivered'})
            record = records[key]
            assert all(abs(record['face']['fixed'][k]-r['metrics'][k]) < 1e-6 for k in mm.FACE_KEYS), (name,n)
            if raw == final:
                raw_lpips = record['face']['fixed']['lpips']
            else:
                raw_key = row_key(b['reference'], raw)
                if raw_key in records:
                    raw_lpips = records[raw_key]['face']['fixed']['lpips']
                elif n >= 9:
                    raw_lpips = next(x['before']['lpips'] for x in current_branches[name]['rows'] if x['stage'] == n)
                else:
                    raw_lpips = decision['metrics']['lpips']
                extra_raw_hashes[raw] = sha(raw)
            scored.append({'stage':n, 'id':key, 'output':final, 'raw':raw, 'raw_fixed_lpips':raw_lpips,
                           'final_fixed_lpips':record['face']['fixed']['lpips'], 'rebased':r['rebased']})
            trajectories.append({'branch':name, **scored[-1]})
            previous = final
        failed_call_records=[]
        if complete_branch:
            assert len(ledger) == b['logical_calls'], name
        else:
            failure=failures[0]
            assert sha(failure['input'])==sha(previous)
            assert len(ledger)==b['observed_successful_calls']==9
            assert len(ledger)+1==b['observed_attempted_calls']==10
            failed_call_records=[{'stage':9,'role':'failed_edit','failure_record':str(GEN/'failures'/f'{failure["id"]}.json')}]
        ledgers[name] = {'logical_calls_verified':len(ledger) if complete_branch else None,
                         'observed_successful_calls':len(ledger),'observed_attempted_calls':len(ledger)+len(failed_call_records),
                         'planned_logical_calls':expected_cost[b['policy']],
                         'failed_call_records':failed_call_records, 'reset_stages':b['reset_stages'], 'calls':ledger,
                         'unique_call_records_within_branch':len({x['call'] for x in ledger})}
        keys = [r['id'] for r in scored]
        summary[name] = {'person':b['person'], 'policy':b['policy'], 'logical_calls':b.get('logical_calls'),
                         'planned_logical_calls':expected_cost[b['policy']], 'observed_successful_calls':len(ledger),
                         'observed_attempted_calls':len(ledger)+len(failed_call_records),
                         'deliverable_stages':len(keys),'full_ten_stage_complete':complete_branch,
                         'reset_stages':b['reset_stages'], 'final_id':keys[-1] if complete_branch else None,
                         'last_observed_id':keys[-1], 'last_observed_stage':len(keys), 'face':{},
                         'fixed_lpips_alarm_stages_observed':sum(records[k]['face']['fixed']['lpips']>=THRESHOLD for k in keys)}
        for scope, metric_keys in [('face',mm.FACE_KEYS), ('skin',mm.SKIN_KEYS)]:
            if scope not in records[keys[0]]: continue
            summary[name][scope] = {mode:{
                'mean':{metric:float(mm.np.mean([records[k][scope][mode][metric] for k in keys])) for metric in metric_keys} if complete_branch else None,
                'final':{metric:records[keys[-1]][scope][mode][metric] for metric in metric_keys} if complete_branch else None,
                'observed_mean':{metric:float(mm.np.mean([records[k][scope][mode][metric] for k in keys])) for metric in metric_keys},
                'last_observed':{metric:records[keys[-1]][scope][mode][metric] for metric in metric_keys},
                'observed_worst':{metric:float((min if metric=='ssim' else max)(records[k][scope][mode][metric] for k in keys)) for metric in metric_keys}}
                for mode in mm.MODES}
        if 'skin' in summary[name]:
            summary[name]['skin_regions']={region:{mode:{
                'mean':{metric:float(mm.np.mean([records[k]['skin'][mode]['regions'][region][metric] for k in keys])) for metric in mm.SKIN_KEYS},
                'final':{metric:records[keys[-1]]['skin'][mode]['regions'][region][metric] for metric in mm.SKIN_KEYS}}
                for mode in mm.MODES} for region in mm.REGIONS}
        if b['reset_stages'] and b['policy'] != 'always-original':
            recurrence[name] = first_recurrence(scored, b['reset_stages'][0])
    single_shot = {b['person']:{'final_id':summary[b['name']]['final_id'], 'logical_calls':1, 'observed_outputs':1,
                   'face':{mode: summary[b['name']]['face'][mode]['final'] for mode in mm.MODES}, 'mean_over_ten_stages':None,
                   'same_output_as_end_workflow':b['name']}
                   for b in generation['branches'] if b['policy']=='end-only'}
    assert single_shot['P03-r1']['final_id']==single_shot['P03-r2']['final_id']
    assert summary['P04-end-only']['final_id']==summary['P04-triggered']['final_id']==summary['P04-always-original']['final_id']
    assert len(trajectories)==198
    for path,digest in {**sources,**image_hashes,**extra_raw_hashes}.items(): assert sha(path)==digest, path
    manifest = {'finalized_at_utc':datetime.now(timezone.utc).isoformat(), 'collection_complete':True,
                'full_design_complete':False, 'new_calls':25,'new_failed_calls':1,'new_attempted_calls':26,
                'planned_new_calls':27,'not_attempted_dependency_stages':1,
                'source_hashes':sources, 'image_hashes':{**image_hashes,**extra_raw_hashes},
                'formula_reused_directly':str(BASE/'analyze.py'), 'formula_sha256':formula_hash,
                'lpips_state_dict_sha256':old_manifest['lpips_state_dict_sha256'], 'versions':old_manifest['versions'],
                'threshold_applied_only_to_fixed_lpips':THRESHOLD, 'base_images':len(old['rows']),
                'new_output_ids':new_ids, 'auxiliary_reused_ids':sorted(set(auxiliary_ids)),
                'human_evaluation':'not_read_or_collected', 'independent_agent_evaluation':'not_read_or_collected'}
    save('manifest.json',manifest)
    result = {'manifest_sha256':sha(ROOT/'manifest.json'), 'analysis_complete':True,
              'collection_complete':True,'full_design_complete':False, 'rows':records, 'trajectories':trajectories,
              'summary':summary, 'direct_one_shot':single_shot, 'first_reset_recurrence':recurrence, 'call_ledgers':ledgers,
              'call_audit':call_audit, 'unique_call_records_across_workflows':len(call_audit),
              'shared_final_outputs':{key:[name for name,v in summary.items() if v['final_id']==key] for key in {v['final_id'] for v in summary.values() if v['final_id'] is not None}},
              'new_output_registration':{'boundary_hits':{s:sum(records[k]['locations'][s]['boundary'] for k in new_ids) for s in ('1','3','6')},
                    'setting_sensitive_count':sum(records[k]['setting_sensitive'] for k in new_ids),
                    'max_shift_spread_px':max(records[k]['shift_spread_px'] for k in new_ids)},
              'diagnostic_only':True, 'human_evaluation':'not_read_or_collected', 'independent_agent_evaluation':'not_read_or_collected'}
    save('results.json',result)
    with (ROOT/'curves.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['branch','stage','id','mode','mae','ssim','lpips'])
        writer.writeheader()
        for r in trajectories:
            for mode in mm.MODES:
                writer.writerow({k:r[k] for k in ('branch','stage','id')}|{'mode':mode}|records[r['id']]['face'][mode])
    print(json.dumps({'analysis_complete':True,'new_calls':25,'new_failures':1,'unique_metric_rows':len(records),'branches':len(summary),'trajectories':len(trajectories),'recurrence':recurrence},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--finalize',action='store_true',help='Only after root confirms terminal collection and final generation snapshot.')
    main(parser.parse_args().finalize)
