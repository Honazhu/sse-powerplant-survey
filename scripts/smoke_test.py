"""Run native oTree bots in an isolated project and export synthetic fixtures."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
APPS = ['eligibility', 'household', 'random_matrix', 'attitudes']


def main():
    env = os.environ.copy()
    for name in list(env):
        if name.startswith('OTREE_') or name in {'DATABASE_URL', 'REDIS_URL'}:
            env.pop(name)
    with TemporaryDirectory(prefix='nuclear-synthetic-') as temporary:
        project = Path(temporary)
        for filename in ['settings.py', 'timing.py']:
            shutil.copy(ROOT / filename, project / filename)
        for directory in [*APPS, '_static', '_templates']:
            shutil.copytree(
                ROOT / directory, project / directory,
                ignore=shutil.ignore_patterns('__pycache__'),
            )
        subprocess.run(
            [str(Path(sys.executable).parent / 'otree'), 'test',
             'nuclear_survey_pilot', '1', '--export', 'synthetic'],
            cwd=project, env=env, check=True, timeout=60,
        )
        destination = ROOT / 'data' / 'synthetic' / ('v3_3_smoke_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        destination.mkdir(parents=True, exist_ok=False)
        for filename in [*(f'{app}.csv' for app in APPS), 'all_apps_wide.csv', 'attitudes_custom.csv', 'random_matrix_custom.csv']:
            shutil.copy(project / 'synthetic' / filename, destination / filename)
        subprocess.run([sys.executable, str(ROOT / 'scripts/export_dce.py'),
                        '--input', str(destination / 'all_apps_wide.csv'), '--output-dir', str(destination)], check=True)
        subprocess.run([sys.executable, str(ROOT / 'analysis/merge_attitudes.py'),
                        '--native', str(destination / 'all_apps_wide.csv'),
                        '--dce-difference', str(destination / 'dce_difference.csv'),
                        '--attitudes', str(destination / 'attitudes_wide.csv'),
                        '--output-dir', str(destination)], check=True)
    print('Exported isolated synthetic records and page timing to', destination)


if __name__ == '__main__':
    main()
