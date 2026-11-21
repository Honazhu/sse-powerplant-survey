"""V2.4 frozen design, all allowed orientations, recorded choices and version dispatch."""
from collections import Counter, defaultdict
from copy import deepcopy
import csv
import hashlib
import itertools
import json
import numpy as np
import pytest
from dce_modules import matrix as m, facility_design as f, randomization as r, exports as e
from scripts.check_v24_design import plan, contrast, sample, design, wtp_status
from scripts.check_facility_design import fit_logit
from test_smoke import ROOT

EXPECTED = (
    ('S01', 'nuclear', 10, 6500, 50, 7500), ('S02', 'oil_fired', 50, 7000, 10, 6500),
    ('S03', 'nuclear', 50, 8500, 10, 6500), ('S04', 'oil_fired', 10, 6500, 50, 8500),
    ('S05', 'nuclear', 10, 6500, 50, 6500), ('S06', 'oil_fired', 50, 6500, 10, 6500),
    ('S07', 'nuclear', 50, 7000, 10, 6500), ('S08', 'oil_fired', 10, 6500, 50, 7500),
)


def test_frozen_matrix_hash_and_all_invariants():
    assert m.CHOICE_SETS == EXPECTED
    assert m.BLOCKS == {'A': ('S01','S04','S06','S07'), 'B': ('S02','S03','S05','S08')}
    assert m.DESIGN_VERSION == f.SURVEY_VERSION == f.WORDING_VERSION == 'V2.4'
    assert m.DESIGN_HASH == '77b7ca09b110d974140745fe583049c18ce1a56290e550969e0279c08e3bde39'
    assert hashlib.sha256(m.canonical_json(m.design_payload()).encode()).hexdigest() == m.DESIGN_HASH
    m.validate_design()
    assert 'size_m2' not in m.PROFILE_FIELDS
    assert {s['choice_set_id'] for s in m.design_payload()['choice_sets'] if s['premium_sek']==0} == {'S05','S06'}


def test_every_randomized_order_and_side_pattern_preserves_profiles_and_balance():
    orders, patterns = defaultdict(set), defaultdict(set)
    for seed in range(600):
        p=plan(str(seed));f.validate_plan(p)
        assert Counter(p['sequence']) == {'A':25,'B':25}
        for n in range(1,51):
            assert abs(p['sequence'][:n].count('A') - p['sequence'][:n].count('B')) <= 1
        for block in 'AB':
            index=p['sequence'].index(block)+1
            a=r.make_assignment(p,block,str(seed),index,'person','session')
            assert a==r.make_assignment(p,block,str(seed),index,'person','session')
            f.validate_assignment(a)
            orders[block].add(tuple(a['choice_set_order']))
            patterns[block].add(tuple((t['choice_set_id'],t['near_side']) for t in sorted(a['tasks'],key=lambda t:t['choice_set_id'])))
            assert Counter(t['near_side'] for t in a['tasks'])=={'A':2,'B':2}
            for facility in f.FACILITY_LABELS:
                assert Counter(t['near_side'] for t in a['tasks'] if t['facility_type']==facility)=={'A':1,'B':1}
    assert {len(v) for v in orders.values()}=={24}
    assert {len(v) for v in patterns.values()}=={4}


def test_all_block_side_patterns_identified_and_synthetic_stress():
    sets=m.design_payload()['choice_sets']
    assert np.linalg.matrix_rank([contrast(s) for s in sets])==4
    for block in 'AB':
        for flip_n,flip_o in itertools.product((False,True),repeat=2):
            tasks=[dict(s,A=s['B'],B=s['A']) if (flip_o if s['facility_type']=='oil_fired' else flip_n) else s for s in sets if s['block_id']==block]
            assert np.linalg.matrix_rank([contrast(s) for s in tasks])==4
    rows=sample(532724);X=design(rows);groups=np.array([row['participant'] for row in rows])
    assert X.shape==(200,4) and len(set(groups))==50
    eta=X@np.array([.15,-.8,1,-.3]);y=np.random.default_rng(532724).binomial(1,1/(1+np.exp(-eta)))
    fit=fit_logit(X,y,groups)
    assert fit['converged'] and np.isfinite(fit['participant_cluster_se']).all()
    separated=fit_logit(X,(X[:,2]>0).astype(int),groups)
    assert wtp_status(separated).startswith('unstable')
    for rent in (1,0,-1e-8):
        assert wtp_status(dict(converged=True,beta=[0,rent,1,0])).startswith('unstable')


def synthetic_records(answered=4, seed='sample', block='A'):
    from dce_modules import package
    import importlib
    v=importlib.import_module(package.__name__+'.exports_v24')
    p=plan('test');index=p['sequence'].index(block)+1
    a=r.make_assignment(p,block,seed,index,'person','session')
    module=dict(participant_code='person',session_code='session',study_mode='pilot',data_class='synthetic',
                survey_version='V2.4',wording_version='V2.4',task_count=4,tasks_answered=answered,
                module_started=True,module_completed=answered==4,assignment_json=json.dumps(a),
                choice_set_order_json=json.dumps(a['choice_set_order']),side_allocation_json=json.dumps(a['side_allocation']))
    module.update({k:a[k] for k in v.MODULE_FIELDS if k in a})
    for i,t in enumerate(a['tasks'],1):
        choice=('A' if i%2 else 'B') if i<=answered else ''
        chosen=t[choice] if choice else {}
        row=dict(module,**{k:t[k] for k in v.TASK_METADATA},
                 **{f'{s}_{k}':value for s in 'AB' for k,value in t[s].items()},choice=choice,
                 chosen_facility_type=chosen.get('facility_type'),chosen_distance_km=chosen.get('distance_km'),
                 chosen_rent_sek=chosen.get('rent_sek_month'),chosen_near20=chosen.get('near20'),
                 chosen_far=int(chosen['distance_km']==50) if choice else None,task_completed=bool(choice),
                 task_displayed=i<=answered+1,task_started_at=100 if i<=answered+1 else None,
                 task_submitted_at=105 if choice else None,task_duration_s=5 if choice else None,
                 task_timing_status='ok' if choice else 'not_submitted')
        yield v.with_aliases(row)


@pytest.mark.parametrize('answered',[0,1,2,4])
@pytest.mark.parametrize('block',['A','B'])
def test_native_aliases_chosen_profiles_and_all_formats(answered,block,tmp_path):
    rows=list(synthetic_records(answered,block=block));wide,long,diff=e.reshape(rows)
    assert (len(wide),len(long),len(diff))==(1,8,4)
    for i,(task,d) in enumerate(zip(rows,diff)):
        a,b=long[2*i:2*i+2]
        assert a['alternative_id']=='A' and b['alternative_id']=='B'
        assert d['delta_rent_1000']==(task['A_rent_sek_month']-task['B_rent_sek_month'])/1000
        assert d['delta_far']==int(task['A_distance_km']==50)-int(task['B_distance_km']==50)
        assert d['delta_far_x_oil']==d['delta_far']*int(task['facility_type']=='oil_fired')
        assert 'delta_size_m2' not in d and 'coal' not in d and 'size_m2' not in a
        assert task['set_id']==task['choice_set_id'] and task['choice']==task['choice_ab']
        if i<answered:
            assert a['chosen']+b['chosen']==1
            assert task['chosen_rent_sek']==task['home_'+task['choice']+'_rent_sek']
            assert task['chosen_distance_km']==task['home_'+task['choice']+'_distance_km']
        else:
            assert a['chosen']==b['chosen']==d['chose_A']==''
    e.write_formats(rows,tmp_path)
    with pytest.raises(FileExistsError):e.write_formats(rows,tmp_path)


@pytest.mark.parametrize('bad',['profile','chosen_distance','chosen_rent','chosen_facility','chosen_far','swap','alias','missing','duplicate','duration','facility','size','hash','completion','block'])
def test_rejects_corrupted_v24_records(bad):
    rows=list(synthetic_records())
    if bad=='profile':rows[0]['A_distance_km']=50 if rows[0]['A_distance_km']==10 else 10
    elif bad.startswith('chosen_'):
        key={'chosen_distance':'chosen_distance_km','chosen_rent':'chosen_rent_sek','chosen_facility':'chosen_facility_type','chosen_far':'chosen_far'}[bad]
        rows[0][key]='corrupt'
    elif bad=='swap':rows[0]['side_swapped']=1-rows[0]['side_swapped']
    elif bad=='alias':rows[0]['choice_ab']='B'
    elif bad=='missing':rows.pop()
    elif bad=='duplicate':rows.append(rows[0])
    elif bad=='duration':rows[0]['task_duration_s']=999
    elif bad=='facility':rows[0]['facility_type']='coal'
    elif bad=='size':
        # The persisted V2.4 profile cannot acquire a legacy size attribute.
        for row in rows:
            a=json.loads(row['assignment_json']);a['tasks'][0]['A']['size_m2']=55;row['assignment_json']=json.dumps(a)
    elif bad=='hash':rows[0]['design_hash']='4c925a9034bcfebb4dd15e904d4f345b6c1422f169b96f4c50b249a3558bcb7e'
    elif bad=='completion':rows[0]['task_completed']=False
    else:rows[0]['block_id']='B'
    with pytest.raises(ValueError):e.reshape(rows)


def test_s01_both_orientations_and_both_answers():
    seen=set()
    for seed in range(20):
        rows=list(synthetic_records(seed=str(seed)))
        row=next(x for x in rows if x['set_id']=='S01')
        for choice in 'AB':
            copied=deepcopy(rows);t=next(x for x in copied if x['set_id']=='S01')
            t.update(choice=choice,choice_ab=choice,chosen_facility_type='nuclear',
                     chosen_distance_km=t[f'{choice}_distance_km'],chosen_rent_sek=t[f'{choice}_rent_sek_month'],
                     chosen_near20=t[f'{choice}_near20'],chosen_far=int(t[f'{choice}_distance_km']==50))
            e.reshape(copied)
            seen.add((t['side_swapped'],choice))
            if t['side_swapped']==0 and choice=='B':
                assert (t['chosen_distance_km'],t['chosen_rent_sek'],t['chosen_far'])==(50,7500,1)
    assert seen=={(0,'A'),(0,'B'),(1,'A'),(1,'B')}


def test_historical_v23_dispatch_and_mixed_version_refusal():
    path=ROOT/'data/synthetic/v2_2b_browser_1794733130242432000/all_apps_wide.csv'
    before=path.read_bytes()
    with path.open() as file:old=list(e.records_from_native(csv.DictReader(file)))
    _,long,diff=e.reshape(old)
    assert {x['facility_type'] for x in long}=={'','nuclear','coal'}
    assert 'delta_size_m2' in diff[0] and 'delta_far' not in diff[0]
    assert all('chosen_distance_km' not in row for row in old)
    with pytest.raises(ValueError,match='mixed housing versions'):
        e.reshape(old+list(synthetic_records()))
    assert before==path.read_bytes()
