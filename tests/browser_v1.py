"""Optional local Chrome CDP acceptance test; see docs/UI_TESTING.md. Synthetic only."""
import asyncio,base64,csv,io,json,time,urllib.request,os
from pathlib import Path
import websockets

BASE=os.environ.get('SURVEY_TEST_BASE', 'http://127.0.0.1:8000')
DEBUG_BASE=os.environ.get('SURVEY_CHROME_DEBUG', 'http://127.0.0.1:9227')
OUT=Path(__file__).resolve().parents[1] / 'docs/ui_previews/v1_1'
OUT.mkdir(parents=True,exist_ok=True)
REPORT={'browser':'Installed Chrome headless; mobile viewport/touch emulation, not physical iPhone Safari','viewports':[375,390,430,1280,1440],'checks':[],'screenshots':[]}

def http(path):
    with urllib.request.urlopen(BASE+path) as r:return r.read().decode()

async def new_participant():
    async with websockets.connect(BASE.replace('http://', 'ws://') + '/create_demo_session') as ws:
        await ws.send(json.dumps({'session_config':'nuclear_survey_pilot'}))
        while True:
            message=json.loads(await ws.recv())
            if 'error' in message:raise RuntimeError(message)
            if 'session_url' in message:break
    rows=list(csv.DictReader(io.StringIO(http('/ExportWide'))))
    return rows[-1]['participant.code']

class CDP:
    def __init__(self,ws):self.ws=ws;self.id=0;self.events=[]
    async def call(self,method,params=None):
        self.id+=1;mid=self.id
        await self.ws.send(json.dumps({'id':mid,'method':method,'params':params or {}}))
        while True:
            data=json.loads(await self.ws.recv())
            if data.get('id')==mid:
                if 'error' in data:raise RuntimeError(data)
                return data.get('result',{})
            self.events.append(data)
    async def js(self,expression):
        r=await self.call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
        if 'exceptionDetails' in r:raise RuntimeError(r['exceptionDetails'])
        return r['result'].get('value')
    async def wait(self,page):
        for _ in range(100):
            try:
                if await self.js("document.readyState === 'complete' && location.pathname.includes("+json.dumps('/'+page+'/')+") && !!document.querySelector('.survey-heading h1')"):
                    return
            except RuntimeError:pass
            await asyncio.sleep(.1)
        raise AssertionError((page,await self.js('location.href+document.body.innerText')))
    async def start(self,code):
        await self.call('Page.navigate',{'url':BASE+'/InitializeParticipant/'+code})
        await self.wait('AgeConfirmation')
    async def choose(self,name,value):
        result=await self.js(f'''(() => {{ const input = document.querySelector('input[name="{name}"][value="{value}"]'); if(!input) return false; input.click(); return input.checked; }})()''')
        assert result,(name,value)
    async def next(self,page,double=False):
        await self.js("document.querySelector('.otree-btn-next').click();"+("document.querySelector('.otree-btn-next').click();" if double else ''))
        await self.wait(page)
    async def capture(self,label):
        for width in REPORT['viewports']:
            await self.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':844 if width<640 else 1000,'deviceScaleFactor':1,'mobile':width<640})
            await self.call('Emulation.setTouchEmulationEnabled',{'enabled':width<640})
            await self.js('scrollTo(0,0)')
            await asyncio.sleep(.06)
            layout=await self.js('''(() => {
                const boxes=s=>Array.from(document.querySelectorAll(s)).map(e=>({width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}));
                const housing=Array.from(document.querySelectorAll('.survey-housing-card')).map(e=>({x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y}));
                return {width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
                formCount:document.querySelectorAll('form').length,h1:document.querySelector('h1').textContent,
                targets:boxes('.survey-option,.survey-rating,.otree-btn-next,.survey-copy-id'),housing,
                scaleColumns:document.querySelector('.survey-rating-grid')?getComputedStyle(document.querySelector('.survey-rating-grid')).gridTemplateColumns.split(' ').length:null,
                lang:document.documentElement.lang,viewport:document.querySelector('meta[name="viewport"]').content,
                bodyFont:getComputedStyle(document.body).fontSize};
            })()''')
            assert layout['scroll']<=layout['client'],(label,width,layout)
            assert layout['formCount']==1,(label,width,layout)
            assert layout['lang']=='en' and 'viewport-fit=cover' in layout['viewport']
            assert float(layout['bodyFont'][:-2])>=16
            assert all(t['height']>=44 and t['width']>=44 for t in layout['targets']),(label,width,layout)
            if layout['scaleColumns'] is not None:assert layout['scaleColumns']==(5 if width<640 else 10)
            if layout['housing']:
                a,b=layout['housing'];assert (a['x']==b['x'] and a['y']<b['y']) if width<640 else (a['x']<b['x'] and a['y']==b['y'])
            metrics=await self.call('Page.getLayoutMetrics');height=metrics['cssContentSize']['height']
            file=f'{"mobile" if width<640 else "desktop"}_{width}_{label}.png'
            result=await self.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':True,'clip':{'x':0,'y':0,'width':width,'height':height,'scale':1}})
            (OUT/file).write_bytes(base64.b64decode(result['data']))
            REPORT['screenshots'].append(file)
            REPORT['checks'].append({'page':label,'width':width,'horizontal_overflow':False,'touch_targets_44px':True,'single_form':True})


async def fill(c, rent='6500', income='25', refuse=False, pays=True):
    await c.choose('age_group', '26_35')
    await c.choose('rent_status', 'True' if pays else 'False')
    await c.choose('previous_power_plant_exposure', '2')
    await c.js("document.querySelector('[name=income_not_disclosed]').checked="+str(refuse).lower()+";document.querySelector('[name=income_not_disclosed]').dispatchEvent(new Event('change',{bubbles:true}))")
    for name,value in [('monthly_rent_sek',rent),('income_thousand_sek',income)]:
        await c.js("(()=>{const e=document.querySelector('[name="+name+"]');e.value="+json.dumps(value)+";e.dispatchEvent(new Event('input',{bubbles:true}));})()")

async def wait_error(c):
    for _ in range(80):
        if await c.js("document.body.innerText.includes('Please enter a valid number.') && !!document.querySelector('.otree-form-errors')"):return
        await asyncio.sleep(.1)
    raise AssertionError(await c.js('document.body.innerText'))

async def badge(c, code):
    assert await c.js("document.querySelector('#survey-reference-code').textContent.trim()") == code

async def main():
    tabs=json.load(urllib.request.urlopen(DEBUG_BASE + '/json'))
    target=next(t for t in tabs if t['type']=='page')
    async with websockets.connect(target['webSocketDebuggerUrl'],max_size=16*1024*1024) as ws:
        c=CDP(ws);await c.call('Page.enable');await c.call('Runtime.enable');await c.call('Network.enable')
        code=await new_participant();await c.start(code)
        assert not await c.js("!!document.querySelector('#survey-reference-code')")
        await c.capture('eligibility')
        await c.choose('adult_confirmed','True');await c.next('Introduction')
        assert not await c.js("!!document.querySelector('#survey-reference-code')")
        await c.capture('introduction')
        await c.next('VoluntaryParticipation',double=True)
        assert not await c.js("!!document.querySelector('#survey-reference-code')")
        assert '43086@student.hhs.se' in await c.js('document.body.innerText')
        await c.capture('consent')
        await c.choose('willing_to_participate','True')
        await c.choose('cookies_allowed','True')
        assert await c.js("document.querySelector('#cookie-probe-status').value")=='supported'
        assert not await c.js("document.cookie.includes('nuclear_cookie_probe')")
        await c.next('HouseholdInformation');await badge(c,code)
        await c.call('Emulation.setFocusEmulationEnabled', {'enabled':True})
        await c.call('Page.bringToFront')
        await c.call('Browser.grantPermissions',{'origin':BASE,'permissions':['clipboardReadWrite','clipboardSanitizedWrite']})
        await c.js("document.querySelector('[data-copy-reference]').click()")
        for _ in range(30):
            if await c.js("document.querySelector('[data-copy-status]').textContent==='Copied'"):break
            await asyncio.sleep(.1)
        assert await c.js('navigator.clipboard.readText()') == code
        await c.js("navigator.clipboard.writeText=()=>Promise.reject(new Error('synthetic unsupported'));document.querySelector('[data-copy-reference]').click()")
        await asyncio.sleep(.1)
        assert await c.js('getSelection().toString()') == code
        assert 'manually' in await c.js("document.querySelector('[data-copy-status]').textContent")
        await c.capture('reference_household')
        assert await c.js("document.querySelector('#rent-amount').hidden")
        await fill(c)
        await c.capture('household')
        await c.choose('rent_status','False')
        assert await c.js("document.querySelector('#rent-amount').hidden && document.querySelector('[name=monthly_rent_sek]').value === ''")
        await c.js("document.querySelector('[name=income_not_disclosed]').click()")
        assert await c.js("document.querySelector('[name=income_thousand_sek]').value === '' && document.querySelector('[name=income_thousand_sek]').disabled")
        await c.capture('household_missing')
        await fill(c,rent='12.5',income='-1')
        assert await c.js("document.querySelector('[name=monthly_rent_sek]').getAttribute('aria-invalid')==='true'")
        assert not await c.js("document.querySelector('form').checkValidity()")
        # Bypass all browser validation and handlers to test the real server.
        await c.js("document.querySelector('form').submit()")
        await wait_error(c)
        await c.capture('household_errors')
        await fill(c)
        await c.next('MatrixPlaceholder',double=True);await badge(c,code)
        before=await c.js("document.querySelector('.survey-housing-grid').innerText")
        await c.call('Page.reload');await c.wait('MatrixPlaceholder');await badge(c,code)
        assert before==await c.js("document.querySelector('.survey-housing-grid').innerText")
        await c.capture('matrix_demo')
        await c.next('AttitudesPlaceholder');await badge(c,code);await c.capture('attitudes')
        await c.next('Completion');await badge(c,code)
        assert not await c.js("!!document.querySelector('.otree-btn-next')")
        REPORT['checks'].append({'adult_complete':'passed','copy_clipboard_and_fallback':'passed','badge_all_apps_and_reload':'passed','conditional_clearing':'passed','numeric_client_and_server_errors':'passed','double_submit_did_not_skip':'passed','matrix_refresh':'passed'})
        for case in ['under_18','declined','cookie_refused','cookie_blocked','javascript_disabled']:
            casecode=await new_participant()
            if case=='javascript_disabled':await c.call('Emulation.setScriptExecutionDisabled',{'value':True})
            await c.start(casecode)
            await c.choose('adult_confirmed','False' if case=='under_18' else 'True')
            await c.next('Exit' if case=='under_18' else 'Introduction')
            if case!='under_18':
                await c.next('VoluntaryParticipation')
                await c.choose('willing_to_participate','False' if case=='declined' else 'True')
                if case=='declined':await c.next('Exit')
            if case in ['under_18','declined']:
                assert not await c.js("!!document.querySelector('.otree-btn-next')")
                assert not await c.js("!!document.querySelector('#survey-reference-code')")
                if case=='under_18':
                    await c.capture('exit')
                    await c.call('Page.navigate',{'url':BASE+'/p/'+casecode+'/household/HouseholdInformation/5'})
                    await c.wait('Exit')
                    assert not await c.js("!!document.querySelector('[name=age_group]')")
            else:
                if case=='cookie_blocked':await c.js("Object.defineProperty(document,'cookie',{configurable:true,get(){throw new Error('synthetic blocked')},set(){throw new Error('synthetic blocked')}})")
                await c.choose('cookies_allowed','False' if case=='cookie_refused' else 'True')
                assert await c.js("document.querySelector('#cookie-probe-status').value")==('declined' if case=='cookie_refused' else 'not_tested' if case=='javascript_disabled' else 'blocked')
                await c.next('HouseholdInformation')
                if case=='javascript_disabled':
                    await fill(c,rent='bad',income='bad',refuse=True,pays=False)
                    # Ordinary Next with JS disabled: inactive strings must not block progression.
                    await c.next('MatrixPlaceholder')
                else:
                    await fill(c,rent='',income='0',pays=False)
                    await c.next('MatrixPlaceholder')
                await badge(c,casecode)
                await c.next('AttitudesPlaceholder');await badge(c,casecode);await c.next('Completion')
            REPORT['checks'].append({case:'passed'})
            if case=='javascript_disabled':await c.call('Emulation.setScriptExecutionDisabled',{'value':False})
        rows=list(csv.DictReader(io.StringIO(http('/ExportWide'))))
        row=next(r for r in rows if r['participant.code']==code)
        assert row['household.1.player.income_sek']=='25000'
        assert row['household.1.player.monthly_rent_sek']=='6500'
        assert row['household.1.player.previous_power_plant_exposure']=='2'
        assert row['attitudes.1.player.nuclear_energy_support']==''
        assert row['participant.finished']=='1'
        last=next(r for r in rows if r['participant.code']==casecode)
        assert last['household.1.player.monthly_rent_sek']==last['household.1.player.income_sek']==''
        assert last['household.1.player.income_not_disclosed']=='1'
        REPORT['checks'].append({'browser_csv_join_and_values':'passed'})
        errors=[e for e in c.events if e.get('method')=='Runtime.exceptionThrown']
        REPORT['javascript_uncaught_errors']=errors
        assert not errors,errors
    (OUT/'checks.json').write_text(json.dumps(REPORT,indent=2))
    print('PASS:',len(REPORT['screenshots']),'real Chrome screenshots; V1 browser flows, responsive UI and CSV checks passed.')

if __name__ == '__main__':
    asyncio.run(main())
