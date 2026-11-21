"""Final-release schema and experimental invariants, independent of old V3 exports."""
import ast
import csv
from pathlib import Path
import pytest
from attitudes.questions import QUESTIONS, FORM_FIELDS
from completion_final import FIELDS
from settings import APP_SEQUENCE, SESSION_CONFIGS

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('question', QUESTIONS, ids=[q['field'] for q in QUESTIONS])
def test_attitude_codings_and_explicit_missing(question):
    assert [code for code, _ in question['choices']] == [2,1,0,-1,-2,99]
    assert question['choices'][-1][1] == ("Don't know" if question['field'] in ('nuclear_economic','nuclear_climate') else 'Prefer not to say')
    assert question['choices'][2][0] == 0 and question['choices'][-1][0] != 0

def test_schema_dictionary_and_six_tasks():
    with (ROOT/'FINAL_DATA_DICTIONARY.csv').open(newline='',encoding='utf-8') as f:
        names = [r['variable_name'] for r in csv.DictReader(f)]
    assert names == FIELDS and len(names) == len(set(names))
    assert APP_SEQUENCE == ['eligibility','random_matrix','attitudes','household']
    assert all(config['app_sequence'] == APP_SEQUENCE for config in SESSION_CONFIGS)
    for i in range(1,7):
        for col in ('choice_set_id','facility_type','A_distance_km','A_rent_sek_month','B_distance_km','B_rent_sek_month','choice'):
            assert f'choice_{i}_{col}' in FIELDS
    for field in FORM_FIELDS:
        assert field in FIELDS and field+'_missing_reason' in FIELDS
    assert 'household_income_after_tax' in FIELDS and 'gender' in FIELDS and 'main_activity' in FIELDS

def test_v5_matrix_and_allocation_unchanged():
    v5 = ROOT.parent / 'survey-v5' / 'random_matrix'
    if not v5.exists(): pytest.skip('Separate V5 source is not present in this checkout')
    for name in ('matrix.py','facility_design.py'):
        assert (ROOT/'random_matrix'/name).read_bytes() == (v5/name).read_bytes()
    def function(path, name):
        node = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == name)
        # Ignore docstrings, which do not participate in allocation.
        if isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str): node.body.pop(0)
        if name == 'assign_once':
            # Session-mode guard changed for isolated Final; allocation is identical.
            guard = next(n for n in node.body if isinstance(n,ast.If) and any(isinstance(x,ast.Raise) and 'Allocation plan/session mismatch' in ast.dump(x) for x in n.body))
            guard.test = ast.Constant(value=True)
        return ast.dump(node, include_attributes=False)
    for name in ('allocation_sequence','make_assignment','stored_assignment','displayed_task','assign_once'):
        assert function(ROOT/'random_matrix/randomization.py',name)==function(v5/'randomization.py',name)
