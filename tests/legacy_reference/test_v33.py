"""V3.3 release contracts, native routing, partial responses and historical DK."""
import csv
import importlib
import io
import json
import sqlite3

import pytest

from scripts.export_dce import attitude_exports as a, attitudes_package
from scripts.pilot_server import check_database_schema
from analysis.merge_attitudes import merge_datasets, read_csv, HOUSEHOLD_FIELDS
from test_attitudes import frames, responses
from test_smoke import ROOT, project, otree
from test_dce_http import PilotServer, request, sql, to_matrix, submit_household

q = importlib.import_module(attitudes_package.__name__ + '.questions')
MAPPING = [
    ('Q1', 'nuclear_economic', "Nuclear power has a positive effect on Sweden's economy."),
    ('Q2', 'housing_cost', 'Keeping my monthly housing costs low is a high priority when deciding where to live.'),
    ('Q3', 'nuclear_support', 'I support the use of nuclear power to generate electricity in Sweden.'),
    ('Q4', 'nuclear_climate', 'Nuclear power helps reduce greenhouse gas emissions.'),
    ('Q5', 'nuclear_risk', 'I would be concerned about safety risks if I lived near an operating nuclear power plant.'),
]


@pytest.mark.parametrize('index', range(5))
@pytest.mark.parametrize('value', [-2, -1, 0, 1, 2])
def test_question_variable_raw_score_mapping(index, value):
    item = q.QUESTIONS[index]
    number, field, wording = MAPPING[index]
    assert (item['number'], item['field'], item['wording']) == (number, field, wording)
    assert item['choices'] == list(zip((-2,-1,0,1,2), ('Strongly disagree','Slightly disagree','Neutral','Slightly agree','Strongly agree')))
    row = a.scored_record(dict(session_code='s', participant_code='p', attitudes_version='V3.3',
        attitudes_completed=1, attitudes_submitted_at=123, **dict.fromkeys(a.RAW_FIELDS, value)))
    assert row[field] == row[field + '_score'] == str(value)
    with pytest.raises(ValueError):
        a.scored_record(dict(row, **{field: 99}))


@pytest.mark.parametrize('release', ['v3_http_1794735342256838000', 'v3_browser_1794735361345897000',
                                    'v2_4_browser_1794762133050201000'])
def test_actual_v30_exports_are_lossless_and_never_relabelled(release):
    folder = ROOT/'data/synthetic'/release
    native = read_csv(folder/'all_apps_wide.csv').to_dict('records')
    previous = read_csv(folder/'attitudes_wide.csv').to_dict('records')
    assert a.records_from_native(native) == previous
    merged, audit = merge_datasets(*frames(native))
    assert merged.survey_flow_version.eq('').all()
    assert set(merged.attitudes_version) == {'V3.0'}
    assert len(merged) == len(native)*4
    dk_count = 0
    for field in ('nuclear_economic', 'nuclear_climate'):
        dk = merged[field].eq(99).fillna(False)
        dk_count += dk.sum()
        assert merged.loc[dk, field+'_score'].isna().all()
        assert merged.loc[dk, field+'_dk'].eq(1).all()
        if dk.any():
            corrupt = [dict(row) for row in previous]
            row = next(row for row in corrupt if row[field] == '99')
            row[field+'_score'] = '0'
            with pytest.raises(ValueError): a.validate_wide(corrupt)
    assert dk_count > 0


@pytest.mark.parametrize('answered', [1, 2, 3, 4])
def test_dropout_before_household_retains_all_dce_data(project, answered):
    assert otree(project, 'create_session', 'nuclear_survey_pilot', '1').returncode == 0
    person = sql(project, 'SELECT id,code FROM otree_participant')[0]
    server = PilotServer(project)
    try:
        server.start()
        page = request(to_matrix(server.base, person['code']))
        household = sql(project, 'SELECT * FROM household_player')[0]
        assert all(household[name] is None for name in HOUSEHOLD_FIELDS)
        assignment = sql(project, 'SELECT assignment_json FROM random_matrix_player WHERE round_number=1')[0]
        for _ in range(answered): page = request(page.url, {'choice':'B'})
        assert ('/HouseholdInformation/' if answered == 4 else '/Choice/') in page.url
        # Direct future URLs and old URLs cannot bypass the current required page.
        for path in ('household/HouseholdInformation/5', 'attitudes/AttitudeSurvey/14', 'attitudes/Completion/15'):
            forged = server.base + '/p/' + person['code'] + '/' + path
            assert request(forged).url == page.url
        native = list(csv.DictReader(io.StringIO(request(server.base+'/ExportWide').text)))
        merged, audit = merge_datasets(*frames(native))
        assert len(merged) == 4 and merged.chose_A.notna().sum() == answered
        assert merged.dce_completed.eq(int(answered == 4)).all()
        assert merged.household_completed.eq(0).all() and merged.attitudes_completed.eq(0).all()
        assert merged[HOUSEHOLD_FIELDS].replace('', None).isna().all().all()
        assert merged[a.SCORE_FIELDS].isna().all().all()
        assert merged.survey_flow_version.eq('V3.3').all()
        assert set(merged.facility_type) == {'nuclear','oil_fired'}
        assert merged.choice_set_id.nunique() == 4
        assert sql(project, 'SELECT assignment_json FROM random_matrix_player WHERE round_number=1')[0] == assignment
        assert not sql(project, 'SELECT * FROM attitudes_player')[0]['attitudes_completed']
        (project/'v33-dropout-audit.json').write_text(json.dumps(audit,indent=2))
    finally: server.stop();server.log.close()


def test_server_rejects_missing_duplicate_and_dk_payload_preserving_other_values(project):
    assert otree(project, 'create_session', 'nuclear_survey_pilot', '1').returncode == 0
    code = sql(project, 'SELECT code FROM otree_participant')[0]['code']
    server = PilotServer(project)
    try:
        server.start(); page = request(to_matrix(server.base, code))
        for _ in range(4): page = request(page.url, {'choice':'A'})
        # Household required validation is still authoritative after DCE.
        invalid = request(page.url, {})
        assert invalid.url == page.url and 'otree-form-errors' in invalid.text
        page = submit_household(page)
        values = dict(nuclear_economic=-2, housing_cost=-1, nuclear_support=0, nuclear_climate=1, nuclear_risk=2)
        before = sql(project, 'SELECT * FROM attitudes_player')
        for field in a.RAW_FIELDS:
            missing = dict(values);missing.pop(field)
            for payload in (missing, list(values.items()) + [(field, '2')], dict(values, **{field:99})):
                failed = request(page.url, payload)
                assert failed.url == page.url and 'otree-form-errors' in failed.text
                assert sql(project, 'SELECT * FROM attitudes_player') == before
                from html.parser import HTMLParser
                class Inputs(HTMLParser):
                    def __init__(self):super().__init__();self.checked={}
                    def handle_starttag(self, tag, attrs):
                        attr=dict(attrs)
                        if tag=='input' and 'checked' in attr:self.checked[attr['name']]=attr['value']
                parser=Inputs();parser.feed(failed.text)
                for other in set(values)-{field}:assert parser.checked[other] == str(values[other])
        done = request(page.url, values)
        assert '/Completion/' in done.url
        saved=sql(project, 'SELECT * FROM attitudes_player')[0]
        assert all(saved[field] == value for field,value in values.items())
    finally: server.stop();server.log.close()


def test_old_flow_database_is_refused_read_only(project):
    assert otree(project, 'create_session', 'nuclear_survey_pilot', '1').returncode == 0
    with sqlite3.connect(project/'db.sqlite3') as db:
        db.execute("UPDATE eligibility_player SET survey_flow_version='V3.0'")
    before=(project/'db.sqlite3').read_bytes()
    with pytest.raises(SystemExit, match='Historical survey flow'):check_database_schema(project)
    assert (project/'db.sqlite3').read_bytes() == before
