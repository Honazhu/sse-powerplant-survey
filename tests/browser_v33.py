"""Optional local Chrome CDP acceptance test; see docs/UI_TESTING.md. Synthetic only."""
import asyncio,base64,csv,io,json,time,urllib.request,os,sys
from pathlib import Path
import websockets

BASE=os.environ.get('SURVEY_TEST_BASE', 'http://127.0.0.1:8000')
DEBUG_BASE=os.environ.get('SURVEY_CHROME_DEBUG', 'http://127.0.0.1:9227')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT / 'docs/ui_previews' / ('v3_3_1_' + str(time.time_ns()))
OUT.mkdir(parents=True,exist_ok=True)
VIEWPORTS=[int(width) for width in os.environ.get('SURVEY_TEST_VIEWPORTS','375,390,430,1440').split(',')]
assert VIEWPORTS and all(320 <= width <= 2560 for width in VIEWPORTS)
SCREENSHOT_PAGES=set(filter(None,os.environ.get('SURVEY_SCREENSHOT_PAGES','').split(',')))
REPORT={'wording_version':'V2.4','design_version':'V2.4','numeric_matrix_version':'V2.4','browser':'Installed Chrome headless; mobile viewport/touch emulation, not physical iPhone Safari','viewports':VIEWPORTS,'checks':[],'screenshots':[]}
REPORT['attitudes_version']='V3.3'
REPORT['survey_flow_version']='V3.3'
REPORT['ui_patch']='V3.3.1'
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
                const boxes=s=>Array.from(document.querySelectorAll(s)).filter(e=>e.getClientRects().length).map(e=>({width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}));
                const housing=Array.from(document.querySelectorAll('.survey-housing-card')).map(e=>({x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y}));
                return {width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
                formCount:document.querySelectorAll('form').length,h1:document.querySelector('h1').textContent,
                targets:boxes('.survey-option,.survey-rating,.otree-btn-next,.survey-copy-id,.survey-slider input[type=range],.survey-slider-labels button'),housing,
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
        if await c.js("document.readyState==='complete' && (location.pathname.includes('/HouseholdInformation/') || document.querySelector('[data-task]')?.dataset.task==="+json.dumps(str(index+1))+")"):
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
                await raw_submit(c)
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
    await c.wait('HouseholdInformation')
    return displayed


async def reload_page(c, page):
    origin=await c.js('performance.timeOrigin')
    await c.call('Page.reload')
    for _ in range(100):
        try:
            if await c.js("document.readyState==='complete' && performance.timeOrigin!=="+json.dumps(origin)):break
        except RuntimeError:pass
        await asyncio.sleep(.1)
    else:raise AssertionError('Reload did not finish')
    await c.wait(page)

async def raw_submit(c):
    origin=await c.js('performance.timeOrigin')
    await c.js('document.querySelector("form").submit()')
    for _ in range(100):
        try:
            if await c.js("document.readyState==='complete' && performance.timeOrigin!=="+json.dumps(origin)):return
        except RuntimeError:pass
        await asyncio.sleep(.1)
    raise AssertionError('Raw submission did not finish navigating')

async def viewport(c,width):
    await c.call('Emulation.setDeviceMetricsOverride',{'width':width,'height':900,'deviceScaleFactor':1,'mobile':width<640})
    await c.call('Emulation.setTouchEmulationEnabled',{'enabled':width<640})

async def slider_select(c,field,score,drag=False):
    selector='[data-field="'+field+'"] input[type="range"]'
    await c.js('document.querySelector('+json.dumps(selector)+').scrollIntoView({block:"center",behavior:"instant"})')
    await asyncio.sleep(.08)
    box=await c.js('(()=>{const e=document.querySelector('+json.dumps(selector)+');const b=e.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height,value:Number(e.value),mobile:innerWidth<640};})()')
    point=lambda v:dict(x=box['x']+14+(box['width']-28)*(v+2)/4,y=box['y']+box['height']/2)
    start=point(box['value'] if drag else score);end=point(score)
    if box['mobile']:
        await c.call('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[start]})
        if drag:
            for i in range(1,9):
                await c.call('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[dict(x=start['x']+(end['x']-start['x'])*i/8,y=end['y'])]})
                await asyncio.sleep(.015)
        await c.call('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    else:
        await c.call('Input.dispatchMouseEvent',dict(type='mousePressed',button='left',clickCount=1,**start))
        if drag:
            for i in range(1,9):
                await c.call('Input.dispatchMouseEvent',dict(type='mouseMoved',button='left',buttons=1,x=start['x']+(end['x']-start['x'])*i/8,y=end['y']))
        await c.call('Input.dispatchMouseEvent',dict(type='mouseReleased',button='left',clickCount=1,**end))
    await asyncio.sleep(.05)
    actual=await c.js('new FormData(document.querySelector("form")).get('+json.dumps(field)+')')
    assert actual==str(score),(field,score,actual,box)

async def wait_attitude_errors(c,count):
    for _ in range(100):
        try:
            if await c.js('document.querySelectorAll(".survey-attitude-question .form-control-errors").length=== '+str(count)):return
        except RuntimeError:pass
        await asyncio.sleep(.1)
    raise AssertionError(await c.js('document.body.innerText'))

async def slider_state(c,field):
    return await c.js('''(() => {
        const q=document.querySelector('[data-field="'+FIELD+'"]');
        const slider=q.querySelector('[data-slider]'), range=slider.querySelector('input[type=range]');
        const style=getComputedStyle(range);
        return {answered:slider.dataset.answered, value:range.value,
            formValues:new FormData(document.querySelector('form')).getAll(FIELD),
            fill:style.getPropertyValue('--slider-thumb-fill').trim(),
            border:style.getPropertyValue('--slider-thumb-border').trim(),
            hintHidden:slider.querySelector('[data-slider-hint]').hidden,
            hint:slider.querySelector('[data-slider-hint]').textContent,
            status:slider.querySelector('[role=status]').textContent,
            valueText:range.getAttribute('aria-valuetext'),
            pressed:Array.from(slider.querySelectorAll('[aria-pressed=true]')).map(e=>e.dataset.score),
            rangeHasName:range.hasAttribute('name')};
    })()'''.replace('FIELD',json.dumps(field)))

async def assert_unanswered(c,fields):
    for field in fields:
        state=await slider_state(c,field)
        assert state['answered']=='false' and state['value']=='0',state
        assert state['formValues']==[] and state['pressed']==[] and not state['rangeHasName'],state
        assert state['fill']=='#ffffff' and state['border']=='#7c8982',state
        assert state['status']==state['valueText']=='Not answered' and not state['hintHidden'],state
        assert state['hint']=='Drag the circle or tap a position to answer.'

async def assert_selected(c,field,score):
    state=await slider_state(c,field)
    label=['Strongly disagree','Slightly disagree','Neutral','Slightly agree','Strongly agree'][score+2]
    assert state['answered']=='true' and state['value']==str(score),state
    assert state['formValues']==[str(score)] and state['pressed']==[str(score)],state
    assert state['fill']=='#305950' and state['border']=='#ffffff',state
    assert state['hintHidden'] and state['status']=='Selected: '+label and state['valueText']==label,state

async def label_select(c,field,score):
    selector=f'[data-field="{field}"] button[data-score="{score}"]'
    await c.js('document.querySelector('+json.dumps(selector)+').scrollIntoView({block:"center",behavior:"instant"})')
    await asyncio.sleep(.05)
    point=await c.js('''(() => {const e=document.querySelector(SELECTOR), b=e.getBoundingClientRect();
        return {x:b.x+b.width/2,y:b.y+b.height/2,width:b.width,height:b.height,mobile:innerWidth<640,type:e.type,name:e.name};})()'''.replace('SELECTOR',json.dumps(selector)))
    assert point['width']>=44 and point['height']>=44 and point['type']=='button' and point['name']=='',point
    origin=await c.js('performance.timeOrigin')
    coords=dict(x=point['x'],y=point['y'])
    if point['mobile']:
        await c.call('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[coords]})
        await c.call('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    else:
        await c.call('Input.dispatchMouseEvent',dict(type='mousePressed',button='left',clickCount=1,**coords))
        await c.call('Input.dispatchMouseEvent',dict(type='mouseReleased',button='left',clickCount=1,**coords))
    await asyncio.sleep(.05)
    await assert_selected(c,field,score)
    assert await c.js('performance.timeOrigin')==origin  # Label must never submit.

async def eligibility(c,code,cookies='False'):
    await c.start(code)
    assert not await c.js("!!document.querySelector('#survey-reference-code')")
    await c.choose('adult_confirmed','True');await c.next('Introduction')
    assert not await c.js("!!document.querySelector('#survey-reference-code')")
    await c.next('VoluntaryParticipation')
    assert not await c.js("!!document.querySelector('#survey-reference-code')")
    await c.choose('willing_to_participate','True');await c.choose('cookies_allowed',cookies)
    await c.next('ScenarioInstructions');await badge(c,code)
    row=native_row(code)
    assert row['participant.household_complete']=='0'
    assert all(row['household.1.player.'+f]=='' for f in ['age_group','rent_status','monthly_rent_sek','income_thousand_sek','income_sek','income_not_disclosed','previous_power_plant_exposure'])
    return row

async def main():
    with urllib.request.urlopen(DEBUG_BASE+'/json',timeout=15) as response:tabs=json.load(response)
    target=next(t for t in tabs if t['type']=='page')
    async with websockets.connect(target['webSocketDebuggerUrl'],max_size=24*1024*1024) as ws:
        c=CDP(ws);await c.call('Page.enable');await c.call('Runtime.enable');await c.call('Network.enable')
        code=await new_participant();await eligibility(c,code,cookies='True')
        await c.capture('reference_first_visible')
        assert await c.js("document.querySelector('#survey-reference-code').getBoundingClientRect().top") < 400
        await c.call('Emulation.setFocusEmulationEnabled',{'enabled':True});await c.call('Page.bringToFront')
        await c.call('Browser.grantPermissions',{'origin':BASE,'permissions':['clipboardReadWrite','clipboardSanitizedWrite']})
        await c.js("document.querySelector('[data-copy-reference]').click()")
        await asyncio.sleep(.15)
        assert await c.js('navigator.clipboard.readText()')==code
        await c.js("navigator.clipboard.writeText=()=>Promise.reject(new Error('synthetic unsupported'));document.querySelector('[data-copy-reference]').click()")
        await asyncio.sleep(.1)
        assert await c.js('getSelection().toString()')==code
        await instructions(c,code,capture=True)
        displayed=await complete_choices(c,capture=True,code=code)
        await badge(c,code);await c.capture('household_after_dce')
        assert native_row(code)['random_matrix.1.player.module_completed']=='1'
        assert native_row(code)['participant.household_complete']=='0'
        await raw_submit(c)
        for _ in range(100):
            if await c.js("!!document.querySelector('.otree-form-errors')"):break
            await asyncio.sleep(.1)
        await c.wait('HouseholdInformation')
        await fill(c,rent='12.5',income='-1');await raw_submit(c);await wait_error(c)
        await fill(c);await c.next('AttitudeSurvey');await badge(c,code)
        assert await c.js('document.querySelector("h1").textContent')=='Part D — Attitudes'
        fields=['nuclear_economic','housing_cost','nuclear_support','nuclear_climate','nuclear_risk']
        statements=["Nuclear power has a positive effect on Sweden's economy.",
            'Keeping my monthly housing costs low is a high priority when deciding where to live.',
            'I support the use of nuclear power to generate electricity in Sweden.',
            'Nuclear power helps reduce greenhouse gas emissions.',
            'I would be concerned about safety risks if I lived near an operating nuclear power plant.']
        legends=await c.js('Array.from(document.querySelectorAll(".survey-attitude-question legend")).map(e=>e.textContent)')
        assert legends==[f'Q{i}. {s}' for i,s in enumerate(statements,1)]
        assert await c.js('Array.from(document.querySelectorAll(".survey-attitude-question")).map(e=>e.dataset.field)')==fields
        assert await c.js('document.querySelectorAll(".survey-slider input[type=range]:not(:disabled)").length')==5
        assert not await c.js('!!document.querySelector(".survey-attitudes input:checked")')
        assert not await c.js('new FormData(document.querySelector("form")).has("nuclear_economic")')
        assert not await c.js('document.body.innerText.includes("I don\'t know")')
        await assert_unanswered(c,fields)
        await c.capture('attitudes_blank')
        # Resizing and focusing every range/label cannot mark any question answered.
        for width in VIEWPORTS:
            await viewport(c,width)
            await c.js('document.querySelectorAll(".survey-slider input,.survey-slider-labels button").forEach(e=>e.focus())')
            await assert_unanswered(c,fields)
        ax=await c.call('Accessibility.getFullAXTree')
        sliders=[n for n in ax['nodes'] if n.get('role',{}).get('value')=='slider']
        assert len(sliders)==5 and {n['name']['value'] for n in sliders}==set(legends)
        REPORT['checks'].append({'five_ghosts_focus_resize_no_answers_and_accessible_slider_names':'passed'})
        # Focus alone must never count as an answer; ordinary submit is blocked.
        await c.js('document.querySelector("input[type=range]").focus();document.querySelector(".otree-btn-next").click()')
        await asyncio.sleep(.15)
        assert await c.js('document.querySelectorAll("[data-slider-error]:not([hidden])").length')==5
        assert not await c.js('new FormData(document.querySelector("form")).has("nuclear_economic")')
        # Bypass client validation: server rejects all five missing values.
        await raw_submit(c);await wait_attitude_errors(c,5)
        await c.capture('attitudes_required_error')
        await reload_page(c,'AttitudeSurvey')
        for width in VIEWPORTS:
            await reload_page(c,'AttitudeSurvey')
            await viewport(c,width)
            await assert_unanswered(c,fields)
            # Untouched neutral via real pointer tap, followed by every position.
            await slider_select(c,'nuclear_economic',0)
            await assert_selected(c,'nuclear_economic',0)
            await assert_unanswered(c,fields[1:])
            for score in [-2,-1,0,1,2]:
                await slider_select(c,'nuclear_economic',score,drag=True)
                await assert_selected(c,'nuclear_economic',score)
            await slider_select(c,'housing_cost',-2)
            await slider_select(c,'housing_cost',2)
            for field in fields:
                for score in [-2,-1,0,1,2]:await label_select(c,field,score)
            REPORT['checks'].append({'width':width,'native_range_drag_all_five_positions':True,'track_tap':True,'input':'CDP touch' if width<640 else 'CDP mouse'})
            REPORT['checks'].append({'width':width,'all_five_labels_on_all_five_questions':'passed','one_radio_per_field_no_submit':True})
        # A fresh GET intentionally discards unsubmitted browser choices.
        assert all(native_row(code)['attitudes.1.player.'+f]=='' for f in fields)
        await reload_page(c,'AttitudeSurvey')
        assert not await c.js('!!document.querySelector(".survey-attitudes input:checked")')
        await viewport(c,1440)
        for field in fields:await label_select(c,field,0)
        await c.capture('attitudes_neutral_selected')
        await reload_page(c,'AttitudeSurvey')
        await assert_unanswered(c,fields)
        await viewport(c,1440)
        for field,score in zip(fields[:4],[-2,-1,0,1]):await slider_select(c,field,score)
        await raw_submit(c);await wait_attitude_errors(c,1)
        values=await c.js('Object.fromEntries(new FormData(document.querySelector("form")))')
        assert [values[f] for f in fields[:4]]==['-2','-1','0','1'] and fields[4] not in values
        await c.capture('attitudes_partial_error')
        await viewport(c,1440)
        await slider_select(c,'nuclear_risk',2)
        await slider_select(c,'nuclear_support',-1)
        await c.js('document.querySelector("[data-field=nuclear_support] input[type=range]").focus()')
        await c.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
        await c.call('Input.dispatchKeyEvent',{'type':'keyUp','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
        assert await c.js('new FormData(document.querySelector("form")).get("nuclear_support")')=='0'
        assert await c.js('getComputedStyle(document.activeElement).outlineStyle')=='solid'
        assert await c.js('document.activeElement.getAttribute("aria-valuetext")')=='Neutral'
        # A focused label supports keyboard activation without submitting.
        await c.js("document.querySelector('[data-field=nuclear_support]').querySelectorAll('button')[2].focus()")
        await c.call('Input.dispatchKeyEvent',{'type':'keyDown','key':'Enter','code':'Enter','windowsVirtualKeyCode':13})
        await c.call('Input.dispatchKeyEvent',{'type':'keyUp','key':'Enter','code':'Enter','windowsVirtualKeyCode':13})
        await assert_selected(c,'nuclear_support',0)
        assert await c.js('location.pathname.includes("/AttitudeSurvey/")')
        for field in fields:
            assert await c.js('new FormData(document.querySelector("form")).getAll('+json.dumps(field)+').length')==1
        await c.capture('attitudes_selected')
        await c.next('Completion');await badge(c,code);await c.capture('completion')
        final=native_row(code)
        assert [final['attitudes.1.player.'+f] for f in fields]==['-2','-1','0','1','2']
        assert final['attitudes.1.player.attitudes_version']=='V3.3'
        assert final['eligibility.1.player.survey_flow_version']=='V3.3'
        assert final['household.1.player.income_sek']=='25000'
        for index,task in enumerate(displayed,1):
            prefix=f'random_matrix.{index}.player.'
            assert final[prefix+'choice_set_id']==task['set']
            for side in 'AB':
                for field,value in task[side].items():assert final[prefix+side+'_'+field]==str(value)
        REPORT['checks'].append({'adult_flow_copy_id_server_validation_keyboard_refresh_mapping':'passed'})
        # Exclusions, cookie refusal, blocked cookies, and complete no-JS fallback.
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
                assert not await c.js("!!document.querySelector('#survey-reference-code,.otree-btn-next')")
                await c.call('Page.navigate',{'url':BASE+'/p/'+casecode+'/household/HouseholdInformation/5'})
                await c.wait('Exit')
            else:
                if case=='cookie_blocked':await c.js("Object.defineProperty(document,'cookie',{configurable:true,get(){throw new Error('synthetic blocked')},set(){throw new Error('synthetic blocked')}})")
                await c.choose('cookies_allowed','False' if case=='cookie_refused' else 'True')
                await c.next('ScenarioInstructions');await instructions(c,casecode);await complete_choices(c)
                await fill(c,rent='bad' if case=='javascript_disabled' else '',income='bad' if case=='javascript_disabled' else '0',refuse=case=='javascript_disabled',pays=False)
                await c.next('AttitudeSurvey')
                if case=='javascript_disabled':
                    assert await c.js('document.querySelectorAll("[data-slider]:not([hidden])").length')==0
                    for field in fields:await c.choose(field,'-2')
                else:
                    # Persist a complete explicit-Neutral submission via labels.
                    for field in fields:await label_select(c,field,0 if case=='cookie_refused' else 2)
                await c.next('Completion');await badge(c,casecode)
                expected='-2' if case=='javascript_disabled' else '0' if case=='cookie_refused' else '2'
                assert all(native_row(casecode)['attitudes.1.player.'+f]==expected for f in fields)
            if case=='javascript_disabled':await c.call('Emulation.setScriptExecutionDisabled',{'value':False})
            REPORT['checks'].append({case:'passed'})
        # All dropout lengths, with no fabricated Household answers.
        dropout_codes={}
        for count in [1,2,3,4]:
            drop=await new_participant();await eligibility(c,drop);await instructions(c,drop)
            for i in range(1,count+1):await c.choose('choice','A');await advance_choice(c,i)
            dropout_codes[drop]=count
        # Household completed, attitude selections unsubmitted remain NULL.
        drop=await new_participant();await eligibility(c,drop);await instructions(c,drop);await complete_choices(c)
        await fill(c);await c.next('AttitudeSurvey');await slider_select(c,'nuclear_economic',0)
        assert native_row(drop)['attitudes.1.player.nuclear_economic']==''
        from scripts.export_dce import exports as d, attitude_exports as a
        from analysis.merge_attitudes import merge_datasets,read_csv
        import pandas as pd
        native_text=http('/ExportWide');rows=list(csv.DictReader(io.StringIO(native_text)))
        export_dir=ROOT/'data/synthetic'/('v3_3_1_browser_'+str(time.time_ns()));export_dir.mkdir(parents=True)
        (export_dir/'README.md').write_text('Invented V3.3.1 UI patch browser Pilot records only. Questionnaire/flow remain V3.3. No real respondents.\n')
        (export_dir/'all_apps_wide.csv').write_text(native_text)
        records=list(d.records_from_native(rows));d.write_formats(records,export_dir)
        arows=a.records_from_native(rows);d.write_csv(export_dir/'attitudes_wide.csv',arows,a.EXPORT_FIELDS)
        merged,audit=merge_datasets(pd.DataFrame(rows),read_csv(export_dir/'dce_difference.csv'),read_csv(export_dir/'attitudes_wide.csv'))
        assert len(merged)==len(rows)*4 and len(arows)==len(rows)
        for drop,count in dropout_codes.items():
            subset=merged[merged.participant_code==drop]
            assert len(subset)==4 and subset.chose_A.notna().sum()==count
            assert subset.household_completed.eq(0).all() and subset.attitudes_completed.eq(0).all()
            assert subset.dce_completed.eq(int(count==4)).all()
            assert subset[a.SCORE_FIELDS].isna().all().all()
            assert subset[['age_group','monthly_rent_sek','income_sek']].replace('',None).isna().all().all()
        merged.to_csv(export_dir/'analysis_merged.csv',index=False,na_rep='')
        import hashlib
        audit['input_sha256']={name:hashlib.sha256((export_dir/name).read_bytes()).hexdigest() for name in ['all_apps_wide.csv','dce_difference.csv','attitudes_wide.csv']}
        (export_dir/'merge_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
        REPORT.update(participant_count=len(rows),exports=str(export_dir.relative_to(ROOT)),displayed_tasks=displayed,
            design_hash=final['random_matrix.1.player.design_hash'],csv_rows={'native':len(rows),'wide':len(rows),'tasks':len(records),'long':len(records)*2,'difference':len(records),'attitudes':len(arows),'merged':len(merged)})
        REPORT['checks'].append({'native_all_formats_and_dropout_1_2_3_4_choices':'passed'})
        REPORT['javascript_uncaught_errors']=[e for e in c.events if e.get('method')=='Runtime.exceptionThrown']
        assert not REPORT['javascript_uncaught_errors']
    (OUT/'checks.json').write_text(json.dumps(REPORT,indent=2)+'\n')
    print('PASS:',len(REPORT['screenshots']),'screenshots;',len(REPORT['checks']),'checks;',OUT)

if __name__=='__main__':asyncio.run(asyncio.wait_for(main(),timeout=510))
