"""Local synthetic Pilot with disk commits; use a NEW isolated project copy."""
import argparse
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def clean_environment():
    env = os.environ.copy()
    for name in list(env):
        if name.startswith('OTREE_') or name in {'DATABASE_URL', 'REDIS_URL'}:
            env.pop(name)
    return env


def prepare_project(destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    for name in ('settings.py', 'timing.py', 'completion_v5.py'):
        shutil.copy(ROOT / name, destination / name)
    for name in ('eligibility', 'household', 'random_matrix', 'attitudes', '_templates', '_static', 'scripts', 'tests', 'analysis'):
        shutil.copytree(ROOT / name, destination / name, ignore=shutil.ignore_patterns('__pycache__'))
    (destination / '.v2-synthetic-preview').write_text('V2.4 housing / V3.3 flow and attitudes; isolated synthetic Pilot\n')
    return destination


def check_database_schema(project):
    """Read-only compatibility check; never migrate a retained preview DB."""
    database = Path(project).resolve() / 'db.sqlite3'
    if database.exists():
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
            columns = {row[1] for row in connection.execute('PRAGMA table_info(random_matrix_player)')}
            eligibility_columns = {row[1] for row in connection.execute('PRAGMA table_info(eligibility_player)')}
            attitude_columns = {row[1] for row in connection.execute('PRAGMA table_info(attitudes_player)')}
        required = {'wording_version', 'numeric_matrix_version', 'numeric_matrix_hash',
                    'treatment_design_version', 'facility_assignment_seed', 'facility_type_assignment', 'facility_type', 'premium_sek', 'base_rent_sek', 'side_swapped',
                    'chosen_facility_type', 'chosen_distance_km', 'chosen_rent_sek', 'chosen_far', 'task_completed'}
        if not required.issubset(columns):
            raise SystemExit('This database predates current wording-version tracking or facility-treatment fields. Use a new isolated '
                             'current-release preview directory; the historical database has not been changed.')
        attitude_required = {'attitudes_version', 'attitudes_completed', 'attitudes_submitted_at',
                             'nuclear_support', 'nuclear_risk', 'nuclear_economic', 'nuclear_climate', 'housing_cost'}
        if not attitude_required.issubset(attitude_columns):
            raise SystemExit('This database predates V3.0 attitude fields. Use a new isolated Pilot database; '
                             'the historical database has not been changed.')

        if 'survey_flow_version' not in eligibility_columns:
            raise SystemExit('This database predates V3.3 survey flow. Use a new isolated Pilot; no migration performed.')
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
            versions = connection.execute('SELECT DISTINCT survey_flow_version FROM eligibility_player').fetchall()
        if any(row[0] != '5.0.0' for row in versions):
            raise SystemExit('Historical survey flow cannot resume under V3.3; use a new isolated Pilot.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, help='New directory, or a previously prepared V2 preview to resume')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    project = args.project or Path(tempfile.mkdtemp(prefix='sse-v2-parent-')) / 'survey'
    project = project.resolve()
    if project == ROOT or not ((project / '.v2-synthetic-preview').is_file() or not project.exists()):
        raise SystemExit('Use a new directory or a marked V2 preview; never the source/legacy database.')
    if not project.exists():
        prepare_project(project)
    print(f'Isolated Pilot project: {project}', flush=True)
    if args.prepare_only:
        return
    check_database_schema(project)
    env = clean_environment()
    os.environ.clear()
    os.environ.update(env)
    os.chdir(project)
    sys.path.insert(0, str(project))
    # CLI devserver_inner forces OTREE_IN_MEMORY=1. Call the same framework
    # setup/server with its supported disk backend instead; no framework patch.
    from otree.main import setup
    setup()
    from otree.database import IN_MEMORY
    assert not IN_MEMORY
    from otree.cli.prodserver1of2 import run_asgi_server
    print(f'Disk-backed synthetic Pilot: http://127.0.0.1:{args.port}', flush=True)
    run_asgi_server('127.0.0.1', args.port, is_devserver=True)


if __name__ == '__main__':
    main()
