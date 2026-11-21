"""Synthetic local integration checks; isolated disposable database only."""
import base64, csv, io, json, os, pickle, re, shutil, socket, sqlite3, subprocess, sys, time
from pathlib import Path
from collections import Counter
import requests

ROOT = Path(__file__).resolve().parents[1]

def test_final_http(tmp_path):
    project = tmp_path / 'project'
    shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.sqlite3','*.pyc'))
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('OTREE_') or key in ('DATABASE_URL','REDIS_URL'): env.pop(key)
    env['OTREE_ADMIN_PASSWORD'] = 'synthetic-test-password'
    cli = str(Path(sys.executable).with_name('otree'))
    create = subprocess.run([cli,'create_session','survey_final_production','9'],cwd=project,env=env,capture_output=True,text=True,timeout=30)
    assert create.returncode == 0, create.stderr
    with sqlite3.connect(project/'db.sqlite3') as db:
        codes = [r[0] for r in db.execute('select code from otree_participant order by id_in_session')]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    server_code = "from otree.main import setup; setup(); from otree.cli.prodserver1of2 import run_asgi_server; run_asgi_server('127.0.0.1', %d, is_devserver=True)" % port
    log = (tmp_path/'server.log').open('w+')
    proc = subprocess.Popen([sys.executable,'-c',server_code], cwd=project, env=env, stdout=log, stderr=log)
    base = f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if proc.poll() is not None:
                log.seek(0); raise AssertionError(log.read())
            try:
                if requests.get(base,timeout=1).status_code==200: break
            except requests.ConnectionError: pass
            time.sleep(.05)
        else: raise AssertionError('server startup timeout')
        def get(url):
            r=requests.get(url,timeout=10); assert r.status_code==200, r.text[:3000]; return r
        def post(page,data):
            r=requests.post(page.url,data=data,timeout=10); assert r.status_code==200, r.text[:3000]; return r
        def start(i, age='True'):
            return post(get(base+'/InitializeParticipant/'+codes[i]),{'adult_confirmed':age})
        def finished(code):
            # Only deserialize synthetic data created by this isolated test.
            with sqlite3.connect(project/'db.sqlite3') as db:
                raw = db.execute('select _vars from otree_participant where code=?', (code,)).fetchone()[0]
            return pickle.loads(base64.b64decode(raw))['finished']
        assert '/Exit/' in start(0,'False').url
        assert '/Exit/' in post(start(1),{'willing_to_participate':'False'}).url
        for i in range(2,9):
            page=start(i); assert codes[i] in page.text
            page=post(page,{'willing_to_participate':'True'}); assert '/CookiePreferences/' in page.url
            assert '/CookiePreferences/' in post(page,{}).url
            page=post(page,{'cookies_allowed': 'True' if i==3 else 'False'}); assert '/ScenarioInstructions/' in page.url
            assert codes[i] in page.text and 'Part B' in page.text
            page=post(page,{})
            with sqlite3.connect(project/'db.sqlite3') as db:
                assignment_before = db.execute('select assignment_json from random_matrix_player r join otree_participant p on p.id=r.participant_id where p.code=? and r.round_number=1', (codes[i],)).fetchone()[0]
                attitude_values = db.execute('select a.attitudes_completed, a.nuclear_economic, a.nuclear_climate, a.nuclear_support, a.nuclear_risk, a.housing_cost from attitudes_player a join otree_participant p on p.id=a.participant_id where p.code=?', (codes[i],)).fetchone()
                household_values = db.execute('select h.household_completed, h.age_group from household_player h join otree_participant p on p.id=h.participant_id where p.code=?', (codes[i],)).fetchone()
                assert attitude_values[0] == 0 and all(value is None for value in attitude_values[1:])
                assert household_values[0] == 0 and household_values[1] is None
            for n in range(1,7):
                assert f'Question {n} of 6' in page.text and codes[i] in page.text and not finished(codes[i])
                before=re.search(r'data-choice-set="(S\d+)"',page.text).group(1)
                assert before in get(page.url).text
                page=post(page,{'choice':'A'})
                if (i == 4 and n == 2) or (i == 7 and n == 4) or (i == 8 and n == 5): break
            if i in (4,7,8): continue
            assert '/AttitudeSurvey/' in page.url and codes[i] in page.text and 'Part C' in page.text
            assert 'type="range"' not in page.text
            with sqlite3.connect(project/'db.sqlite3') as db:
                complete = db.execute('select h.household_completed from household_player h join otree_participant p on p.id=h.participant_id where p.code=?',(codes[i],)).fetchone()[0]
                assert not complete
            attitudes=dict(nuclear_economic='99',nuclear_climate='0',nuclear_support='-2',nuclear_risk='99',housing_cost='2')
            if i == 6: attitudes = dict.fromkeys(attitudes, '99')
            page=post(page,attitudes)
            assert '/HouseholdInformation/' in page.url and codes[i] in page.text and 'Part D' in page.text and not finished(codes[i])
            with sqlite3.connect(project/'db.sqlite3') as db:
                assignment_after = db.execute('select assignment_json from random_matrix_player r join otree_participant p on p.id=r.participant_id where p.code=? and r.round_number=1', (codes[i],)).fetchone()[0]
                assert assignment_before == assignment_after
            if i==5: continue
            h=dict(age_group='prefer_not',gender='non_binary',residence_code='prefer_not',main_activity='prefer_not',rent_status_final='prefer_not',income_missing_reason='prefer_not',children_under_18='prefer_not',education_completed='prefer_not')
            if i==3: h.update(rent_status_final='yes', rent_missing_reason='dont_know', income_missing_reason='', household_income_after_tax='45000',additional_feedback='<script>alert(1)</script>')
            invalid=dict(h,additional_feedback='<script>alert(1)</script>' + 'a'*1501)
            invalid_page = post(page,invalid)
            assert '/HouseholdInformation/' in invalid_page.url and not finished(codes[i])
            assert '<script>alert(1)</script>' not in invalid_page.text and '&lt;script&gt;' in invalid_page.text
            old=page.url
            page=post(page,h); assert '/Completion/' in page.url and codes[i] in page.text and finished(codes[i])
            assert '/Completion/' in get(page.url).url
            requests.post(old,data=h,timeout=10)
        rows=list(csv.DictReader(io.StringIO(get(base+'/api/export_app_custom?app=household').text)))
        assert len(rows)==3 and {r['survey_reference_id'] for r in rows}=={codes[2],codes[3],codes[6]}
        no=next(r for r in rows if r['survey_reference_id']==codes[2]); yes=next(r for r in rows if r['survey_reference_id']==codes[3])
        assert no['nuclear_economic']=='' and no['nuclear_economic_missing_reason']=='dont_know'
        assert no['nuclear_climate']=='0' and no['nuclear_risk_missing_reason']=='prefer_not'
        missing = next(r for r in rows if r['survey_reference_id']==codes[6])
        for field in ('nuclear_economic','nuclear_climate','nuclear_support','nuclear_risk','housing_cost'):
            assert missing[field] == ''
            assert missing[field+'_missing_reason'] == ('dont_know' if field in ('nuclear_economic','nuclear_climate') else 'prefer_not')
        assert no['monthly_rent_sek']=='' and no['income_missing_reason']=='prefer_not'
        assert all(no[f'choice_{n}_task_duration_s']=='' for n in range(1,7))
        assert yes['household_income_after_tax']=='45000' and yes['rent_missing_reason']=='dont_know'
        assert yes['additional_feedback']=='<script>alert(1)</script>'
        assert all(r['survey_version']=='final' for r in rows)
        for row in rows:
            assert Counter(row[f'choice_{n}_facility_type'] for n in range(1,7)) == {'nuclear':3, 'oil_fired':3}
            assignment = json.loads(row['assignment_json'])
            assert len(assignment['tasks']) == 6
            for n, task in enumerate(assignment['tasks'], 1):
                assert row[f'choice_{n}_choice'] == 'A'
                assert row[f'choice_{n}_choice_set_id'] == task['choice_set_id']
                for side in 'AB':
                    assert int(row[f'choice_{n}_{side}_distance_km']) == task[side]['distance_km']
                    assert int(row[f'choice_{n}_{side}_rent_sek_month']) == task[side]['rent_sek_month']
        timing=list(csv.DictReader(io.StringIO(get(base+'/api/export_app_custom?app=household&function_name=custom_export_timing').text)))
        assert timing and {r['participant_code'] for r in timing}=={codes[3]}
        assert all(r['page_name'] != 'CookiePreferences' for r in timing)
        assert any(r['page_name'] == 'AttitudeSurvey' and r['seconds_on_page'] != '' for r in timing)
    finally:
        proc.terminate(); proc.wait(timeout=10); log.close()
    # Deletion runs offline against only this disposable database. The page-time
    # export above flushed the single test worker's native timing buffer.
    deletion_env = env.copy()
    deletion_env['FINAL_DELETION_DATABASE_URL'] = 'sqlite:///' + str(project / 'db.sqlite3')
    command = [sys.executable, str(project / 'scripts/delete_final_participant.py'), codes[3]]
    with sqlite3.connect(project / 'db.sqlite3') as db:
        snapshot = list(db.iterdump())
        other_id = db.execute('select id from otree_participant where code=?',(codes[2],)).fetchone()[0]
        other_before = {t: db.execute(f'select * from {t} where participant_id=? order by id',(other_id,)).fetchall() for t in ('eligibility_player','attitudes_player','random_matrix_player','household_player')}
    dry = subprocess.run(command, cwd=project, env=deletion_env, capture_output=True, text=True)
    assert dry.returncode == 0 and 'Dry run' in dry.stdout, dry.stderr
    with sqlite3.connect(project / 'db.sqlite3') as db:
        assert list(db.iterdump()) == snapshot
    wrong = subprocess.run(command + ['--execute', '--maintenance-confirmed'], input='wrong\n', cwd=project, env=deletion_env, capture_output=True, text=True)
    assert wrong.returncode != 0
    # Failure after child-row/timing updates must roll back the entire transaction.
    with sqlite3.connect(project / 'db.sqlite3') as db:
        db.execute("CREATE TRIGGER test_abort_delete BEFORE DELETE ON otree_participant BEGIN SELECT RAISE(ABORT, 'test rollback'); END")
        db.commit()
        before_failure = list(db.iterdump())
    failed = subprocess.run(command + ['--execute', '--maintenance-confirmed'], input=codes[3]+'\n', cwd=project, env=deletion_env, capture_output=True, text=True)
    assert failed.returncode != 0
    with sqlite3.connect(project / 'db.sqlite3') as db:
        assert list(db.iterdump()) == before_failure
        db.execute('DROP TRIGGER test_abort_delete')
    deletion = subprocess.run(command + ['--execute', '--maintenance-confirmed'], input=codes[3]+'\n', cwd=project, env=deletion_env, capture_output=True, text=True)
    assert deletion.returncode == 0, deletion.stderr
    with sqlite3.connect(project / 'db.sqlite3') as db:
        assert db.execute('select count(*) from otree_participant where code=?',(codes[3],)).fetchone()[0]==0
        assert db.execute('select count(*) from otree_participant where code=?',(codes[2],)).fetchone()[0]==1
        for table in ('eligibility_player', 'attitudes_player', 'random_matrix_player', 'household_player'):
            assert db.execute(f'select * from {table} where participant_id=? order by id',(other_id,)).fetchall() == other_before[table]
            assert db.execute(f'select count(*) from {table} where participant_id not in (select id from otree_participant)').fetchone()[0]==0
        all_timing=''.join((x[0] or '') for x in db.execute('select text from otree_pagetimebatch'))
        assert codes[3] not in all_timing and codes[2] in all_timing
    again = subprocess.run(command, cwd=project, env=deletion_env, capture_output=True, text=True)
    assert again.returncode != 0
    with (tmp_path / 'restart.log').open('w+') as restart_log:
        proc = subprocess.Popen([sys.executable,'-c',server_code], cwd=project, env=env, stdout=restart_log, stderr=restart_log)
        try:
            for _ in range(100):
                try:
                    response = requests.get(base+'/api/export_app_custom?app=household',timeout=1)
                    if response.status_code==200: break
                except requests.ConnectionError: pass
                time.sleep(.05)
            else: raise AssertionError('server restart timeout')
            after=list(csv.DictReader(io.StringIO(response.text)))
            assert {r['survey_reference_id'] for r in after}=={codes[2],codes[6]}
        finally:
            proc.terminate(); proc.wait(timeout=10)

def test_twenty_concurrent_qa_sqlite(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    project = tmp_path / 'project'
    shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.sqlite3','*.pyc'))
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('OTREE_') or key in ('DATABASE_URL','REDIS_URL'): env.pop(key)
    env['OTREE_ADMIN_PASSWORD']='synthetic-test-password'
    cli = str(Path(sys.executable).with_name('otree'))
    create=subprocess.run([cli,'create_session','survey_final_qa','20'],cwd=project,env=env,capture_output=True,text=True,timeout=30)
    assert create.returncode==0, create.stderr
    with sqlite3.connect(project/'db.sqlite3') as db: codes=[r[0] for r in db.execute('select code from otree_participant order by id_in_session')]
    with socket.socket() as sock: sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    code="from otree.main import setup; setup(); from otree.cli.prodserver1of2 import run_asgi_server; run_asgi_server('127.0.0.1', %d, is_devserver=True)"%port
    log=(tmp_path/'server.log').open('w+')
    proc=subprocess.Popen([sys.executable,'-c',code],cwd=project,env=env,stdout=log,stderr=log)
    base=f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if proc.poll() is not None: log.seek(0); raise AssertionError(log.read())
            try:
                if requests.get(base,timeout=1).status_code==200: break
            except requests.ConnectionError: pass
            time.sleep(.05)
        else: raise AssertionError('server startup timeout')
        def participant(code):
            def request(method,url,data=None):
                r=requests.request(method,url,data=data,timeout=30)
                assert r.status_code==200, r.text[:1000]
                return r
            p=request('GET',base+'/InitializeParticipant/'+code)
            p=request('POST',p.url,{'adult_confirmed':'True'})
            p=request('POST',p.url,{'willing_to_participate':'True'})
            p=request('POST',p.url,{'cookies_allowed':'False'})
            assert '/ScenarioInstructions/' in p.url
            p=request('POST',p.url,{})
            for _ in range(6): p=request('POST',p.url,{'choice':'A'})
            assert '/AttitudeSurvey/' in p.url
            score = ['2','1','0','-1','-2','99'][codes.index(code) % 6]
            p=request('POST',p.url,dict.fromkeys(['nuclear_economic','nuclear_climate','nuclear_support','nuclear_risk','housing_cost'], score))
            p=request('POST',p.url,dict(age_group='prefer_not',gender='prefer_not',residence_code='prefer_not',main_activity='prefer_not',rent_status_final='no',income_missing_reason='dont_know',children_under_18='prefer_not',education_completed='prefer_not'))
            assert '/Completion/' in p.url
        with ThreadPoolExecutor(max_workers=20) as pool: list(pool.map(participant,codes))
        with sqlite3.connect(project/'db.sqlite3') as db:
            assignments=db.execute('select allocation_index, assignment_json from random_matrix_player where round_number=1').fetchall()
        assert len(assignments)==20 and len({r[0] for r in assignments})==20
        assert all(len(json.loads(r[1])['tasks'])==6 for r in assignments)
        with sqlite3.connect(project/'db.sqlite3') as db:
            saved = db.execute('select p.code, a.nuclear_economic, a.nuclear_climate, a.nuclear_support, a.nuclear_risk, a.housing_cost from attitudes_player a join otree_participant p on p.id=a.participant_id').fetchall()
        assert len(saved)==20
        for code, *values in saved:
            score=[2,1,0,-1,-2,99][codes.index(code) % 6]
            assert values == [score]*5

        rows=list(csv.DictReader(io.StringIO(requests.get(base+'/api/export_app_custom?app=household',timeout=10).text)))
        assert rows==[]
    finally:
        proc.terminate(); proc.wait(timeout=10); log.close()
