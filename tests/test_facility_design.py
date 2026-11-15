"""Actual treatment overlay, identified contrasts and backward-compatible missingness."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
import sqlite3

import numpy as np
import pytest
from legacy_dce_modules import matrix as m, facility_design as f, randomization as r, exports as e
from test_dce import synthetic_records
from test_smoke import ROOT
from scripts.pilot_server import check_database_schema
from scripts.check_facility_design import sample, design, fit_logit, context_ranks


def test_treatment_hash_and_numeric_source_separate():
    assert m.DESIGN_HASH == '96862c147a85b30d887c0a77432805011ae6e755e608a0c8e408a82571dd5053'
    assert f.DESIGN_VERSION == 'V2.3' and f.NUMERIC_MATRIX_VERSION == 'V2.0'
    assert f.DESIGN_HASH != m.DESIGN_HASH
    payload=f.design_payload()
    assert payload['choice_sets']==m.design_payload()['choice_sets']
    changed=json.loads(json.dumps(payload));changed['facility_rules']['tasks_per_facility']=3
    assert hashlib.sha256(m.canonical_json(changed).encode()).hexdigest()!=f.DESIGN_HASH


def test_facility_pairs_balance_sets_and_preserve_housing_rng():
    maps=defaultdict(set)
    for seed in range(60):
        blocks=r.allocation_sequence(50,str(seed));schedule=f.facility_schedule(blocks,str(seed))
        assert schedule==f.facility_schedule(blocks,str(seed))
        plan=dict(seed=str(seed),sequence=blocks,design=f.design_payload(),design_hash=f.DESIGN_HASH,facility_schedule=schedule)
        f.validate_plan(plan);counts=defaultdict(Counter)
        for index,block in enumerate(blocks,1):
            a=r.make_assignment(plan,block,f'p{index}',index,'synthetic','session')
            b=r.make_assignment(plan,block,f'p{index}',index,'synthetic','session')
            assert a==b
            f.validate_assignment(a)
            # Existing numeric order/side RNG draw sequence must remain exactly intact.
            import random
            rng=random.Random(f'p{index}')
            sets=[s['choice_set_id'] for s in m.design_payload()['choice_sets'] if s['block_id']==block]
            rng.shuffle(sets);sides=['A','A','B','B'];rng.shuffle(sides)
            assert a['choice_set_order']==sets and a['side_allocation']==sides
            maps[block].add(a['facility_type_assignment'])
            for task in a['tasks']:counts[task['choice_set_id']][task['facility_type']]+=1
            assert all(abs(c['nuclear']-c['coal'])<=1 for c in counts.values())
        assert all(set(c)=={'nuclear','coal'} for c in counts.values())
    assert all(len(values)==6 for values in maps.values())


def test_actual_difference_rank_and_synthetic_logit():
    rows=sample(532722);X=design(rows,True);groups=np.array([r['participant'] for r in rows])
    assert X.shape==(200,5) and np.linalg.matrix_rank(X)==5
    assert context_ranks(rows)=={'nuclear':4,'coal':4}
    assert np.linalg.matrix_rank(np.column_stack([X,np.zeros(200)]))==5
    coal=np.array([r['Coal'] for r in rows])
    assert np.linalg.matrix_rank(np.column_stack([X,coal*X[:,1],coal*X[:,2]]))==7
    rng=np.random.default_rng(532722);beta=np.array([.15,-.6,.6,-.8,-.4])
    eta=X@beta+rng.normal(0,.3,50)[groups]*X[:,3]
    y=rng.binomial(1,1/(1+np.exp(-eta)))
    result=fit_logit(X,y,groups)
    assert result['converged'] and all(np.isfinite(result['participant_cluster_se']))
    assert not fit_logit(X,(X[:,3]>0).astype(int),groups)['converged']


@pytest.mark.parametrize('bad', ['task_label','one_alternative','map','numeric_hash','seed','round_count'])
def test_exports_reject_treatment_corruption(bad):
    rows=list(synthetic_records())
    if bad=='task_label': rows[0]['facility_type']='coal' if rows[0]['facility_type']=='nuclear' else 'nuclear'
    elif bad=='one_alternative': rows[0]['A_facility_type']='coal' if rows[0]['A_facility_type']=='nuclear' else 'nuclear'
    elif bad=='map':
        for row in rows: row['facility_type_assignment']='{}'
    elif bad=='numeric_hash':
        for row in rows: row['numeric_matrix_hash']='invalid'
    elif bad=='seed':
        for row in rows: row['facility_assignment_seed']=''
    else:rows.pop()
    with pytest.raises(ValueError):e.reshape(rows)


def test_current_exports_facility_and_missing_outcomes():
    rows=list(synthetic_records(answered=2));wide,long,diff=e.reshape(rows)
    assert Counter(row['facility_type'] for row in diff)=={'nuclear':2,'coal':2}
    for i,task in enumerate(diff,1):
        assert wide[0][f'task{i}_facility_type']==task['facility_type']
        assert long[2*i-2]['facility_type']==long[2*i-1]['facility_type']==task['facility_type']
        assert task['coal']==int(task['facility_type']=='coal')
        assert task['delta_near20_coal']==task['delta_near20']*task['coal']
        if i>2:assert task['chose_A']==long[2*i-2]['chosen']==long[2*i-1]['chosen']==''


@pytest.mark.parametrize('release',['v2_browser_1794596024642772000','v2_1_1_browser_1794691582034023000','v2_2a_browser_1794693478137951000'])
def test_historical_exports_do_not_invent_treatment_metadata(release):
    source=ROOT/'data/synthetic'/release/'all_apps_wide.csv';before=source.read_bytes()
    with source.open() as file: records=list(e.records_from_native(csv.DictReader(file)))
    wide,long,diff=e.reshape(records)
    assert all(row[field]=='' for row in records for field in [*e.FACILITY_MODULE_FIELDS,'facility_type'])
    assert all(row['coal']==row['delta_near20_coal']=='' for row in diff)
    # Original alternative-level facility observations are still historical nuclear.
    assert all(row['facility_type'] in ('','nuclear') for row in long)
    assert source.read_bytes()==before


def test_helper_refuses_v22a_schema_without_writing(tmp_path):
    database=tmp_path/'db.sqlite3'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE random_matrix_player (id INTEGER PRIMARY KEY, wording_version TEXT, choice TEXT)')
        db.execute("INSERT INTO random_matrix_player VALUES (1,'V2.2a','B')")
    before=database.read_bytes()
    with pytest.raises(SystemExit,match='facility-treatment fields'):check_database_schema(tmp_path)
    assert database.read_bytes()==before
