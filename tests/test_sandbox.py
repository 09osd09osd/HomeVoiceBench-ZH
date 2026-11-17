import copy,unittest
from homevoice.sandbox import Sandbox,TOOLS
from homevoice.fixtures import fixture,when,payload,schedule
from homevoice.blueprints import blueprint
from homevoice.catalog import SCENES
from homevoice.grading import grade_rules
ACTOR={'id':'user_1','name':'小林','role':'adult_member'}
class SandboxTests(unittest.TestCase):
    def setUp(self):self.env=fixture('UNIT',1);self.s=Sandbox(self.env,ACTOR)
    def test_16_tools_and_read_queries(self):
        self.assertEqual(len(TOOLS),16)
        for tool,args in [('home_get',{}),('device_list',{}),('clock_get',{}),('policy_get',{'resource_type':'device','resource_id':'light_living','action':'device_set'}),('device_get',{'device_id':'light_living'}),('sensor_read',{'room_id':'living','metrics':['temperature_c']}),('schedule_list',{}),('media_search',{'query':'安静'})]:self.assertTrue(self.s.call(tool,args)['ok'])
    def test_device_atomicity_and_capabilities(self):
        before=copy.deepcopy(self.s.state['devices'])
        r=self.s.call('device_set',{'device_id':'light_living','changes':{'power':True,'target_temperature_c':25}})
        self.assertEqual(r['error']['code'],'UNSUPPORTED_OPERATION');self.assertEqual(self.s.state['devices'],before)
    def test_idempotent_request_and_conflict(self):
        a={'kind':'reminder','when':when('2026-12-02T08:00:00+08:00'),'payload':payload('带钥匙')}
        r=self.s.call('schedule_create',a,'same');self.assertEqual(self.s.call('schedule_create',a,'same'),r);self.assertEqual(len(self.s.state['schedules']),1)
        b=copy.deepcopy(a);b['payload']['message']='带雨伞';self.assertEqual(self.s.call('schedule_create',b,'same')['error']['code'],'CONFLICT')
        self.s.call('schedule_create',a,'new');self.assertEqual(len(self.s.state['schedules']),2)
    def test_schedule_lifecycle_and_owner(self):
        r=self.s.call('schedule_create',{'kind':'reminder','when':when('2026-12-02T08:00:00+08:00'),'payload':payload('带钥匙')});id=r['data']['id']
        r=self.s.call('schedule_update',{'schedule_id':id,'patch':{'when':when('2026-12-02T08:30:00+08:00')}});self.assertEqual(r['data']['when']['at'],'2026-12-02T08:30:00+08:00')
        self.assertEqual(self.s.call('schedule_cancel',{'schedule_id':id})['data']['status'],'cancelled')
        self.s.state['schedules'].append(schedule('private','私密内容','2026-12-02T09:00:00+08:00',owner='other'))
        self.assertNotIn('private',[x['id'] for x in self.s.call('schedule_list',{'status':'all'})['data']['schedules']])
        self.assertEqual(self.s.call('schedule_cancel',{'schedule_id':'private'})['error']['code'],'PERMISSION_DENIED')
    def test_delay_cancel_no_rollback(self):
        self.env['faults']=[{'id':'delay','tool_name':'device_set','resource_id':'light_living','on_attempts':[1],'kind':'delay','delay_ms':1000}];s=Sandbox(self.env,ACTOR)
        r=s.call('device_set',{'device_id':'light_living','changes':{'power':True}});id=r['operation_id'];self.assertEqual(r['status'],'pending')
        self.assertEqual(s.call('task_get',{'task_id':id})['data']['status'],'pending')
        self.assertEqual(s.call('task_cancel',{'task_id':id})['data']['status'],'cancelled');s.advance(2000);self.assertFalse(s.find('devices','light_living')['state']['power'])
        s=Sandbox(self.env,ACTOR);id=s.call('device_set',{'device_id':'light_living','changes':{'power':True}})['operation_id'];s.advance(2000)
        self.assertEqual(s.call('task_cancel',{'task_id':id})['error']['code'],'NOT_CANCELLABLE');self.assertTrue(s.find('devices','light_living')['state']['power'])
    def test_media_lifecycle(self):
        s=self.s;r=s.call('media_play',{'content_id':'media_1','device_id':'speaker_living'});id=r['data']['id']
        self.assertEqual(s.call('media_control',{'playback_id':id,'action':'pause'})['data']['status'],'paused')
        self.assertEqual(s.call('media_control',{'playback_id':id,'action':'seek','position_s':20})['data']['position_s'],20)
        self.assertTrue(s.call('media_control',{'playback_id':id,'action':'resume'})['ok'])
        self.assertEqual(s.call('media_control',{'playback_id':id,'action':'stop'})['data']['status'],'stopped')
    def test_clock_triggers_once_and_external_order(self):
        self.env['external_events']=[{'id':'event1','at':'2026-12-01T18:00:01+08:00','type':'device_change','target_id':'light_living','changes':{'brightness_pct':40},'sensor_value':None}]
        s=Sandbox(self.env,ACTOR)
        r=s.call('schedule_create',{'kind':'device_action','when':when('2026-12-01T18:00:01+08:00'),'payload':payload(actions=[{'device_id':'light_living','changes':{'brightness_pct':80}}])})
        self.assertTrue(r['ok']);s.advance(2000);self.assertEqual(s.find('devices','light_living')['state']['brightness_pct'],80);self.assertEqual(len(s.state['tasks']),1);s.advance(1000);self.assertEqual(len(s.state['tasks']),1)
    def test_wrong_then_reverted_is_caught(self):
        c=blueprint(SCENES[0],1);s=Sandbox(c['environment'],ACTOR)
        s.call('device_set',{'device_id':'light_living','changes':{'power':True}});s.call('device_set',{'device_id':'light_living','changes':{'power':False}});s.end_turn('U1')
        checks={x['check_id']:x for x in grade_rules(c,s)};self.assertTrue(checks['S1']['passed']);self.assertFalse(checks['NO_EXTRA']['passed'])
    def test_model_cannot_set_owner_or_empty_patch(self):
        self.assertEqual(self.s.call('schedule_create',{'owner_id':'admin','kind':'reminder','when':when('2026-12-02T08:00:00+08:00'),'payload':payload('x')})['error']['code'],'INVALID_ARGUMENT')
        self.assertEqual(self.s.call('schedule_update',{'schedule_id':'missing','patch':{}})['error']['code'],'INVALID_ARGUMENT')
    def test_case_reset(self):
        self.s.call('device_set',{'device_id':'light_living','changes':{'power':True}});other=Sandbox(self.env,ACTOR);self.assertFalse(other.find('devices','light_living')['state']['power'])
    def test_extra_polling_does_not_require_pending_forever(self):
        scene=next(s for s in SCENES if s['scene_id']=='T29');c=blueprint(scene,11);s=Sandbox(c['environment'],ACTOR)
        for t in c['reference']['turns']:
            for e in t['calls']:s.call(e['call']['tool_name'],e['call']['arguments'])
            s.advance(1500);s.end_turn(t['node_id'])
        self.assertTrue(all(r['passed'] for r in grade_rules(c,s)))
    def test_wrong_existing_schedule_target_is_caught(self):
        scene=next(s for s in SCENES if s['scene_id']=='T23');c=blueprint(scene,1);s=Sandbox(c['environment'],ACTOR)
        s.call('schedule_update',{'schedule_id':'keep_existing','patch':{'when':when('2026-12-02T08:30:00+08:00')}});s.end_turn('U1')
        result={x['check_id']:x for x in grade_rules(c,s)};self.assertFalse(result['NO_EXTRA']['passed'])
if __name__=='__main__':unittest.main()
