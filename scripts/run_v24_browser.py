"""Run bounded Chrome checks against a fresh local synthetic Pilot; clean up owned processes."""
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from scripts.pilot_server import prepare_project, clean_environment

ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def ready(url, process):
    for _ in range(150):
        if process.poll() is not None:
            raise RuntimeError(f'Owned process exited with {process.returncode}')
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:return
        except OSError:pass
        time.sleep(.1)
    raise RuntimeError('Local process startup timeout')


def main():
    run_id=str(time.time_ns())
    evidence=ROOT/'docs/v2_4_evidence'/('browser_run_'+run_id);evidence.mkdir()
    workspace=Path(tempfile.mkdtemp(prefix='sse-v24-browser-'))
    project=prepare_project(workspace/'survey')
    server_port,chrome_port=port(),port()
    processes=[];logs=[];report=dict(project=str(project),evidence=str(evidence))
    try:
        for name,command in [
            ('pilot',[sys.executable,str(ROOT/'scripts/pilot_server.py'),'--project',str(project),'--port',str(server_port)]),
            ('chrome',['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','--headless',
                       '--remote-debugging-address=127.0.0.1',f'--remote-debugging-port={chrome_port}',
                       f'--user-data-dir={workspace}/chrome','--no-first-run','--no-default-browser-check',
                       '--disable-background-networking','--disable-sync','about:blank'])]:
            log=(evidence/f'{name}.log').open('x');logs.append(log)
            processes.append(subprocess.Popen(command,stdout=log,stderr=log,env=clean_environment()))
        ready(f'http://127.0.0.1:{server_port}',processes[0])
        ready(f'http://127.0.0.1:{chrome_port}/json',processes[1])
        env=clean_environment()
        env.update(SURVEY_TEST_BASE=f'http://127.0.0.1:{server_port}',SURVEY_CHROME_DEBUG=f'http://127.0.0.1:{chrome_port}',
                   SURVEY_TEST_VIEWPORTS='390,1440',SURVEY_SCREENSHOT_PAGES='instructions,choice_1,choice_2,choice_3,choice_4,nuclear_comparison,oil_fired_comparison,zero_premium,choice_required_error,choice_selected,completion')
        with (evidence/'browser.log').open('x') as log:
            result=subprocess.run([sys.executable,str(ROOT/'tests/browser_v24.py')],env=env,stdout=log,stderr=log,timeout=330)
        report['browser_returncode']=result.returncode
        print((evidence/'browser.log').read_text())
        if result.returncode:raise RuntimeError('Browser assertions failed; see retained log.')
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
        for log in logs:log.close()
        report['owned_processes_stopped']=all(p.poll() is not None for p in processes)
        database=project/'db.sqlite3'
        if database.exists():
            with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
                report['integrity_check']=db.execute('PRAGMA integrity_check').fetchone()[0]
                report['foreign_key_violations']=db.execute('PRAGMA foreign_key_check').fetchall()
        (evidence/'process-status.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))


if __name__=='__main__':main()
