"""V2.4 instruction routing, separate timing and actual persisted Choice pages."""
import csv
import html
import io
import json
import re
import time
import sqlite3

import pytest
import requests
from scripts.pilot_server import prepare_project
from test_dce_http import PilotServer, request, sql, to_instructions
from test_smoke import otree, project
from dce_modules import exports, facility_design
from timing import iter_page_durations

SCENARIO = [
    'Imagine choosing between two rental homes in Sweden. In each question, the homes are located at different distances from the same power plant. The type of power plant is shown for each home.',
    'The homes are otherwise identical, including their size, quality, lease terms, neighbourhood amenities, commuting time, public transport access and moving costs. The power plant is not visible from either home.',
]
BUDGET = 'Please consider your household budget. Higher rent leaves less money for other goods and services. All rents are stated in SEK per month for the entire home.'
REMINDER = 'Choose the apartment you prefer, considering the listed characteristics and your budget.'


def plain(markup):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', markup)).split())


def cards(markup):
    result = {}
    for side, content in re.findall(r'data-home="([AB])">(.*?)</section>', markup, re.S):
        attributes = re.findall(r'<dd data-attribute="([^"]+)"[^>]*>(.*?)</dd>', content, re.S)
        result[side] = {name: plain(value) for name, value in attributes}
    return result


@pytest.fixture(scope='module')
def framed_pilot(tmp_path_factory):
    project = prepare_project(tmp_path_factory.mktemp('v22a-framing') / 'survey')
    result = otree(project, 'create_session', 'nuclear_survey_pilot', '3')
    assert result.returncode == 0, result.stdout + result.stderr
    people = sql(project, 'SELECT id,code FROM otree_participant ORDER BY id_in_session')
    server = PilotServer(project)
    server.start()
    pages, instructions = [], []
    try:
        for person in people:
            url = to_instructions(server.base, person['code'])
            before = sql(project, 'SELECT * FROM random_matrix_player ORDER BY id')
            cursors = sql(project, 'SELECT * FROM random_matrix_subsession ORDER BY id')
            response = request(url)
            assert '/ScenarioInstructions/' in response.url
            assert request(response.url).text == response.text
            assert sql(project, 'SELECT * FROM random_matrix_player ORDER BY id') == before
            assert sql(project, 'SELECT * FROM random_matrix_subsession ORDER BY id') == cursors
            unassigned = [p for p in before if p['participant_id'] == person['id']]
            assert len(unassigned) == 4
            assert all(p['assignment_json'] is None and p['task_started_at'] is None for p in unassigned)
            if not instructions:
                time.sleep(2.1)  # A measurable synthetic reading interval, outside every task timer.
            submitted = time.time()
            instructions.append(dict(code=person['code'], markup=response.text, submitted=submitted))
            response = request(response.url, {})
            assert '/Choice/' in response.url and 'Choice 1 of 4' in response.text
            first = sql(project, f"SELECT task_started_at FROM random_matrix_player WHERE participant_id={person['id']} AND round_number=1")[0]
            assert first['task_started_at'] >= submitted
            for index in range(1, 5):
                before = sql(project, 'SELECT * FROM random_matrix_player ORDER BY id')
                refreshed = request(response.url)
                after = sql(project, 'SELECT * FROM random_matrix_player ORDER BY id')
                assert before == after  # No new task, changed timer, answer or assignment.
                assert response.text == refreshed.text
                pages.append(dict(code=person['code'], index=index, markup=response.text))
                response = request(response.url, {'choice': 'A' if index % 2 else 'B'})
            assert '/HouseholdInformation/' in response.url
        native = list(csv.DictReader(io.StringIO(request(server.base + '/ExportWide').text)))
        times = list(csv.DictReader(io.StringIO(request(server.base + '/ExportPageTimes').text)))
        assert len(sql(project, 'SELECT id FROM random_matrix_player')) == 12
        return pages, native, instructions, times
    finally:
        server.stop()
        server.log.close()


def test_instructions_once_and_clean_four_choices(framed_pilot):
    pages, native, instructions, times = framed_pilot
    assert len(instructions) == 3 and len(pages) == 12
    for page in instructions:
        text = plain(page['markup'])
        assert 'Choosing a Rental Home' in text
        assert 'These are hypothetical housing scenarios rather than descriptions of actual available homes.' in text
        assert 'id="power-plant-context"' not in page['markup']
        assert 'Continue to Housing Choices' in text
        assert 'data-wording-version="V2.4"' in page['markup']
        scenario = re.search(r'<section[^>]+aria-labelledby="rental-scenario"[^>]*>(.*?)</section>', page['markup'], re.S)[1]
        assert plain(scenario) == ' '.join(SCENARIO)
        budget = re.search(r'<aside[^>]+id="budget-reminder"[^>]*>(.*?)</aside>', page['markup'], re.S)[1]
        assert plain(budget) == BUDGET
        assert not any(term in plain(scenario) for term in ('10 km', '50 km', 'Nuclear', 'Oil-fired', 'Home A', 'Home B'))
        events = [t for t in times if t['participant_code'] == page['code'] and t['app_name'] == 'random_matrix']
        assert [t['page_name'] for t in events] == ['ScenarioInstructions'] + ['Choice'] * 4
        assert [t['round_number'] for t in events] == ['1', '1', '2', '3', '4']
    for page in pages:
        text = plain(page['markup'])
        assert f"Choice {page['index']} of 4" in text
        assert 'Which home would you prefer to rent?' in text
        assert 'data-wording-version="V2.4"' in page['markup']
        for sentence in SCENARIO + [BUDGET]:
            assert sentence not in text
        assert REMINDER not in text
        assert 'Part C — Housing Choice Experiment' not in text
        assert 'id="budget-reminder"' not in page['markup']
        assert 'id="rental-scenario"' not in page['markup']
        assert 'id="repeated-task-reminder"' not in page['markup']
        assert 'Distance to Power Plant' in text
        assert 'checked' not in page['markup'].split('<fieldset')[1].split('</fieldset>')[0]
        for prohibited in ('differ in three characteristics', 'Imagine that you are looking',
                           'Please remember that paying higher rent', 'Please choose your preferred apartment',
                           'additional monthly rent', 'always cheaper', 'always safer', 'safer apartment', 'maximum wtp'):
            assert prohibited.lower() not in text.lower()
    assert all(row['random_matrix.1.player.tasks_answered'] == '4' for row in native)


def test_instruction_time_separate_from_choice_time(framed_pilot):
    _, native, instructions, times = framed_pilot
    durations = list(iter_page_durations(times))
    for instruction in instructions:
        events = [t for t in durations if t['participant_code'] == instruction['code'] and t['app_name'] == 'random_matrix']
        assert len(events) == 5
        assert events[0]['page_name'] == 'ScenarioInstructions'
        assert events[1]['seconds_on_page'] == int(events[1]['epoch_time_completed']) - int(events[0]['epoch_time_completed'])
        row = next(r for r in native if r['participant.code'] == instruction['code'])
        assert float(row['random_matrix.1.player.task_started_at']) >= instruction['submitted']
    first = next(t for t in durations if t['participant_code'] == instructions[0]['code'] and t['page_name'] == 'ScenarioInstructions')
    assert first['seconds_on_page'] >= 2


def test_wording_version_in_native_and_all_analysis_formats(framed_pilot):
    _, native, _, _ = framed_pilot
    for row in native:
        for index in range(1, 5):
            prefix = f'random_matrix.{index}.player.'
            assert row[prefix + 'wording_version'] == 'V2.4'
            assert row[prefix + 'design_version'] == 'V2.4'
            assert row[prefix + 'numeric_matrix_version'] == 'V2.4'
            assert row[prefix + 'numeric_matrix_hash'] == '77b7ca09b110d974140745fe583049c18ce1a56290e550969e0279c08e3bde39'
            assert row[prefix + 'design_hash'] == facility_design.DESIGN_HASH
    records = list(exports.records_from_native(native))
    for rows in [records, *exports.reshape(records)]:
        assert {r['wording_version'] for r in rows} == {'V2.4'}
        assert {r['design_version'] for r in rows} == {'V2.4'}


def test_all_displayed_profiles_match_native_and_derived_exports(framed_pilot):
    pages, native, _, _ = framed_pilot
    by_code = {row['participant.code']: row for row in native}
    for page in pages:
        row = by_code[page['code']]
        prefix = f"random_matrix.{page['index']}.player."
        context = row[prefix + 'facility_type']
        assert context == row[prefix + 'A_facility_type'] == row[prefix + 'B_facility_type']
        assert f'Power plant context: {facility_design.FACILITY_LABELS[context]}' in plain(page['markup'])
        rendered = cards(page['markup'])
        assert set(rendered) == {'A', 'B'}
        assert {rendered[s]['distance_km'] for s in rendered} == {'10 km', '50 km'}
        for side in ('A', 'B'):
            assert list(rendered[side]) == ['facility_type', 'distance_km', 'rent_sek_month']
            assert rendered[side] == dict(
                facility_type=facility_design.FACILITY_LABELS[context],
                distance_km=row[prefix + side + '_distance_km'] + ' km',
                rent_sek_month=f"{int(row[prefix + side + '_rent_sek_month']):,} SEK/month")
    wide, long, diff = exports.reshape(exports.records_from_native(native))
    assert (len(wide), len(long), len(diff)) == (3, 24, 12)
    assert len({row['choice_set_id'] for row in diff}) == 8
    for row in diff:
        alternatives = [a for a in long if a['participant_code'] == row['participant_code'] and a['task_index'] == row['task_index']]
        a, b = alternatives
        assert a['chosen'] + b['chosen'] == 1
        assert row['delta_rent_1000'] == (int(a['rent_sek_month']) - int(b['rent_sek_month'])) / 1000


@pytest.mark.parametrize('set_id,premium', [('S01', 1000), ('S02', 500), ('S03', 2000),
    ('S04', 2000), ('S05', 0), ('S06', 0), ('S07', 500), ('S08', 1000)])
def test_price_framing_edge_cases(framed_pilot, set_id, premium):
    pages, _, _, _ = framed_pilot
    page = next(p for p in pages if f'data-choice-set="{set_id}"' in p['markup'])
    homes = cards(page['markup'])
    near = next(a for a in homes.values() if a['distance_km'] == '10 km')
    far = next(a for a in homes.values() if a['distance_km'] == '50 km')
    assert near['rent_sek_month'] == '6,500 SEK/month'
    assert far['rent_sek_month'] == f'{6500 + premium:,} SEK/month'
    text = plain(page['markup']).lower()
    assert 'floor area' not in text and 'apartment' not in text
    assert 'safer' not in text and 'dangerous' not in text


def test_instruction_dropout_has_no_assignment_or_choice_time(project):
    result = otree(project, 'create_session', 'nuclear_survey_pilot', '1')
    assert result.returncode == 0, result.stdout + result.stderr
    code = sql(project, 'SELECT code FROM otree_participant')[0]['code']
    server = PilotServer(project)
    try:
        server.start()
        page = request(to_instructions(server.base, code))
        assert '/ScenarioInstructions/' in page.url
        rows = sql(project, 'SELECT * FROM random_matrix_player ORDER BY round_number')
        assert len(rows) == 4
        assert all(row['choice'] is None and row['task_started_at'] is None and not row['task_displayed'] for row in rows)
        assert rows[0]['assignment_json'] is None
        assert sql(project, 'SELECT allocation_cursor FROM random_matrix_subsession WHERE round_number=1')[0]['allocation_cursor'] == 0
        native = csv.DictReader(io.StringIO(request(server.base + '/ExportWide').text))
        wide, long, _ = exports.reshape(exports.records_from_native(native))
        assert wide[0]['tasks_answered'] == '0' and wide[0]['wording_version'] == 'V2.4'
        assert all(row['chosen'] == '' for row in long)
    finally:
        server.stop()
        server.log.close()


@pytest.mark.parametrize('invalid_context', ['unsupported_fixture', 'mixed_fixture'])
def test_context_label_refuses_unsupported_saved_design(project, invalid_context):
    result = otree(project, 'create_session', 'nuclear_survey_pilot', '1')
    assert result.returncode == 0, result.stdout + result.stderr
    code = sql(project, 'SELECT code FROM otree_participant')[0]['code']
    # Corrupt only this disposable plan to prove the label reads stored data, not a hardcoded default.
    with sqlite3.connect(project / 'db.sqlite3') as db:
        plan = json.loads(db.execute('SELECT allocation_plan_json FROM random_matrix_subsession WHERE round_number=1').fetchone()[0])
        for choice_set in plan['design']['choice_sets']:
            for side in ('A', 'B'):
                if invalid_context == 'unsupported_fixture' or side == 'A':
                    choice_set[side]['facility_type'] = 'unsupported_test_type'
        db.execute('UPDATE random_matrix_subsession SET allocation_plan_json=? WHERE round_number=1', (json.dumps(plan),))
    server = PilotServer(project)
    try:
        server.start()
        response = requests.get(to_instructions(server.base, code), timeout=10)
        assert response.status_code == 500 and 'treatment design hash mismatch' in response.text
        assert sql(project, 'SELECT allocation_cursor FROM random_matrix_subsession WHERE round_number=1')[0]['allocation_cursor'] == 0
    finally:
        server.stop()
        server.log.close()
