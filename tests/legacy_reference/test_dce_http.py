"""Real local HTTP, concurrent entry and hard-restart tests on disposable SQLite."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time

import requests
from dce_modules import exports, matrix, facility_design
from test_smoke import project, otree, ROOT
from test_dce import rank


def sql(project, query):
    with sqlite3.connect(f'file:{project / "db.sqlite3"}?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute(query)]


class PilotServer:
    def __init__(self, project):
        self.project = project
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.base = f'http://127.0.0.1:{self.port}'
        self.process = None
        self.log = (project / 'test-server.log').open('a')

    def start(self):
        (self.project / '.v2-synthetic-preview').write_text('test-only')
        self.process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/pilot_server.py'),
                                         '--project', str(self.project), '--port', str(self.port)],
                                        stdout=self.log, stderr=self.log)
        for _ in range(100):
            if self.process.poll() is not None:
                raise AssertionError((self.project / 'test-server.log').read_text())
            try:
                if requests.get(self.base, timeout=1).status_code == 200:
                    return
            except requests.ConnectionError:
                pass
            time.sleep(.05)
        raise AssertionError('Pilot server startup timeout')

    def stop(self, hard=False):
        if self.process and self.process.poll() is None:
            self.process.kill() if hard else self.process.terminate()
            self.process.wait(timeout=10)


def request(url, values=None, follow=True):
    response = requests.get(url, timeout=30) if values is None else requests.post(
        url, data=values, allow_redirects=follow, timeout=30)
    assert response.status_code in (200, 302, 303), response.text[:2000]
    return response


def to_instructions(base, code):
    page = request(f'{base}/InitializeParticipant/{code}')
    page = request(page.url, {'adult_confirmed': 'True'})
    page = request(page.url, {})
    page = request(page.url, dict(willing_to_participate='True', cookies_allowed='False', cookie_probe_status='declined'), follow=False)
    return requests.compat.urljoin(page.url, page.headers['location'])


def submit_household(page):
    assert '/HouseholdInformation/' in page.url
    return request(page.url, dict(age_group='26_35', rent_status='False', income_thousand_sek='0',
                                  income_not_disclosed='', previous_power_plant_exposure='2'))


def to_matrix(base, code):
    page = request(to_instructions(base, code))
    assert '/ScenarioInstructions/' in page.url
    page = request(page.url, {}, follow=False)
    return requests.compat.urljoin(page.url, page.headers['location'])


def test_concurrent_50_entry_restart_partial_and_exports(project):
    for count in (52, 1):
        result = otree(project, 'create_session', 'nuclear_survey_pilot', str(count))
        assert result.returncode == 0, result.stdout + result.stderr
    participants = sql(project, 'SELECT code,session_id FROM otree_participant ORDER BY session_id,id_in_session')
    server = PilotServer(project)
    server.start()
    try:
        # Exclusion consumes no allocation sequence position.
        underage = request(server.base + '/InitializeParticipant/' + participants[50]['code'])
        assert '/Exit/' in request(underage.url, dict(adult_confirmed='False')).url
        declined = request(server.base + '/InitializeParticipant/' + participants[51]['code'])
        declined = request(declined.url, dict(adult_confirmed='True'))
        declined = request(declined.url, {})
        assert '/Exit/' in request(declined.url, dict(willing_to_participate='False', cookie_probe_status='not_tested')).url
        with ThreadPoolExecutor(max_workers=10) as pool:
            urls = list(pool.map(lambda p: to_matrix(server.base, p['code']), participants[:50]))
        assert sql(project, 'SELECT allocation_cursor FROM random_matrix_subsession WHERE round_number=1')[0]['allocation_cursor'] == 0
        # Duplicate simultaneous first GETs to one slot plus 49 other entrants.
        with ThreadPoolExecutor(max_workers=12) as pool:
            pages = list(pool.map(request, urls + [urls[0]] * 4))
        rows = sql(project, 'SELECT * FROM random_matrix_player WHERE round_number=1 AND module_started=1')
        assert len(rows) == 50
        assert sorted(Counter(row['block_id'] for row in rows).values()) == [25, 25]
        assert sorted(row['allocation_index'] for row in rows) == list(range(1, 51))
        assert all(row['tasks_answered'] == 0 for row in rows)
        assert all(row['design_hash'] == facility_design.DESIGN_HASH for row in rows)
        for row in rows:
            a = json.loads(row['assignment_json'])
            assert len(set(a['choice_set_order'])) == 4
            assert Counter(a['side_allocation']) == {'A': 2, 'B': 2}
            assert Counter(t['facility_type'] for t in a['tasks']) == {'nuclear': 2, 'oil_fired': 2}
            facility_design.validate_assignment(a)
        realized = [task for row in rows for task in json.loads(row['assignment_json'])['tasks']]
        assert rank([[1, (t['A']['rent_sek_month'] - t['B']['rent_sek_month']) / 1000,
                      t['B']['near20'] - t['A']['near20'],
                      (t['B']['near20'] - t['A']['near20']) * (t['facility_type'] == 'oil_fired')]
                     for t in realized]) == 4
        assert Counter(t['choice_set_id'] for t in realized) == {f'S{i:02}': 25 for i in range(1, 9)}
        before = {row['id']: row['assignment_json'] for row in rows}
        # Exactly one response on duplicate POST, with stale URL redirected.
        page = request(urls[0], {'choice': 'A'})
        assert 'Choice 2 of 4' in page.text
        repeated = request(urls[0], {'choice': 'B'})
        assert repeated.url == page.url
        page = request(page.url, {'choice': 'B'})
        partial_url = page.url
        partial_code = participants[0]['code']
        assert 'Choice 3 of 4' in page.text
        # Full four-task participant reaches the required attitude form + Completion.
        page = pages[1]
        for choice in ('B', 'A', 'B', 'A'):
            page = request(page.url, {'choice': choice})
        page = submit_household(page)
        assert '/AttitudeSurvey/' in page.url
        page = request(page.url, dict(nuclear_support=0, nuclear_risk=0, nuclear_economic=0,
                                      nuclear_climate=0, housing_cost=0))
        assert '/Completion/' in page.url
        # Separate session starts its own cursor, seed and assignment plan.
        request(to_matrix(server.base, participants[52]['code']))
        cursors = sql(project, 'SELECT allocation_cursor,allocation_plan_json FROM random_matrix_subsession WHERE round_number=1 ORDER BY id')
        assert [r['allocation_cursor'] for r in cursors] == [50, 1]
        assert len({json.loads(r['allocation_plan_json'])['seed'] for r in cursors}) == 2
        # SIGKILL: disk commits must survive, without orderly shutdown save.
        server.stop(hard=True)
        server.start()
        resumed = request(server.base + '/InitializeParticipant/' + partial_code)
        assert resumed.url == partial_url
        assert 'Choice 3 of 4' in resumed.text
        assert request(urls[0]).url == partial_url  # back URL redirects to current page
        after = sql(project, 'SELECT id,assignment_json FROM random_matrix_player WHERE round_number=1 AND allocation_index IS NOT NULL')
        assert all(row['assignment_json'] == before[row['id']] for row in after if row['id'] in before)
        native = request(server.base + '/ExportWide').text
        records = list(exports.records_from_native(csv.DictReader(io.StringIO(native))))
        wide, long, diff = exports.reshape(records)
        partial = next(row for row in wide if row['participant_code'] == partial_code)
        assert partial['tasks_answered'] == '2' and partial['module_completed'] == '0'
        assert partial['task1_choice'] == 'A' and partial['task2_choice'] == 'B'
        assert partial['task3_choice'] == partial['task4_choice'] == ''
        assert partial['task3_task_displayed'] == '1' and partial['task4_task_displayed'] == '0'
        assert partial['task3_task_duration_s'] == partial['task4_task_duration_s'] == ''
        assert len(wide) == 53 and len(long) == 424 and len(diff) == 212
        for row in long:
            if not row['choice']:
                assert row['chosen'] == ''
        # Save evidence only under pytest's disposable project.
        (project / 'all_apps_wide.csv').write_text(native)
        exports.write_formats(records, project / 'dce_exports')
        assert len(sql(project, 'SELECT id FROM random_matrix_player')) == 53 * 4
    finally:
        server.stop()
        server.log.close()
