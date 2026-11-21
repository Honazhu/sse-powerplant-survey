"""Real Chrome viewport QA on synthetic, disposable local participants.

Install playwright as a dev dependency and set FINAL_CHROME to the browser binary.
Set FINAL_BROWSER_ARTIFACTS to save synthetic screenshots.
"""
import os, shutil, socket, sqlite3, subprocess, sys, time
from pathlib import Path
import pytest, requests
playwright = pytest.importorskip('playwright.sync_api', reason='Install Playwright to run browser QA')
ROOT = Path(__file__).resolve().parents[1]
CHROME = os.environ.get('FINAL_CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')

@pytest.mark.skipif(not Path(CHROME).is_file(), reason='Chrome executable unavailable')
def test_browser_all_viewports(tmp_path):
    project = tmp_path/'project'
    shutil.copytree(ROOT, project, ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.sqlite3','*.pyc','test_artifacts'))
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('OTREE_') or key in ('DATABASE_URL','REDIS_URL'): env.pop(key)
    env['OTREE_ADMIN_PASSWORD']='synthetic-test-password'
    cli=str(Path(sys.executable).with_name('otree'))
    result=subprocess.run([cli,'create_session','survey_final_qa','5'],cwd=project,env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
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
        with playwright.sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=CHROME, headless=True, args=['--no-sandbox'])
            try:
                for width, code in zip((320,375,390,768,1280),codes):
                    page=browser.new_page(viewport={'width':width,'height':850},device_scale_factor=1)
                    def check_layout(stage):
                        metrics=page.evaluate('''() => {const card=document.querySelector('.otree-body').getBoundingClientRect(); return {scroll:document.documentElement.scrollWidth, inner:innerWidth, card:{left:card.left,right:card.right}, over:[...document.querySelectorAll('input,select,textarea,button,.survey-housing-card,.survey-option,.survey-reference,.technology-logos img')].filter(e=>{let s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none' && s.visibility!=='hidden' && r.width>0 && (r.left < -1 || r.right > innerWidth+1)}).map(e=>e.outerHTML.slice(0,160))} }''')
                        assert metrics['scroll'] <= metrics['inner']+1, (width,stage,metrics)
                        assert metrics['card']['left']>=-1 and metrics['card']['right']<=width+1,(width,stage,metrics)
                        assert not metrics['over'], (width,stage,metrics)
                        for logo in page.locator('.technology-logos img').all():
                            assert logo.evaluate('(e)=>e.complete && e.naturalWidth>0')
                        dest=os.environ.get('FINAL_BROWSER_ARTIFACTS')
                        if width==375 and dest:
                            Path(dest).mkdir(parents=True,exist_ok=True)
                            page.screenshot(path=str(Path(dest)/(stage+'.png')),full_page=True)
                    def advance(): page.locator('.otree-btn-next').click()
                    def choose(name,value): page.locator(f'input[name="{name}"][value="{value}"]').check()
                    page.goto(base+'/InitializeParticipant/'+code,wait_until='networkidle')
                    choose('adult_confirmed','True'); advance()
                    check_layout('consent'); choose('willing_to_participate','True'); advance()
                    check_layout('cookies'); choose('cookies_allowed','False'); advance()
                    assert '/ScenarioInstructions/' in page.url
                    check_layout('instructions'); assert 'Part B' in page.locator('.survey-section').inner_text(); advance()
                    for n in range(6):
                        check_layout('choice' if n==0 else f'choice_{n+1}')
                        assert page.locator('.survey-housing-card').count()==2
                        assert all(page.locator(f'[data-attribute="{attr}"]').count()==2 for attr in ('distance_km','rent_sek_month'))
                        choose('choice','A'); advance()
                    assert '/AttitudeSurvey/' in page.url
                    check_layout('attitudes'); assert 'Part C' in page.locator('.survey-section').inner_text()
                    assert page.locator('.survey-attitudes input[type=range]').count()==0
                    for field in ('nuclear_economic','nuclear_climate','nuclear_support','nuclear_risk','housing_cost'): choose(field,'99')
                    advance()
                    assert '/HouseholdInformation/' in page.url
                    check_layout('household'); assert 'Part D' in page.locator('.survey-section').inner_text()
                    search=page.locator('#country-search'); select=page.locator('select[name=residence_code]')
                    search.fill('South Georgia')
                    assert not select.locator('option[value="GS"]').evaluate('(e)=>e.hidden')
                    assert select.locator('option[value="SE"]').evaluate('(e)=>e.hidden')
                    assert not select.locator('option[value="prefer_not"]').evaluate('(e)=>e.hidden')
                    select.select_option('GS'); assert select.input_value()=='GS'
                    select.select_option('prefer_not'); assert select.input_value()=='prefer_not'
                    card=page.locator('.otree-body').bounding_box(); box=select.bounding_box()
                    assert card['x']-1<=box['x'] and box['x']+box['width']<=card['x']+card['width']+1
                    for field,value in [('age_group','prefer_not'),('gender','prefer_not'),('main_activity','prefer_not'),('rent_status_final','prefer_not'),('income_missing_reason','prefer_not'),('children_under_18','prefer_not'),('education_completed','prefer_not')]: choose(field,value)
                    feedback=page.locator('textarea[name=additional_feedback]'); feedback.fill('Synthetic feedback\nSecond line')
                    assert feedback.evaluate('(e)=>e.scrollWidth <= e.clientWidth')
                    check_layout('feedback'); advance()
                    assert 'Thank you for completing the survey' in page.locator('h1').inner_text()
                    check_layout('completion')
                    page.close()
            finally: browser.close()
    finally:
        proc.terminate(); proc.wait(timeout=10); log.close()
