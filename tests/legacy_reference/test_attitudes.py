"""V3 raw choices, missingness, page persistence and CSV relationship checks."""
import csv
import io
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import requests

from scripts.export_dce import attitude_exports as a, exports as d
from analysis.merge_attitudes import merge_datasets, read_csv
from scripts.pilot_server import prepare_project, check_database_schema
from test_smoke import ROOT, project, otree
from test_dce_http import PilotServer, request, sql, to_matrix, submit_household


def responses(score=0, dk=False):
    result = dict.fromkeys(a.RAW_FIELDS, score)
    if dk:
        result.update(nuclear_economic=99, nuclear_climate=99)
    return result


@pytest.fixture(scope='module')
def attitude_pilot(tmp_path_factory):
    project = prepare_project(tmp_path_factory.mktemp('v3-attitudes') / 'survey')
    result = otree(project, 'create_session', 'nuclear_survey_pilot', '12')
    assert result.returncode == 0, result.stdout + result.stderr
    people = sql(project, 'SELECT id,code FROM otree_participant ORDER BY id_in_session')
    server = PilotServer(project)
    server.start()
    pages, completed = [], {}
    try:
        for index, person in enumerate(people[:9]):
            page = request(to_matrix(server.base, person['code']))
            for task in range(2 if index == 8 else 4):
                page = request(page.url, {'choice': 'A' if task % 2 == 0 else 'B'})
            if index == 8:
                assert 'Choice 3 of 4' in page.text
                continue
            assert '/HouseholdInformation/' in page.url
            if index == 7:  # DCE complete, Household never submitted.
                continue
            page = submit_household(page)
            assert '/AttitudeSurvey/' in page.url
            pages.append(page.text)
            before = sql(project, 'SELECT * FROM random_matrix_player ORDER BY id')
            attitude_before = sql(project, f"SELECT * FROM attitudes_player WHERE participant_id={person['id']}")
            assert all(attitude_before[0][f] is None for f in a.RAW_FIELDS)
            assert not attitude_before[0]['attitudes_completed']
            assert request(page.url).text == page.text
            assert sql(project, f"SELECT * FROM attitudes_player WHERE participant_id={person['id']}") == attitude_before
            if index == 7:  # DCE complete; attitude form displayed but never submitted.
                continue
            score = [-2, -1, 0, 1, 2, 0, 0][index]
            values = responses(score)
            if index == 5:
                values = dict(nuclear_economic=-2, housing_cost=-1, nuclear_support=0, nuclear_climate=1, nuclear_risk=2)
            if index == 6:
                for field, bad in [(f, '') for f in a.RAW_FIELDS] + [
                        (f, v) for f in a.RAW_FIELDS for v in ('99', '-3', '3', '2.0', '0.5', 'no', '+1', ' 0')]:
                    failed = request(page.url, dict(values, **{field: bad}))
                    assert failed.url == page.url and 'otree-form-errors' in failed.text
                    assert sql(project, f"SELECT * FROM attitudes_player WHERE participant_id={person['id']}") == attitude_before
                    assert sql(project, 'SELECT * FROM random_matrix_player ORDER BY id') == before
            old_url = page.url
            page = request(page.url, values)
            assert '/Completion/' in page.url
            saved = sql(project, f"SELECT * FROM attitudes_player WHERE participant_id={person['id']}")
            assert request(old_url, responses(2)).url == page.url  # stale POST cannot overwrite
            assert request(old_url).url == page.url
            assert sql(project, f"SELECT * FROM attitudes_player WHERE participant_id={person['id']}") == saved
            assert sql(project, 'SELECT * FROM random_matrix_player ORDER BY id') == before
            completed[person['code']] = values
        underage = request(server.base + '/InitializeParticipant/' + people[9]['code'])
        assert '/Exit/' in request(underage.url, {'adult_confirmed': 'False'}).url
        declined = request(server.base + '/InitializeParticipant/' + people[10]['code'])
        declined = request(declined.url, {'adult_confirmed': 'True'})
        declined = request(declined.url, {})
        assert '/Exit/' in request(declined.url, {'willing_to_participate': 'False', 'cookie_probe_status': 'not_tested'}).url
        # Slot 12 remains completely unstarted; saved attitudes must also be missing.
        server.stop(hard=True)
        server.start()
        assert '/Completion/' in request(server.base + '/InitializeParticipant/' + people[0]['code']).url
        native = request(server.base + '/ExportWide').text
        rows = list(csv.DictReader(io.StringIO(native)))
        (project / 'all_apps_wide.csv').write_text(native)
        d.write_formats(d.records_from_native(rows), project / 'exports')
        d.write_csv(project / 'exports/attitudes_wide.csv', a.records_from_native(rows), a.EXPORT_FIELDS)
        return dict(project=project, rows=rows, pages=pages, completed=completed, people=people)
    finally:
        server.stop()
        server.log.close()


@pytest.mark.parametrize('score', [-2, -1, 0, 1, 2])
def test_every_score_saved_in_native_and_scored_export(attitude_pilot, score):
    data = attitude_pilot
    person = data['people'][score + 2]
    raw = next(r for r in data['rows'] if r['participant.code'] == person['code'])
    row = next(r for r in a.records_from_native(data['rows']) if r['participant_code'] == person['code'])
    assert row['attitudes_completed'] == '1' and row['attitudes_version'] == 'V3.3'
    for field in a.RAW_FIELDS:
        assert raw['attitudes.1.player.' + field] == row[field] == row[field + '_score'] == str(score)
    assert row['nuclear_economic_dk'] == row['nuclear_climate_dk'] == '0'
    assert raw['attitudes.1.player.nuclear_energy_support'] == ''  # old 1–10 field not repurposed


def test_dk_neutral_unsubmitted_and_excluded_distinct(attitude_pilot):
    rows = a.records_from_native(attitude_pilot['rows'])
    for field, value in dict(nuclear_economic=-2, housing_cost=-1, nuclear_support=0, nuclear_climate=1, nuclear_risk=2).items():
        assert rows[5][field] == rows[5][field + '_score'] == str(value)
    assert rows[2]['nuclear_economic_score'] == '0'
    for row in rows[7:]:
        assert row['attitudes_completed'] == '0' and row['attitudes_status'] == 'not_submitted'
        assert all(row[f] == '' for f in a.RAW_FIELDS + a.SCORE_FIELDS + a.DK_FIELDS)
    # Native form includes the exact labels, five independent fields and no selection.
    from scripts.export_dce import attitudes_package
    import importlib
    questions = importlib.import_module(attitudes_package.__name__ + '.questions')
    from test_framing import plain
    markup = attitude_pilot['pages'][0]
    assert questions.TITLE in plain(markup) and questions.INTRODUCTION in plain(markup)
    assert markup.count('<form') == 1
    for question in questions.QUESTIONS:
        assert question['wording'] in plain(markup)
        for _, label in question['choices']:
            assert label in plain(markup)
    form = markup.split('data-attitudes-version=')[1].split('</form>')[0]
    assert 'checked' not in form and 'value="0"' in form
    assert '99' not in plain(markup) and 'nuclear_support' not in plain(markup)


def frames(native_rows):
    _, _, diff = d.reshape(d.records_from_native(native_rows))
    return (pd.DataFrame(native_rows), pd.DataFrame([d.normalized(r) for r in diff]),
            pd.DataFrame(a.records_from_native(native_rows), columns=a.EXPORT_FIELDS))


def test_merge_preserves_tasks_and_missing_attitudes(attitude_pilot):
    native, diff, attitudes = frames(attitude_pilot['rows'])
    result, audit = merge_datasets(native, diff, attitudes)
    assert len(result) == len(diff) == 48
    assert not result.duplicated(['session_code', 'participant_code', 'task_index']).any()
    assert result['nuclear_support_score'].dtype == 'Int64'
    assert set(result['facility_type']) == {'nuclear', 'oil_fired', ''}
    assert audit['unmatched_attitude_participants'] == []
    for index in (7, 8, 9, 10, 11):
        code = attitude_pilot['people'][index]['code']
        subset = result[result.participant_code == code]
        assert len(subset) == 4 and subset['nuclear_support_score'].isna().all()
        assert (subset['attitudes_completed'] == 0).all()
        assert subset['chose_A'].notna().sum() == (4 if index == 7 else 2 if index == 8 else 0)
        assert subset['household_completed'].eq(0).all()
        assert subset[['age_group', 'monthly_rent_sek', 'income_sek']].replace('', pd.NA).isna().all().all()
        assert subset['dce_completed'].eq(1 if index == 7 else 0).all()
    # Missing attitude export row must retain all four base task rows.
    absent = attitudes.iloc[1:].copy()
    left, audit = merge_datasets(native, diff, absent)
    assert len(left) == 48 and len(audit['unmatched_attitude_participants']) == 1
    assert left.loc[left.attitudes_match == 'left_only', a.SCORE_FIELDS].isna().all().all()
    assert left.loc[left.attitudes_match == 'left_only', 'attitudes_status'].eq('missing_export_row').all()
    _, long, _ = d.reshape(d.records_from_native(attitude_pilot['rows']))
    assert len(long) == 96


@pytest.mark.parametrize('problem', ['duplicate_attitudes', 'duplicate_dce', 'duplicate_native',
    'empty_key', 'invalid_score', 'neutral_to_missing', 'dk_to_neutral', 'wrong_facility', 'wrong_version', 'wrong_session'])
def test_merge_rejects_ambiguous_or_corrupt_input(attitude_pilot, problem):
    native, diff, attitudes = frames(attitude_pilot['rows'])
    if problem == 'duplicate_attitudes': attitudes = pd.concat([attitudes, attitudes.iloc[:1]])
    elif problem == 'duplicate_dce': diff = pd.concat([diff, diff.iloc[:1]])
    elif problem == 'duplicate_native': native = pd.concat([native, native.iloc[:1]])
    elif problem == 'empty_key': attitudes.loc[0, 'participant_code'] = ''
    elif problem == 'invalid_score': attitudes.loc[0, 'nuclear_support_score'] = '99'
    elif problem == 'neutral_to_missing': attitudes.loc[2, 'nuclear_support_score'] = ''
    elif problem == 'dk_to_neutral': attitudes.loc[5, 'nuclear_economic_score'] = '0'
    elif problem == 'wrong_facility': diff.loc[0, 'facility_type'] = 'other'
    elif problem == 'wrong_version': attitudes.loc[0, 'attitudes_version'] = 'V2.2b'
    else: attitudes.loc[0, 'session_code'] = 'wrong-session'
    with pytest.raises(ValueError): merge_datasets(native, diff, attitudes)


def clone_identity(row, session, code):
    row = dict(row, **{'session.code': session, 'participant.code': code})
    key = 'random_matrix.1.player.assignment_json'
    assignment = json.loads(row[key])
    assignment.update(session_code=session, participant_code=code)
    row[key] = json.dumps(assignment)
    return row


def test_same_code_across_sessions_and_string_ids(attitude_pilot):
    first, second = attitude_pilot['rows'][:2]
    rows = [clone_identity(first, 'session-A', '000001'), clone_identity(second, 'session-B', '000001'),
            clone_identity(first, 'session-A', 'NA')]
    merged, _ = merge_datasets(*frames(rows))
    assert len(merged) == 12 and set(merged.participant_code) == {'000001', 'NA'}
    assert merged[merged.session_code == 'session-A'].nuclear_support_score.eq(-2).all()
    assert merged[merged.session_code == 'session-B'].nuclear_support_score.eq(-1).all()


@pytest.mark.parametrize('release', ['v2_browser_1794596024642772000', 'v2_2a_browser_1794693478137951000',
                                    'v2_2b_browser_1794733130242432000'])
def test_historical_preview_never_becomes_v3_or_neutral(release):
    path = ROOT / 'data/synthetic' / release / 'all_apps_wide.csv'
    before = path.read_bytes()
    merged, audit = merge_datasets(*frames(read_csv(path).to_dict('records')))
    assert merged['attitudes_version'].eq('').all()
    assert merged['attitudes_completed'].isna().all()
    assert merged[a.SCORE_FIELDS].isna().all().all()
    assert merged['attitudes_status'].eq('historical_unavailable').all()
    assert audit['output_rows'] == audit['input_rows']['dce_difference']
    assert path.read_bytes() == before


def test_csv_cli_integrated_export_merge_and_overwrite_refusal(attitude_pilot, tmp_path):
    source = attitude_pilot['project'] / 'all_apps_wide.csv'
    before = source.read_bytes()
    exported, merged = tmp_path / 'export', tmp_path / 'merged'
    export_cmd = [sys.executable, str(ROOT / 'scripts/export_dce.py'), '--input', str(source), '--output-dir', str(exported)]
    result = subprocess.run(export_cmd, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    cmd = [sys.executable, str(ROOT / 'analysis/merge_attitudes.py'), '--native', str(source),
           '--dce-difference', str(exported / 'dce_difference.csv'), '--attitudes', str(exported / 'attitudes_wide.csv'),
           '--output-dir', str(merged)]
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert len(read_csv(merged / 'analysis_merged.csv')) == 48
    assert json.loads((merged / 'merge_audit.json').read_text())['input_rows']['attitudes'] == 12
    files = {p: p.read_bytes() for folder in (exported, merged) for p in folder.iterdir()}
    assert subprocess.run(cmd, capture_output=True, timeout=30).returncode != 0
    assert subprocess.run(export_cmd, capture_output=True, timeout=30).returncode != 0
    assert all(p.read_bytes() == contents for p, contents in files.items())
    assert source.read_bytes() == before


def test_pilot_rejects_pre_v3_schema_read_only(tmp_path):
    db_path = tmp_path / 'db.sqlite3'
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE random_matrix_player (wording_version TEXT, numeric_matrix_version TEXT, numeric_matrix_hash TEXT, treatment_design_version TEXT, facility_assignment_seed TEXT, facility_type_assignment TEXT, facility_type TEXT, premium_sek INTEGER, base_rent_sek INTEGER, side_swapped INTEGER, chosen_facility_type TEXT, chosen_distance_km INTEGER, chosen_rent_sek INTEGER, chosen_far INTEGER, task_completed INTEGER)')
        db.execute('CREATE TABLE attitudes_player (completed INTEGER, nuclear_energy_support INTEGER)')
        db.execute('INSERT INTO attitudes_player VALUES (1,NULL)')
    before = db_path.read_bytes()
    with pytest.raises(SystemExit, match='predates V3.0 attitude fields'):check_database_schema(tmp_path)
    assert before == db_path.read_bytes()


def test_csv_reader_preserves_codes_and_rejects_duplicate_headers(tmp_path):
    path = tmp_path / 'keys.csv'
    path.write_text('session_code,participant_code\ns,000012\ns,NA\n')
    assert read_csv(path).participant_code.tolist() == ['000012', 'NA']
    path.write_text('session_code,participant_code,participant_code\ns,p,other\n')
    with pytest.raises(ValueError, match='duplicate column'):read_csv(path)


def test_current_native_version_missing_cannot_become_history(attitude_pilot):
    rows = [dict(row) for row in attitude_pilot['rows']]
    rows[-1]['attitudes.1.player.attitudes_version'] = ''
    with pytest.raises(ValueError, match='missing its attitude version'):a.records_from_native(rows)


def test_old_attitude_version_cannot_receive_new_answers(project):
    result = otree(project, 'create_session', 'nuclear_survey_pilot', '1')
    assert result.returncode == 0
    code = sql(project, 'SELECT code FROM otree_participant')[0]['code']
    server = PilotServer(project)
    try:
        server.start()
        page = request(to_matrix(server.base, code))
        for _ in range(4):page = request(page.url, {'choice': 'A'})
        page = submit_household(page)
        server.stop()
        with sqlite3.connect(project / 'db.sqlite3') as db:
            db.execute('UPDATE attitudes_player SET attitudes_version=NULL')
        before = sql(project, 'SELECT * FROM attitudes_player')
        server.start()
        for response in (requests.get(page.url, timeout=10), requests.post(page.url, data=responses(), timeout=10)):
            assert response.status_code == 500 and 'historical records are not relabelled' in response.text
        assert sql(project, 'SELECT * FROM attitudes_player') == before
    finally:
        server.stop()
        server.log.close()
