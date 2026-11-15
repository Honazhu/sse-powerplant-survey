"""Optional local Chrome CDP acceptance test; see docs/UI_TESTING.md. Synthetic only."""
import asyncio,base64,csv,io,json,time,urllib.request,os
from pathlib import Path
import websockets

BASE=os.environ.get('SURVEY_TEST_BASE', 'http://127.0.0.1:8000')
DEBUG_BASE=os.environ.get('SURVEY_CHROME_DEBUG', 'http://127.0.0.1:9227')
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT / 'docs/ui_previews' / ('v2_4_' + str(time.time_ns()))
OUT.mkdir(parents=True,exist_ok=True)
VIEWPORTS=[int(width) for width in os.environ.get('SURVEY_TEST_VIEWPORTS','375,390,430,1280,1440').split(',')]
assert VIEWPORTS and all(320 <= width <= 2560 for width in VIEWPORTS)
SCREENSHOT_PAGES=set(filter(None,os.environ.get('SURVEY_SCREENSHOT_PAGES','').split(',')))
REPORT={'wording_version':'V2.4','design_version':'V2.4','numeric_matrix_version':'V2.4','browser':'Installed Chrome headless; mobile viewport/touch emulation, not physical iPhone Safari','viewports':VIEWPORTS,'checks':[],'screenshots':[]}
REPORT['attitudes_version']='V3.0'
ATTITUDE_FIELDS=['nuclear_support','nuclear_risk','nuclear_economic','nuclear_climate','housing_cost']

def http(path):
    with urllib.request.urlopen(BASE+path,timeout=15) as r:return r.read().decode()

def native_row(code):
    return next(row for row in csv.DictReader(io.StringIO(http('/ExportWide'))) if row['participant.code']==code)

async def new_participant():
    async with websockets.connect(BASE.replace('http://', 'ws://') + '/create_demo_session') as ws:
        await ws.send(json.dumps({'session_config':'nuclear_survey_pilot'}))
        while True:
            message=json.loads(await asyncio.wait_for(ws.recv(),timeout=20))
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
            data=json.loads(await asyncio.wait_for(self.ws.recv(),timeout=20))
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
                bodyFont:getComputedStyle(document.body).fontSize,bodyFamily:getComputedStyle(document.body).fontFamily,titleFamily:getComputedStyle(document.querySelector('h1')).fontFamily};
            })()''')
            assert layout['scroll']<=layout['client'],(label,width,layout)
            assert layout['formCount']==1,(label,width,layout)
            assert layout['lang']=='en' and 'viewport-fit=cover' in layout['viewport']
            assert float(layout['bodyFont'][:-2])>=16
            assert 'Inter' in layout['bodyFamily'] and 'Marcellus' in layout['titleFamily']
            assert all(t['height']>=44 and t['width']>=44 for t in layout['targets']),(label,width,layout)
            if layout['scaleColumns'] is not None:assert layout['scaleColumns']==(5 if width<640 else 10)
            if layout['housing']:
                a,b=layout['housing'];assert (a['x']==b['x'] and a['y']<b['y']) if width<640 else (a['x']<b['x'] and a['y']==b['y'])
            if not SCREENSHOT_PAGES or label in SCREENSHOT_PAGES:
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

async def advance_choice(c,index):
    await c.js("document.querySelector('.otree-btn-next').click()")
    for _ in range(100):
        if await c.js("document.readyState==='complete' && (location.pathname.includes('/AttitudeSurvey/') || document.querySelector('[data-task]')?.dataset.task==="+json.dumps(str(index+1))+")"):
            return
        await asyncio.sleep(.1)
    raise AssertionError('Choice did not advance')

async def instructions(c,code,capture=False):
    await c.wait('ScenarioInstructions')
    assert await c.js("document.querySelector('.survey-heading h1').textContent")=='Choosing a Rental Home'
    assert await c.js("document.querySelector('#rental-scenario').textContent")=='Choosing a Rental Home'
    assert await c.js("document.querySelector('#hypothetical-context').textContent.includes('rather than descriptions of actual available homes')")
    assert not await c.js("!!document.querySelector('#power-plant-context')")
    assert await c.js("document.querySelector('[data-wording-version]').dataset.wordingVersion")=='V2.4'
    assert await c.js("document.querySelector('.otree-btn-next').textContent")=='Continue to Housing Choices'
    assert not await c.js("!!document.querySelector('[name=choice]')")
    before=native_row(code)
    assert before['random_matrix.1.player.assignment_json']==''
    assert all(before[f'random_matrix.{i}.player.task_started_at']=='' for i in range(1,5))
    if capture:
        origin=await c.js('performance.timeOrigin')
        await c.call('Page.reload')
        for _ in range(100):
            try:
                if await c.js("document.readyState==='complete' && performance.timeOrigin!=="+json.dumps(origin)):break
            except RuntimeError:pass
            await asyncio.sleep(.1)
        else:raise AssertionError('Instructions reload did not complete')
        await c.wait('ScenarioInstructions')
        after=native_row(code)
        assert {k:v for k,v in before.items() if k.startswith('random_matrix.')}=={k:v for k,v in after.items() if k.startswith('random_matrix.')}
        await c.capture('instructions')
        REPORT['checks'].append({'instructions_refresh_no_allocation_or_task_timer':'passed'})
    await c.next('Choice')
    assert await c.js("document.querySelector('[data-task]').dataset.task")=='1'
    REPORT['checks'].append({'instructions_to_four_choices':'passed'})

async def complete_choices(c,capture=False,code=None):
    displayed=[]
    for index in range(1,5):
        assert await c.js("document.querySelector('[data-task]').dataset.task")==str(index)
        assert await c.js("document.querySelector('.survey-heading h1').textContent") == 'Choosing a Rental Home'
        assert not await c.js("!!document.querySelector('#rental-scenario,#budget-reminder,#repeated-task-reminder')")
        assert await c.js("document.querySelector('[data-wording-version]').dataset.wordingVersion") == 'V2.4'
        assert not await c.js("document.body.innerText.includes('Choose the apartment you prefer, considering')")
        assert await c.js("Array.from(document.querySelectorAll('[data-home=A] dt')).map(e=>e.textContent).join('|')") == 'Power Plant Type|Distance to Power Plant|Monthly Rent'
        assert await c.js("Array.from(document.querySelectorAll('[data-attribute=rent_sek_month]')).every(e=>/^\\d{1,2},\\d{3} SEK\\/month$/.test(e.textContent.trim()))")
        assert not await c.js("!!document.querySelector('[name=choice]:checked')")
        task=await c.js("""(()=>{const t={set:document.querySelector('[data-choice-set]').dataset.choiceSet,facility:document.querySelector('#power-plant-context').dataset.facilityType};for(const side of ['A','B']){t[side]={};for(const e of document.querySelectorAll('[data-home='+side+'] [data-attribute]'))t[side][e.dataset.attribute]=e.dataset.attribute==='facility_type'?e.dataset.value:parseInt(e.textContent.replace(/,/g,''));}return t;})()""")
        assert task['facility'] in ('nuclear','oil_fired')
        assert await c.js("document.querySelector('#power-plant-context').textContent")=='Power plant context: '+dict(nuclear='Nuclear power plant',oil_fired='Oil-fired power plant')[task['facility']]
        assert task['A']['facility_type']==task['B']['facility_type']==task['facility']
        assert await c.js("Array.from(document.querySelectorAll('[data-attribute=facility_type]')).every(e=>e.textContent.trim()==="+json.dumps(dict(nuclear='Nuclear power plant',oil_fired='Oil-fired power plant')[task['facility']])+")")
        assert not await c.js("/Apartment|Floor Area/.test(document.body.innerText)")
        displayed.append(task)
        if capture:
            saved=native_row(code)
            origin=await c.js('performance.timeOrigin')
            await c.call('Page.reload')
            for _ in range(100):
                try:
                    if await c.js("document.readyState==='complete' && performance.timeOrigin!=="+json.dumps(origin)):break
                except RuntimeError:pass
                await asyncio.sleep(.1)
            else:raise AssertionError('Choice reload did not complete')
            await c.wait('Choice')
            refreshed=native_row(code)
            keys=[key for key in saved if key.startswith('random_matrix.')]
            assert {key:saved[key] for key in keys}=={key:refreshed[key] for key in keys}
            assert await c.js("document.querySelector('[data-choice-set]').dataset.choiceSet")==task['set']
            assert await c.js("document.querySelector('[data-wording-version]').dataset.wordingVersion")=='V2.4'
            REPORT['checks'].append({'choice':index,'refresh_preserves_all_four_rounds':'passed',
                                     'block_id':saved['random_matrix.1.player.block_id'],
                                     'choice_set_id':task['set'],'wording_version':'V2.4'})
            await c.capture('choice_'+str(index))
            if not any(x.get('facility_capture')==task['facility'] for x in REPORT['checks']):
                await c.capture(task['facility']+'_comparison')
                REPORT['checks'].append({'facility_capture':task['facility']})
            if task['A']['rent_sek_month']==task['B']['rent_sek_month']:
                await c.capture('zero_premium')
            if index==1:
                # Native server must reject an empty answer without advancing.
                width=REPORT['viewports'][0]
                await c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':844,'deviceScaleFactor':1,'mobile':width<640})
                await c.js("document.querySelector('form').submit()")
                for _ in range(80):
                    if await c.js("!!document.querySelector('.otree-form-errors')"):break
                    await asyncio.sleep(.1)
                assert await c.js("document.querySelector('[data-task]').dataset.task")=='1'
                assert await c.js("!!document.querySelector('.otree-form-errors')")
                await c.capture('choice_required_error')
            width=REPORT['viewports'][(index-1)%len(REPORT['viewports'])]
            await c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':844,'deviceScaleFactor':1,'mobile':width<640})
            await c.call('Emulation.setTouchEmulationEnabled',{'enabled':width<640})
            side='A' if index%2 else 'B'
            await asyncio.sleep(.1)
            await c.js("document.querySelector('[name=choice][value="+side+"]').closest('label').scrollIntoView({block:'center',behavior:'instant'})")
            await asyncio.sleep(.1)
            point=await c.js("(()=>{const b=document.querySelector('[name=choice][value="+side+"]').closest('label').getBoundingClientRect();return {x:b.x+b.width/2,y:b.y+b.height/2};})()")
            assert 0<point['x']<width and 0<point['y']<844,(width,point)
            if width<640:
                await c.call('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[point]})
                await c.call('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
            else:
                await c.call('Input.dispatchMouseEvent',dict(type='mousePressed',button='left',clickCount=1,**point))
                await c.call('Input.dispatchMouseEvent',dict(type='mouseReleased',button='left',clickCount=1,**point))
            for _ in range(20):
                if await c.js("document.querySelector('[name=choice][value="+side+"]').checked"):break
                await asyncio.sleep(.1)
            assert await c.js("document.querySelector('[name=choice][value="+side+"]').checked"),(index,width,point)
            REPORT['checks'].append({'choice':index,'width':width,'trusted_touch_or_mouse_selection':'passed'})
            if index==1:await c.capture('choice_selected')
        else:
            await c.choose('choice','A' if index%2 else 'B')
        await advance_choice(c,index)
    await c.wait('AttitudeSurvey')
    return displayed

async def complete_attitudes(c,code,score=0,dk=False,capture=False):
    await c.wait('AttitudeSurvey');await badge(c,code)
    assert await c.js("document.querySelector('h1').textContent")=='Part D — Nuclear & Economic Attitudes'
    assert await c.js("document.querySelector('[data-attitudes-version]').dataset.attitudesVersion")=='V3.0'
    assert await c.js("document.querySelectorAll('.survey-attitude-question').length")==5
    assert not await c.js("!!document.querySelector('.survey-attitudes input:checked')")
    assert await c.js("document.querySelector('.otree-btn-next').textContent")=='Submit and Continue'
    saved=native_row(code)
    assert saved['attitudes.1.player.attitudes_completed']=='0'
    assert all(saved['attitudes.1.player.'+f]=='' for f in ATTITUDE_FIELDS)
    if capture and not dk:
        await c.capture('attitudes_blank')
        await c.js("document.querySelector('form').submit()")
        for _ in range(80):
            if await c.js("document.querySelectorAll('.survey-attitude-question .form-control-errors').length===5"):break
            await asyncio.sleep(.1)
        assert await c.js("document.querySelectorAll('.survey-attitude-question .form-control-errors').length")==5
        await c.capture('attitudes_required_error')
        assert all(native_row(code)['attitudes.1.player.'+f]=='' for f in ATTITUDE_FIELDS)
        origin=await c.js('performance.timeOrigin');await c.call('Page.reload')
        for _ in range(100):
            try:
                if await c.js("document.readyState==='complete' && performance.timeOrigin!=="+json.dumps(origin)):break
            except RuntimeError:pass
            await asyncio.sleep(.1)
        else:raise AssertionError('Attitude reload did not complete')
        await c.wait('AttitudeSurvey')
        refreshed=native_row(code)
        for prefix in ('attitudes.','random_matrix.'):
            assert {k:v for k,v in saved.items() if k.startswith(prefix)}=={k:v for k,v in refreshed.items() if k.startswith(prefix)}
    values={field:99 if dk and field in ('nuclear_economic','nuclear_climate') else score for field in ATTITUDE_FIELDS}
    for field,value in values.items():await c.choose(field,str(value))
    if capture and not dk:
        # Native keyboard navigation selects neutral from the preceding category.
        await c.choose('nuclear_support','-1')
        await c.js("document.querySelector('[name=nuclear_support][value=\"-1\"]').focus()")
        await c.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
        await c.call('Input.dispatchKeyEvent',{'type':'keyUp','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
        assert await c.js("document.querySelector('[name=nuclear_support][value=\"0\"]').checked")
        assert await c.js("getComputedStyle(document.querySelector('[name=nuclear_support]:checked').closest('label')).outlineStyle")=='solid'
        REPORT['checks'].append({'attitude_keyboard_and_visible_focus':'passed'})
    # Selecting in the browser is not a saved response until successful submission.
    assert all(native_row(code)['attitudes.1.player.'+f]=='' for f in ATTITUDE_FIELDS)
    if capture:await c.capture('attitudes_dk' if dk else 'attitudes_neutral')
    await c.next('Completion');await badge(c,code)
    row=native_row(code)
    assert row['attitudes.1.player.attitudes_completed']=='1'
    assert all(row['attitudes.1.player.'+f]==str(v) for f,v in values.items())
    assert {k:v for k,v in saved.items() if k.startswith('random_matrix.')}=={k:v for k,v in row.items() if k.startswith('random_matrix.')}
    REPORT['checks'].append({'attitude_submit_and_native_values':'passed','participant_code':code,'raw_responses':values})

async def main():
    with urllib.request.urlopen(DEBUG_BASE + '/json',timeout=15) as response:tabs=json.load(response)
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
        await c.next('ScenarioInstructions',double=True);await instructions(c,code,capture=True);await badge(c,code)
        before=await c.js("document.querySelector('.survey-housing-grid').innerText")
        await c.call('Page.reload');await c.wait('Choice');await badge(c,code)
        assert before==await c.js("document.querySelector('.survey-housing-grid').innerText")
        displayed = await complete_choices(c, capture=True,code=code)
        await complete_attitudes(c,code,capture=True)
        await c.capture('completion')
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
                    await c.next('ScenarioInstructions')
                else:
                    await fill(c,rent='',income='0',pays=False)
                    await c.next('ScenarioInstructions')
                await instructions(c,casecode)
                await badge(c,casecode)
                await complete_choices(c)
                await complete_attitudes(c,casecode,score=-2 if case=='javascript_disabled' else 2,
                                          dk=case=='cookie_blocked',capture=case=='cookie_blocked')
            REPORT['checks'].append({case:'passed'})
            if case=='javascript_disabled':await c.call('Emulation.setScriptExecutionDisabled',{'value':False})
        rows=list(csv.DictReader(io.StringIO(http('/ExportWide'))))
        row=next(r for r in rows if r['participant.code']==code)
        assert row['household.1.player.income_sek']=='25000'
        assert row['household.1.player.monthly_rent_sek']=='6500'
        assert row['household.1.player.previous_power_plant_exposure']=='2'
        assert row['attitudes.1.player.nuclear_energy_support']==''
        assert row['participant.finished']=='1'
        assert row['random_matrix.1.player.tasks_answered']=='4'
        for index, task in enumerate(displayed, 1):
            prefix=f'random_matrix.{index}.player.'
            assert row[prefix+'choice_set_id']==task['set']
            assert row[prefix+'facility_type']==row[prefix+'A_facility_type']==row[prefix+'B_facility_type']==task['facility']
            choice='A' if index%2 else 'B'
            assert row[prefix+'choice']==choice
            assert row[prefix+'chosen_distance_km']==str(task[choice]['distance_km'])
            assert row[prefix+'chosen_rent_sek']==str(task[choice]['rent_sek_month'])
            assert row[prefix+'chosen_facility_type']==task['facility']
            assert row[prefix+'chosen_far']==str(int(task[choice]['distance_km']==50))
            assert row[prefix+'task_completed']=='1'
            assert row[prefix+'A_size_m2']==row[prefix+'B_size_m2']==''
            assert row[prefix+'wording_version']=='V2.4'
            for side in ('A','B'):
                for field,value in task[side].items():
                    assert row[prefix+side+'_'+field]==str(value)
        last=next(r for r in rows if r['participant.code']==casecode)
        assert last['household.1.player.monthly_rent_sek']==last['household.1.player.income_sek']==''
        assert last['household.1.player.income_not_disclosed']=='1'
        REPORT['checks'].append({'browser_csv_join_and_values':'passed','displayed_choices_match_csv':'passed'})
        assert sorted(t['facility'] for t in displayed)==['nuclear','nuclear','oil_fired','oil_fired']
        REPORT['checks'].append({'nuclear_and_oil_fired_contexts_match_native_csv':'passed','two_tasks_per_facility':'passed'})
        REPORT['displayed_tasks']=displayed
        # Deliberately leave one participant after two submissions, on Choice 3.
        partialcode=await new_participant();await c.start(partialcode)
        await c.choose('adult_confirmed','True');await c.next('Introduction');await c.next('VoluntaryParticipation')
        await c.choose('willing_to_participate','True');await c.choose('cookies_allowed','False');await c.next('HouseholdInformation')
        await fill(c);await c.next('ScenarioInstructions');await instructions(c,partialcode)
        for index,choice in [(1,'B'),(2,'A')]:
            await c.choose('choice',choice);await advance_choice(c,index)
        # A different participant finishes DCE, selects attitude radios, then leaves without submitting.
        dropoutcode=await new_participant();await c.start(dropoutcode)
        await c.choose('adult_confirmed','True');await c.next('Introduction');await c.next('VoluntaryParticipation')
        await c.choose('willing_to_participate','True');await c.choose('cookies_allowed','False');await c.next('HouseholdInformation')
        await fill(c);await c.next('ScenarioInstructions');await instructions(c,dropoutcode)
        await complete_choices(c)
        for field in ATTITUDE_FIELDS:await c.choose(field,'0')
        dropout=native_row(dropoutcode)
        assert dropout['random_matrix.1.player.module_completed']=='1'
        assert dropout['attitudes.1.player.attitudes_completed']=='0'
        assert all(dropout['attitudes.1.player.'+f]=='' for f in ATTITUDE_FIELDS)
        native=http('/ExportWide')
        page_times=http('/ExportPageTimes')
        partial=next(r for r in csv.DictReader(io.StringIO(native)) if r['participant.code']==partialcode)
        assert partial['random_matrix.1.player.tasks_answered']=='2'
        assert partial['random_matrix.1.player.module_completed']=='0'
        assert partial['random_matrix.3.player.choice']==partial['random_matrix.4.player.choice']==''
        from dce_modules import exports, matrix, facility_design
        native_rows=list(csv.DictReader(io.StringIO(native)))
        for exported_person in native_rows:
            for index in range(1,5):
                prefix=f'random_matrix.{index}.player.'
                assert exported_person[prefix+'wording_version']=='V2.4'
                if exported_person[prefix+'choice_set_id']:
                    assert exported_person[prefix+'design_version']=='V2.4'
                    assert exported_person[prefix+'numeric_matrix_hash']==matrix.DESIGN_HASH
                    assert exported_person[prefix+'treatment_design_version']=='V2.4'
                    assert exported_person[prefix+'design_hash']==facility_design.DESIGN_HASH
        export_dir=ROOT/'data/synthetic'/('v2_4_browser_'+str(time.time_ns()))
        export_dir.mkdir()
        (export_dir/'all_apps_wide.csv').write_text(native)
        (export_dir/'page_times.csv').write_text(page_times)
        exports.write_formats(exports.records_from_native(csv.DictReader(io.StringIO(native))),export_dir)
        import sys
        sys.path.insert(0,str(ROOT))
        from scripts.export_dce import attitude_exports
        from analysis.merge_attitudes import merge_datasets, read_csv
        attitude_rows=attitude_exports.records_from_native(native_rows)
        exports.write_csv(export_dir/'attitudes_wide.csv',attitude_rows,attitude_exports.EXPORT_FIELDS)
        merged,audit=merge_datasets(read_csv(export_dir/'all_apps_wide.csv'),read_csv(export_dir/'dce_difference.csv'),read_csv(export_dir/'attitudes_wide.csv'))
        merged.to_csv(export_dir/'analysis_merged.csv',index=False,mode='x',na_rep='')
        (export_dir/'merge_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
        assert len(merged)==4*len(native_rows)
        assert merged[merged.participant_code==dropoutcode][attitude_exports.SCORE_FIELDS].isna().all().all()
        REPORT['checks'].append({'attitude_left_merge_and_dce_dropout_preservation':'passed','analysis_rows':len(merged)})
        timing_rows=list(csv.DictReader(io.StringIO(page_times)))
        for person in native_rows:
            events=[t for t in timing_rows if t['participant_code']==person['participant.code'] and t['app_name']=='random_matrix']
            expected=[] if person['participant.eligible']=='0' else ['ScenarioInstructions']+['Choice']*int(person['random_matrix.1.player.tasks_answered'])
            assert [t['page_name'] for t in events]==expected
        REPORT['checks'].append({'one_instruction_timing_event_separate_from_choice_events':'passed'})
        for filename in ('dce_tasks.csv','dce_wide.csv','dce_long.csv','dce_difference.csv'):
            with (export_dir/filename).open() as f:
                assert all(r['wording_version']=='V2.4' for r in csv.DictReader(f)),filename
        REPORT['session_codes']=sorted({r['session.code'] for r in native_rows})
        REPORT['design_hash']=facility_design.DESIGN_HASH
        REPORT['numeric_matrix_hash']=matrix.DESIGN_HASH
        REPORT['participant_count']=len(native_rows)
        REPORT['exports']=str(export_dir.relative_to(ROOT))
        REPORT['checks'].append({'partial_pilot_two_answers':'passed','displayed_attributes_match_native_csv':'passed','native_and_all_analysis_wording_versions':'passed','design_version_and_hash':'passed'})
        errors=[e for e in c.events if e.get('method')=='Runtime.exceptionThrown']
        REPORT['javascript_uncaught_errors']=errors
        assert not errors,errors
    (OUT/'checks.json').write_text(json.dumps(REPORT,indent=2))
    print('PASS:',len(REPORT['screenshots']),'real Chrome screenshots; V2.4 DCE, preserved V3 attitudes, responsive UI and CSV checks passed.',OUT)

if __name__ == '__main__':
    # Bound the entire run as well as individual network waits; never retry a failed run forever.
    asyncio.run(asyncio.wait_for(main(),timeout=300))
