"""Synthetic disk-backed HTTP and export test. Never uses a configured database."""
import csv
import io
import json
import re
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time

import requests
from scripts.pilot_server import prepare_project, clean_environment

ROOT = Path(__file__).resolve().parents[1]


def test_v5_synthetic_flow_and_export(tmp_path):
    project = prepare_project(tmp_path / 'project')
    env = clean_environment()
    cli = Path(sys.executable).with_name('otree')
    creation = subprocess.run([str(cli), 'create_session', 'nuclear_survey_pilot', '7'],
                              cwd=project, env=env, capture_output=True, text=True, timeout=30)
    assert creation.returncode == 0, creation.stderr
    with sqlite3.connect(project / 'db.sqlite3') as conn:
        codes = [r[0] for r in conn.execute('select code from otree_participant order by id_in_session')]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    with (tmp_path / 'server.log').open('w+') as log:
        process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/pilot_server.py'), '--project', str(project),
                                    '--port', str(port)], env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    log.seek(0); raise AssertionError(log.read())
                try:
                    if requests.get(base, timeout=1).status_code == 200: break
                except requests.ConnectionError: pass
                time.sleep(.05)
            else: raise AssertionError('server startup timeout')
            def get(url):
                r = requests.get(url, timeout=10); assert r.status_code == 200, r.text[:3000]; return r
            def post(page, data):
                r = requests.post(page.url, data=data, timeout=10); assert r.status_code == 200, r.text[:3000]; return r
            def start(index, age='True'):
                page = get(base + '/InitializeParticipant/' + codes[index])
                assert 'Welcome to our housing survey' in page.text
                return post(page, {'adult_confirmed': age})
            assert '/Exit/' in start(0, 'False').url
            page = start(1); assert codes[1] in page.text
            assert '/Exit/' in post(page, {'willing_to_participate': 'False'}).url
            shown = {}
            for index, consent, limit in [(2, 'False', 6), (3, 'True', 6), (4, 'False', 2), (5, 'False', 5), (6, None, 6)]:
                page = start(index)
                answers = {'willing_to_participate': 'True'}
                if consent is not None: answers['cookies_allowed'] = consent
                page = post(page, answers)
                assert '/ScenarioInstructions/' in page.url
                page = post(page, {})
                shown[index] = []
                for i in range(1, limit + 1):
                    assert f'Question {i} of 6' in page.text
                    assert get(page.url).text == page.text
                    match = re.search(r'data-choice-set="(S\d+)"', page.text)
                    cards = re.findall(r'<section class="survey-housing-card".*?</section>', page.text, re.S)
                    assert match and len(cards) == 2
                    displays = []
                    for card in cards:
                        facility = re.search(r'data-attribute="facility_type" data-value="([^"]+)"', card).group(1)
                        distance = int(re.search(r'data-attribute="distance_km">(\d+)', card).group(1))
                        rent = int(re.search(r'data-attribute="rent_sek_month">([\d,]+)', card).group(1).replace(',', ''))
                        displays.append((facility, distance, rent))
                    shown[index].append((match.group(1), displays))
                    page = post(page, {'choice': 'A' if i % 2 else 'B'})
                if limit != 6: continue
                assert '/HouseholdInformation/' in page.url
                household = {'age_group':'26_35', 'residence_code':'HK', 'rent_status':'False',
                             'income_category':'dont_know', 'children_under_18':'prefer_not',
                             'education_completed':'bachelor'}
                if index == 2:
                    household['rent_category'] = 'nothing'  # stale hidden response must be cleared
                if index == 3:
                    household.update(rent_status='True')
                    invalid = post(page, household)
                    assert '/HouseholdInformation/' in invalid.url and 'Please choose an amount.' in invalid.text
                    household['rent_category'] = 'nothing'
                page = post(page, household)
                assert '/AttitudeSurvey/' in page.url
                before = page.url
                page = post(page, {'nuclear_economic':'0', 'housing_cost':'1', 'nuclear_support':'-1',
                                   'nuclear_climate':'2', 'nuclear_risk':'0'})
                assert '/Completion/' in page.url and codes[index] in page.text
                assert '/Completion/' in get(page.url).url
                # A replay must not create an additional research record.
                requests.post(before, data={'nuclear_economic':'2', 'housing_cost':'2', 'nuclear_support':'2',
                                           'nuclear_climate':'-2', 'nuclear_risk':'2'}, timeout=10)
            rows = list(csv.DictReader(io.StringIO(get(base + '/api/export_app_custom?app=attitudes').text)))
            assert len(rows) == 3 and {r['survey_reference_id'] for r in rows} == {codes[2], codes[3], codes[6]}
            no, yes = (next(r for r in rows if r['survey_reference_id'] == codes[i]) for i in (2,3))
            assert yes['rent_category'] == 'nothing'
            assert no['rent_category'] == '' and no['income_category'] == 'dont_know'
            assert no['children_under_18'] == 'prefer_not' and no['residence_code'] == 'HK'
            assert all(no[f'choice_{i}_task_duration_s'] == '' for i in range(1,7))
            assert all(yes[f'choice_{i}_task_duration_s'] != '' for i in range(1,7))
            for row in rows:
                assert row['survey_version'] == '5.0.0'
                assert [row[k] for k in ('nuclear_economic','housing_cost','nuclear_support','nuclear_climate','nuclear_risk')] == ['0','1','-1','2','0']
                assert len({row[f'choice_{i}_choice_set_id'] for i in range(1,7)}) == 6
                index = codes.index(row['survey_reference_id'])
                assignment = json.loads(row['assignment_json'])
                for i, (sid, displays) in enumerate(shown[index], 1):
                    assert row[f'choice_{i}_choice_set_id'] == sid == assignment['tasks'][i-1]['choice_set_id']
                    for side, display in zip('AB', displays):
                        assert display == (row[f'choice_{i}_facility_type'], int(row[f'choice_{i}_{side}_distance_km']),
                                           int(row[f'choice_{i}_{side}_rent_sek_month']))
                    assert row[f'choice_{i}_choice'] == ('A' if i % 2 else 'B')
            times = list(csv.DictReader(io.StringIO(get(base + '/ExportPageTimes').text)))
            for i in (0,1,2,4,5,6):
                assert all(r['page_name'] == 'InitializeParticipant' for r in times if r['participant_code'] == codes[i])
            assert any(r['page_name'] == 'Choice' for r in times if r['participant_code'] == codes[3])
            opt_in = list(csv.DictReader(io.StringIO(get(base + '/api/export_app_custom?app=attitudes&function_name=custom_export_timing').text)))
            assert opt_in and {r['participant_code'] for r in opt_in} == {codes[3]}
            process.terminate(); process.wait(timeout=10)
            process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/pilot_server.py'), '--project', str(project),
                                        '--port', str(port)], env=env, stdout=log, stderr=log)
            for _ in range(100):
                if process.poll() is not None: raise AssertionError('restart failed')
                try:
                    if requests.get(base, timeout=1).status_code == 200: break
                except requests.ConnectionError: pass
                time.sleep(.05)
            else: raise AssertionError('restart timeout')
            after_restart = list(csv.DictReader(io.StringIO(get(base + '/api/export_app_custom?app=attitudes').text)))
            assert after_restart == rows
        finally:
            process.terminate(); process.wait(timeout=10)
