"""Small integration checks in a temporary project; never reset the local DB."""
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPS = ['eligibility', 'household', 'random_matrix', 'attitudes']


@pytest.fixture
def project(tmp_path):
    shutil.copy(ROOT / 'settings.py', tmp_path)
    shutil.copy(ROOT / 'timing.py', tmp_path)
    shutil.copytree(ROOT / '_static', tmp_path / '_static')
    shutil.copytree(ROOT / '_templates', tmp_path / '_templates')
    for app in APPS:
        shutil.copytree(ROOT / app, tmp_path / app, ignore=shutil.ignore_patterns('__pycache__'))
    return tmp_path


def otree(project, *args):
    env = os.environ.copy()
    # Isolate from a developer's database, authentication and production settings.
    for name in list(env):
        if name.startswith('OTREE_') or name in {'DATABASE_URL', 'REDIS_URL'}:
            env.pop(name)
    executable = Path(sys.executable).parent / 'otree'
    return subprocess.run(
        [str(executable), *args], cwd=project, env=env,
        text=True, capture_output=True, timeout=60,
    )


def test_pilot_bots_and_respondent_csv(project):
    result = otree(project, 'test', 'nuclear_survey_pilot', '1', '--export', 'synthetic')
    assert result.returncode == 0, result.stdout + result.stderr
    with (project / 'synthetic/all_apps_wide.csv').open(newline='') as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 8
    assert len({r['participant.code'] for r in rows}) == 8
    assert {r['eligibility.1.player.exit_reason'] for r in rows} == {'', 'under_18', 'declined'}
    for row in rows:
        for index in range(1, 5):
            assert row[f'random_matrix.{index}.player.wording_version'] == 'V2.4'
        assert row['session.config.data_class'] == 'synthetic'
        assert row['session.config.study_mode'] == 'pilot'
        eligible = row['participant.eligible'] == '1'
        assert row['participant.finished'] == ('1' if eligible else '0')
        assert row['household.1.player.placeholder_completed'] == ('1' if eligible else '0')
        prefix = 'random_matrix.1.player.'
        assert row[prefix + 'module_started'] == ('1' if eligible else '0')
        assert row[prefix + 'module_completed'] == ('1' if eligible else '0')
        assert row[prefix + 'tasks_answered'] == ('4' if eligible else '0')
        assert row[prefix + 'scenario_snapshot_json'] == row['participant.demo_assignment'] == ''
        if eligible:
            snapshot = json.loads(row[prefix + 'assignment_json'])
            assert snapshot['participant_code'] == row['participant.code']
            assert snapshot['side_allocation'].count('A') == snapshot['side_allocation'].count('B') == 2
            assert len(set(snapshot['choice_set_order'])) == 4
            for index, task in enumerate(snapshot['tasks'], 1):
                task_prefix = f'random_matrix.{index}.player.'
                assert row[task_prefix + 'choice_set_id'] == task['choice_set_id']
                choice = 'A' if index % 2 else 'B'
                assert row[task_prefix + 'choice'] == choice
                assert int(row[task_prefix + 'chosen_near20']) == task[choice]['near20']
                for side in ('A', 'B'):
                    for name, value in task[side].items():
                        assert row[task_prefix + side + '_' + name] == str(value)
        else:
            assert row[prefix + 'assignment_json'] == ''
            for index in range(1, 5):
                assert row[f'random_matrix.{index}.player.choice'] == ''
        assert row['household.1.player.country_of_residence'] == ''
        assert row['attitudes.1.player.nuclear_energy_support'] == ''
    household = 'household.1.player.'
    answered = [r for r in rows if r['participant.eligible'] == '1']
    assert {r[household + 'age_group'] for r in answered} == {'18_25', '26_35', '36_45', '46_55', '56_65', '66_plus'}
    assert {r[household + 'previous_power_plant_exposure'] for r in answered} == {'0', '1', '2'}
    assert any(r[household + 'income_sek'] == '25000' for r in answered)
    assert any(r[household + 'income_sek'] == '0' for r in answered)
    for row in rows:
        if row['participant.eligible'] == '0':
            assert all(row[household + f] == '' for f in ['age_group', 'rent_status', 'monthly_rent_sek', 'income_thousand_sek', 'income_sek', 'income_not_disclosed', 'previous_power_plant_exposure'])
            continue
        if row[household + 'rent_status'] == '0':
            assert row[household + 'monthly_rent_sek'] == ''
        if row[household + 'income_not_disclosed'] == '1':
            assert row[household + 'income_thousand_sek'] == row[household + 'income_sek'] == ''
        else:
            assert int(row[household + 'income_sek']) == int(row[household + 'income_thousand_sek']) * 1000
    assert {r['eligibility.1.player.cookie_probe_status'] for r in rows} == {
        'not_tested', 'supported', 'blocked', 'declined'
    }
    with (project / 'synthetic/attitudes_custom.csv').open(newline='') as file:
        timing_rows = list(csv.DictReader(file))
    with (project / 'synthetic/random_matrix_custom.csv').open(newline='') as file:
        custom_tasks = list(csv.DictReader(file))
    assert len(custom_tasks) == 32
    from dce_modules import exports
    normalized_tasks = [exports.normalized(row) for row in exports.records_from_native(rows)]
    task_key = lambda row: (row['session_code'], row['participant_code'], row['task_index'])
    assert sorted(custom_tasks, key=task_key) == sorted(normalized_tasks, key=task_key)
    wide, long, difference = exports.reshape(custom_tasks)
    assert (len(wide), len(long), len(difference)) == (8, 64, 32)
    assert {row['wording_version'] for row in custom_tasks} == {'V2.4'}
    assert timing_rows
    by_code = {r['participant.code']: r for r in rows}
    for event in timing_rows:
        assert event['timing_status'] == 'ok'
        assert int(event['seconds_on_page']) >= 0
        respondent = by_code[event['participant_code']]
        if respondent['participant.eligible'] == '0':
            assert event['app_name'] == 'eligibility'
    completed = [r for r in rows if r['participant.finished'] == '1']
    assert len(completed) == 6
    for row in completed:
        pages = {t['page_name'] for t in timing_rows if t['participant_code'] == row['participant.code']}
        assert 'AgeConfirmation' in pages
        assert 'VoluntaryParticipation' in pages
        assert 'CookiePreferences' not in pages
        assert 'Choice' in pages
        instructions = [t for t in timing_rows if t['participant_code'] == row['participant.code'] and t['page_name'] == 'ScenarioInstructions']
        assert len(instructions) == 1 and instructions[0]['round_number'] == '1'
        assert len([t for t in timing_rows if t['participant_code'] == row['participant.code'] and t['page_name'] == 'Choice']) == 4
        ordered = [t['page_name'] for t in timing_rows if t['participant_code'] == row['participant.code']]
        assert ordered == ['AgeConfirmation', 'Introduction', 'VoluntaryParticipation', 'ScenarioInstructions', *(['Choice'] * 4), 'HouseholdInformation', 'AttitudeSurvey']
        assert row['eligibility.1.player.survey_flow_version'] == row['session.config.survey_flow_version'] == 'V3.3'
        assert 'AttitudeSurvey' in pages
        assert 'Completion' not in pages  # terminal page has no submission event


def test_live_session_is_blocked(project):
    result = otree(project, 'create_session', 'nuclear_survey_live', '1')
    assert result.returncode != 0
    assert 'V0 blocks live sessions' in result.stdout + result.stderr
