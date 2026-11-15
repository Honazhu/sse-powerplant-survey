from collections import Counter
from fractions import Fraction
from itertools import combinations, product
import hashlib
import json

import pytest
from legacy_dce_modules import matrix as m, randomization as r, exports as e, facility_design as f

EXPECTED = (
    ('S01', 1, 40, 6000, 40, 6500), ('S02', 1, 70, 8500, 70, 9500),
    ('S03', 1, 40, 6000, 55, 7500), ('S04', 1, 55, 7000, 40, 6500),
    ('S05', 2, 55, 7000, 55, 8500), ('S06', 2, 70, 8000, 70, 10000),
    ('S07', 2, 40, 5000, 55, 7500), ('S08', 2, 55, 7000, 40, 7000),
    ('S09', 3, 40, 6000, 40, 6000), ('S10', 3, 70, 9000, 70, 9500),
    ('S11', 3, 55, 8500, 70, 9000), ('S12', 3, 70, 9500, 55, 8000),
)


def rank(rows):
    rows = [[Fraction(x) for x in row] for row in rows]
    pivot = 0
    for column in range(len(rows[0])):
        match = next((i for i in range(pivot, len(rows)) if rows[i][column]), None)
        if match is None:
            continue
        rows[pivot], rows[match] = rows[match], rows[pivot]
        divisor = rows[pivot][column]
        rows[pivot] = [x / divisor for x in rows[pivot]]
        for i in range(pivot + 1, len(rows)):
            factor = rows[i][column]
            rows[i] = [x - factor * y for x, y in zip(rows[i], rows[pivot])]
        pivot += 1
        if pivot == len(rows):
            break
    return pivot


def plan(block=3):
    sequence = [block]
    return dict(design=f.design_payload(), design_hash=f.DESIGN_HASH, seed='plan-test', sequence=sequence,
                facility_schedule=f.facility_schedule(sequence, 'plan-test'))


def test_exact_frozen_matrix_and_attributes():
    assert m.CHOICE_SETS == EXPECTED
    m.validate_design()
    for s in m.design_payload()['choice_sets']:
        assert (s['N']['distance_km'], s['F']['distance_km']) == (10, 30)
        for side in ('N', 'F'):
            p = s[side]
            assert p['near20'] == int(p['distance_km'] < 20)
            assert p['facility_type'] == 'nuclear'
    assert hashlib.sha256(m.canonical_json(m.design_payload()).encode()).hexdigest() == m.DESIGN_HASH
    assert m.DESIGN_HASH == '96862c147a85b30d887c0a77432805011ae6e755e608a0c8e408a82571dd5053'


def test_balanced_sequences_and_randomized_profiles():
    orders, blocks = set(), set()
    for seed in range(500):
        sequence = r.allocation_sequence(50, seed)
        assert sorted(Counter(sequence).values()) == [16, 17, 17]
        for n in range(1, 51):
            counts = [sequence[:n].count(b) for b in (1, 2, 3)]
            assert max(counts) - min(counts) <= 1
        for block in (1, 2, 3):
            a = r.make_assignment(plan(block), block, str(seed), 1, 'synthetic', 'pilot')
            assert a == r.make_assignment(plan(block), block, str(seed), 1, 'synthetic', 'pilot')
            assert len(a['tasks']) == len(set(a['choice_set_order'])) == 4
            assert Counter(a['side_allocation']) == {'A': 2, 'B': 2}
            assert set(a['choice_set_order']) == {s[0] for s in EXPECTED if s[1] == block}
            for task in a['tasks']:
                source = next(s for s in m.design_payload()['choice_sets'] if s['choice_set_id'] == task['choice_set_id'])
                assert task[task['near_side']] == dict(source['N'], facility_type=task['facility_type'])
                assert task['B' if task['near_side'] == 'A' else 'A'] == dict(source['F'], facility_type=task['facility_type'])
            orders.add(tuple(a['choice_set_order']))
            blocks.add(a['block_id'])
    assert len(orders) == 72 and blocks == {1, 2, 3}


def test_identification_all_216_balanced_side_patterns():
    differences = [[Fraction(nr - fr, 1000), ns - fs, 1] for _, _, ns, nr, fs, fr in EXPECTED]
    assert rank(differences) == 3
    balanced = list(combinations(range(4), 2))
    for patterns in product(balanced, repeat=3):
        actual = []
        for i, diff in enumerate(differences):
            sign = 1 if i % 4 in patterns[i // 4] else -1
            actual.append([1] + [sign * value for value in diff])
        assert rank(actual) == 4


def synthetic_records(answered=4):
    a = r.make_assignment(plan(), 3, 'synthetic-seed', 1, 'synthetic', 'pilot')
    module = dict(participant_code='synthetic', session_code='pilot', study_mode='pilot', data_class='synthetic',
                  survey_version='V2.2b', wording_version='V2.2b', task_count=4, tasks_answered=answered, module_started=True,
                  module_completed=answered == 4, choice_set_order_json=json.dumps(a['choice_set_order']),
                  side_allocation_json=json.dumps(a['side_allocation']), assignment_json=json.dumps(a))
    module.update({k: a[k] for k in e.MODULE_FIELDS if k in a})
    for i, task in enumerate(a['tasks'], 1):
        choice = ('A' if i % 2 else 'B') if i <= answered else ''
        yield dict(module, **{k: task[k] for k in ('task_index', 'choice_set_id', 'presentation_order', 'near_side', 'facility_type')},
                   **{f'{side}_{key}': value for side in ('A', 'B') for key, value in task[side].items()},
                   choice=choice, chosen_near20=task[choice]['near20'] if choice else None,
                   task_displayed=i <= min(answered + 1, 4), task_started_at=100 if i <= answered + 1 else None,
                   task_submitted_at=105 if choice else None, task_duration_s=5 if choice else None,
                   task_timing_status='ok' if choice else 'not_submitted')


@pytest.mark.parametrize('answered', [0, 2, 4])
def test_exports_missing_choices_and_difference_direction(answered, tmp_path):
    records = list(synthetic_records(answered))
    wide, long, diff = e.reshape(records)
    assert (len(wide), len(long), len(diff)) == (1, 8, 4)
    for i in range(4):
        a, b = long[i * 2:i * 2 + 2]
        if i < answered:
            assert a['chosen'] + b['chosen'] == 1
        else:
            assert a['chosen'] == b['chosen'] == diff[i]['chose_A'] == ''
        assert diff[i]['delta_rent_1000'] == (int(a['rent_sek_month']) - int(b['rent_sek_month'])) / 1000
        assert diff[i]['delta_size_m2'] == int(a['size_m2']) - int(b['size_m2'])
        assert diff[i]['delta_near20'] == int(a['near20']) - int(b['near20'])
    e.write_formats(records, tmp_path)
    with pytest.raises(FileExistsError):
        e.write_formats(records, tmp_path)


@pytest.mark.parametrize('corruption', ['duplicate', 'missing_task', 'profile', 'choice', 'chosen', 'completion'])
def test_exports_reject_corruption(corruption):
    records = list(synthetic_records())
    if corruption == 'duplicate': records.append(records[0])
    elif corruption == 'missing_task': records.pop()
    elif corruption == 'profile': records[0]['A_rent_sek_month'] += 500
    elif corruption == 'choice': records[0]['choice'] = 'N'
    elif corruption == 'chosen': records[0]['chosen_near20'] = 1 - records[0]['chosen_near20']
    else:
        for row in records: row['tasks_answered'] = 2
    with pytest.raises(ValueError):
        e.reshape(records)
