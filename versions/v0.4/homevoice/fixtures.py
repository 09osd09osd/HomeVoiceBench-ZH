import copy
START='2026-12-01T18:00:00+08:00'
ROOMS=[{'id':'living','name':'客厅'},{'id':'bedroom','name':'卧室'},{'id':'study','name':'书房'},{'id':'kitchen','name':'厨房'}]
def capability(field,lo=None,hi=None,values=None,unit=None):return {'field':field,'allowed_values':values,'minimum':lo,'maximum':hi,'unit':unit}
def fixture(case_id,index):
    devices=[]
    def add(id,name,type,room,extra,caps):
        state={k:None for k in ['power','brightness_pct','color_temperature_k','target_temperature_c','mode','fan_speed','opening_pct','volume_pct','cleaning_status']};state['target_room_ids']=[];state.update(power=False);state.update(extra)
        devices.append({'id':id,'name':name,'type':type,'room_id':room,'online':True,'state':state,'capabilities':[capability('power',values=[True,False])]+caps})
    for room,label in [('living','客厅'),('bedroom','卧室'),('study','书房')]:add('light_'+room,label+'灯','light',room,{'brightness_pct':20+index%6*10,'color_temperature_k':4000},[capability('brightness_pct',0,100,unit='percent'),capability('color_temperature_k',2700,6500,unit='K')])
    add('ac_living','客厅空调','air_conditioner','living',{'target_temperature_c':26,'mode':'cool','fan_speed':0},[capability('target_temperature_c',16,30,unit='C'),capability('mode',values=['cool','heat','dry','fan','auto']),capability('fan_speed',0,3)])
    add('curtain_bedroom','卧室窗帘','curtain','bedroom',{'opening_pct':50},[capability('opening_pct',0,100,unit='percent')])
    add('fan_study','书房风扇','fan','study',{'fan_speed':1},[capability('fan_speed',1,3)])
    add('purifier_living','客厅净化器','purifier','living',{'mode':'auto','fan_speed':0},[capability('mode',values=['auto','sleep','manual']),capability('fan_speed',0,3)])
    for room,typ,label in [('living','speaker','客厅音箱'),('bedroom','speaker','卧室音箱'),('living','tv','客厅电视')]:add(typ+'_'+room,label,typ,room,{'volume_pct':30},[capability('volume_pct',0,100,unit='percent')])
    add('vacuum','扫地机器人','vacuum','living',{'cleaning_status':'idle'},[capability('target_room_ids'),capability('cleaning_action',values=['start','pause','resume','return_home'])])
    sensors=[]
    for ri,room in enumerate(ROOMS):
        for metric,val,unit in [('temperature_c',22+(index+ri)%7,'C'),('humidity_pct',35+(index*3+ri)%35,'percent'),('illuminance_lux',80+(index*37+ri*140)%700,'lux'),('co2_ppm',450+(index*71+ri*170)%1200,'ppm'),('presence',(index+ri)%2==0,'boolean')]:
            sensors.append({'id':f'sensor_{room["id"]}_{metric}','room_id':room['id'],'metric':metric,'value':val,'unit':unit,'observed_at':START,'online':True})
    permissions=[{'id':f'allow_{r}','actor_role':'adult_member','resource_type':r,'resource_ids':['*'],'actions':['*'],'decision':'allow','owner_only':r in ('schedule','playback','task')} for r in ['home','device','sensor','schedule','media','playback','task']]
    media=[{'id':f'media_{i}','title':title,'type':typ,'duration_s':duration,'source':'fixture','asset_id':f'simulated_media_{i}'} for i,(title,typ,duration) in enumerate([('雨后散步','music',180),('安静钢琴','music',240),('小熊找月亮','story',420),('星空小知识','podcast',600)],1)]
    state={'clock':{'start_at':START,'current_at':START,'timezone':'Asia/Taipei','advance_after_user_turn_ms':1000,'advance_after_tool_call_ms':100},'home':{'home_id':'synthetic_home','name':'安和之家','rooms':copy.deepcopy(ROOMS),'public_preferences':[{'key':'睡前音量','value':'20%'},{'key':'阅读色温','value':'4000K'}]},'devices':devices,'sensors':sensors,'schedules':[],'media_catalog':media,'playbacks':[],'tasks':[]}
    return {'initial_state':state,'permissions':permissions,'faults':[],'external_events':[],'id_prefix':case_id}
def when(at=None,mode='once',local_time=None,weekdays=None):return {'mode':mode,'at':at,'local_time':local_time,'weekdays':weekdays or [],'timezone':'Asia/Taipei'}
def payload(message=None,device=None,actions=None):return {'message':message,'target_device_id':device,'actions':actions or []}
def schedule(id,message,at,owner='user_1'):
    return {'id':id,'owner_id':owner,'kind':'reminder','when':when(at),'payload':payload(message),'status':'active','created_at':START,'updated_at':START,'last_triggered_at':None}
