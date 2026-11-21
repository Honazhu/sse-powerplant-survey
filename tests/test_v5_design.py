"""V5 randomized design checks; no database or respondent data."""
from collections import Counter
from itertools import combinations, product
from dce_modules import matrix, randomization, facility_design
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('v5_countries', Path(__file__).resolve().parents[1] / 'household' / 'countries.py')
country_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(country_module)
COUNTRIES = country_module.COUNTRIES


def test_frozen_matrix_and_stratified_randomization():
    matrix.validate_design()
    expected = set(product(combinations(('S01','S03','S05','S07'), 3),
                           combinations(('S02','S04','S06','S08'), 3)))
    actual = set()
    plan = dict(design=facility_design.design_payload(), design_hash=facility_design.DESIGN_HASH,
                seed='plan', sequence=randomization.allocation_sequence(1, 'plan'),
                assignment_method=randomization.ASSIGNMENT_METHOD)
    facility_design.validate_plan(plan)
    for n in range(1000):
        a = randomization.make_assignment(plan, 'stratified', str(n), 1, 'p', 's')
        assert a == randomization.make_assignment(plan, 'stratified', str(n), 1, 'p', 's')
        facility_design.validate_assignment(a)
        groups = {f: tuple(sorted(t['choice_set_id'] for t in a['tasks'] if t['facility_type'] == f))
                  for f in ('nuclear','oil_fired')}
        actual.add((groups['nuclear'], groups['oil_fired']))
        assert Counter(t['facility_type'] for t in a['tasks']) == {'nuclear':3,'oil_fired':3}
        assert all(t['A']['facility_type'] == t['B']['facility_type'] == t['facility_type'] for t in a['tasks'])
        assert len(set(a['choice_set_order'])) == 6
    assert actual == expected and len(actual) == 16


def test_country_codes_frozen_and_distinct():
    codes = dict(COUNTRIES)
    assert len(codes) == len(COUNTRIES) >= 240
    assert all(len(code) == 2 and code.isupper() for code in codes)
    assert {'SE', 'CN', 'HK', 'MO', 'TW'} <= codes.keys()
