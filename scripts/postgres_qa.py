#!/usr/bin/env python3
"""Destructive-to-test-data PostgreSQL QA, only on an explicitly provided EMPTY test DB.

See FINAL_DEPLOYMENT_CHECKLIST.md. Never point at an existing study database.
"""
import argparse, csv, io, json, os, shutil, socket, subprocess, sys, tempfile, threading, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import requests
from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-disposable-empty-db',action='store_true')
    args=parser.parse_args()
    url=os.environ.get('FINAL_TEST_DATABASE_URL','')
    parsed=urlparse(url)
    if not args.confirm_disposable_empty_db or parsed.scheme not in ('postgres','postgresql') or not parsed.path.lstrip('/').startswith('final_test_'):
        raise SystemExit('Refused: provide FINAL_TEST_DATABASE_URL for a disposable final_test_* PostgreSQL database and the confirmation flag.')
    engine=create_engine(url.replace('postgres://','postgresql://',1))
    try:
        if inspect(engine).get_table_names(): raise SystemExit('Refused: database public schema is not empty.')
        with tempfile.TemporaryDirectory(prefix='final-postgres-qa-') as folder:
            project=Path(folder)/'project'
            shutil.copytree(ROOT,project,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.sqlite3','*.pyc','test_artifacts'))
            env=os.environ.copy()
            for key in list(env):
                if key.startswith('OTREE_') or key in ('DATABASE_URL','REDIS_URL'): env.pop(key)
            env['DATABASE_URL']=url
            env['OTREE_ADMIN_PASSWORD']='synthetic-test-password'
            cli=str(Path(sys.executable).with_name('otree'))
            created=subprocess.run([cli,'create_session','survey_final_production','22'],cwd=project,env=env,capture_output=True,text=True,timeout=90)
            if created.returncode: raise RuntimeError('Synthetic session creation failed. Inspect server logs in the test environment.')
            with engine.connect() as conn:
                codes=[r[0] for r in conn.execute(text('select code from otree_participant order by id_in_session'))]
            assert len(codes)==22 and len(set(codes))==22
            with socket.socket() as sock: sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
            server="from otree.main import setup; setup(); from otree.cli.prodserver1of2 import run_asgi_server; run_asgi_server('127.0.0.1', %d, is_devserver=True)"%port
            base=f'http://127.0.0.1:{port}'
            log=(Path(folder)/'server.log').open('w+')
            def start():
                p=subprocess.Popen([sys.executable,'-c',server],cwd=project,env=env,stdout=log,stderr=log)
                for _ in range(200):
                    if p.poll() is not None: raise RuntimeError('Test server exited during startup.')
                    try:
                        if requests.get(base,timeout=1).status_code==200: return p
                    except requests.RequestException: pass
                    time.sleep(.05)
                raise RuntimeError('Test server startup timed out.')
            p=start()
            errors=[]; stop=threading.Event()
            def req(method,url,data=None):
                r=requests.request(method,url,data=data,timeout=60)
                if r.status_code!=200: raise RuntimeError(f'HTTP {r.status_code} during synthetic flow')
                return r
            def participant(item):
                code, limit=item
                page=req('GET',base+'/InitializeParticipant/'+code)
                for payload in ({'adult_confirmed':'True'},{'willing_to_participate':'True'},{'cookies_allowed':'False'},{}):
                    page=req('POST',page.url,payload)
                for n in range(limit):
                    assert '/Choice/' in page.url
                    if n==0:
                        assert req('GET',page.url).text==page.text
                    previous=page.url
                    page=req('POST',page.url,{'choice':'A'})
                    if n==0: req('POST',previous,{'choice':'B'})
                if limit<6: return
                assert '/AttitudeSurvey/' in page.url
                page=req('POST',page.url,dict(nuclear_economic='0',nuclear_climate='99',nuclear_support='1',nuclear_risk='-1',housing_cost='2'))
                assert '/HouseholdInformation/' in page.url
                page=req('POST',page.url,dict(age_group='prefer_not',gender='prefer_not',residence_code='prefer_not',main_activity='prefer_not',rent_status_final='no',income_missing_reason='dont_know',children_under_18='prefer_not',education_completed='prefer_not'))
                assert '/Completion/' in page.url
            def exports_while_writing():
                while not stop.is_set():
                    try:
                        rows=list(csv.DictReader(io.StringIO(req('GET',base+'/api/export_app_custom?app=household').text)))
                        ids=[r['survey_reference_id'] for r in rows]
                        assert len(ids)==len(set(ids))
                    except Exception as exc: errors.append(exc); return
                    time.sleep(.05)
            try:
                observer=threading.Thread(target=exports_while_writing,daemon=True); observer.start()
                try:
                    with ThreadPoolExecutor(max_workers=22) as pool: list(pool.map(participant, [(c,6) for c in codes[:20]]+[(codes[20],4),(codes[21],5)]))
                finally: stop.set(); observer.join(timeout=60)
                if errors: raise RuntimeError('An export failed during concurrent writes.') from errors[0]
                def verify():
                    rows=list(csv.DictReader(io.StringIO(req('GET',base+'/api/export_app_custom?app=household').text)))
                    assert len(rows)==20 and {r['survey_reference_id'] for r in rows}==set(codes[:20])
                    for row in rows:
                        assert row['completion_status']=='completed'
                        assert Counter(row[f'choice_{i}_facility_type'] for i in range(1,7))=={'nuclear':3,'oil_fired':3}
                        assert all(row[f'choice_{i}_choice']=='A' for i in range(1,7))
                        assert len(json.loads(row['assignment_json'])['tasks'])==6
                    with engine.connect() as conn:
                        indices=[r[0] for r in conn.execute(text('select allocation_index from random_matrix_player where round_number=1'))]
                    assert len(indices)==22 and len(set(indices))==22
                    return rows
                rows=verify(); p.terminate(); p.wait(timeout=20); p=start(); assert verify()==rows
                print('PASS: 20 completed, 2 partial, concurrent exports, duplicate POST, refresh, restart, unique six-task assignments.')
            finally:
                p.terminate(); p.wait(timeout=20); log.close()
    finally: engine.dispose()

if __name__=='__main__': main()
