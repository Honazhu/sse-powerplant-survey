"""Version persistence and preservation; every database mutation is synthetic."""
import csv
import hashlib
import sqlite3

import pytest
import requests
from dce_modules import exports
from scripts.pilot_server import check_database_schema
from test_smoke import ROOT, project, otree
from test_dce_http import PilotServer, request, sql, to_matrix


@pytest.mark.parametrize('release', ['v2_browser_1794596024642772000', 'v2_1_browser_1794599108416794000'])
def test_historical_csv_missing_wording_stays_missing(release, tmp_path):
    source = ROOT / 'data/synthetic' / release / 'all_apps_wide.csv'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    with source.open(newline='') as file:
        original = list(csv.DictReader(file))
    assert all('random_matrix.1.player.wording_version' not in row for row in original)
    records = list(exports.records_from_native(original))
    exports.write_formats(records, tmp_path)
    for name in ('tasks', 'wide', 'long', 'difference'):
        with (tmp_path / f'dce_{name}.csv').open(newline='') as file:
            rows = list(csv.DictReader(file))
        assert rows and {row['wording_version'] for row in rows} == {''}
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


@pytest.mark.parametrize('wording', ['', 'V2.0', 'V2.1', 'V2.1.1', 'V2.2a'])
def test_export_preserves_explicit_historical_version(wording):
    source = ROOT / 'data/synthetic/v2_1_browser_1794599108416794000/all_apps_wide.csv'
    with source.open(newline='') as file:
        rows = list(csv.DictReader(file))
    # Add metadata only to in-memory test copies, never to original evidence.
    for row in rows:
        for index in range(1, 5):
            row[f'random_matrix.{index}.player.wording_version'] = wording
    for output in exports.reshape(exports.records_from_native(rows)):
        assert {row['wording_version'] for row in output} == {wording}
    rows[0]['random_matrix.2.player.wording_version'] = 'V2.2b'
    with pytest.raises(ValueError, match='Inconsistent wording version'):
        list(exports.records_from_native(rows))


@pytest.mark.parametrize('release,version', [('v2_1_1_browser_1794691582034023000','V2.1.1'), ('v2_2a_browser_1794693478137951000','V2.2a')])
def test_actual_versioned_exports_retain_their_version(tmp_path, release, version):
    source = ROOT / 'data/synthetic' / release / 'all_apps_wide.csv'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    with source.open(newline='') as file:
        original = list(csv.DictReader(file))
    records = list(exports.records_from_native(original))
    exports.write_formats(records, tmp_path)
    for name in ('tasks', 'wide', 'long', 'difference'):
        with (tmp_path / f'dce_{name}.csv').open(newline='') as file:
            assert {row['wording_version'] for row in csv.DictReader(file)} == {version}
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_pilot_helper_refuses_old_schema_without_writing(tmp_path):
    path = tmp_path / 'db.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE random_matrix_player (id INTEGER PRIMARY KEY, choice TEXT)')
        db.execute("INSERT INTO random_matrix_player VALUES (1, 'B')")
    before = path.read_bytes()
    with pytest.raises(SystemExit, match='predates.*wording-version tracking'):
        check_database_schema(tmp_path)
    assert path.read_bytes() == before


@pytest.mark.parametrize('older_version', [None, 'V2.0', 'V2.1', 'V2.1.1', 'V2.2a'])
def test_existing_responses_not_relabelled_or_overwritten(project, older_version):
    result = otree(project, 'create_session', 'nuclear_survey_pilot', '1')
    assert result.returncode == 0, result.stdout + result.stderr
    code = sql(project, 'SELECT code FROM otree_participant')[0]['code']
    server = PilotServer(project)
    server.start()
    try:
        page = request(to_matrix(server.base, code))
        page = request(page.url, {'choice': 'A'})
        page = request(page.url, {'choice': 'B'})
        current_url = page.url
        server.stop()
        # Simulate old/missing version metadata only in this disposable test DB.
        with sqlite3.connect(project / 'db.sqlite3') as db:
            db.execute('UPDATE random_matrix_player SET wording_version = ?', (older_version,))
            default = next(row[4] for row in db.execute('PRAGMA table_info(random_matrix_player)') if row[1] == 'wording_version')
            assert default is None  # No current-version column default/backfill.
        before = sql(project, 'SELECT * FROM random_matrix_player ORDER BY round_number')
        server.start()
        for response in (requests.get(current_url, timeout=10),
                         requests.post(current_url, data={'choice': 'A', 'wording_version': 'V2.2b'}, timeout=10)):
            assert response.status_code == 500
            assert 'historical records are not relabelled' in response.text
        assert sql(project, 'SELECT * FROM random_matrix_player ORDER BY round_number') == before
        assert before[0]['choice'] == 'A' and before[1]['choice'] == 'B'
        assert before[2]['choice'] is None and before[3]['choice'] is None
    finally:
        server.stop()
        server.log.close()
