import copy, unittest
from homevoice.authorization import compile_policy
from homevoice.blueprints import blueprint
from homevoice.catalog import SCENES
from homevoice.fixtures import fixture, when, payload
from homevoice.grading import grade_rules
from homevoice.sandbox import Sandbox
from homevoice.semantics import equivalent

ACTOR={'id':'user_1','name':'小林','role':'adult_member'}
def make(scene,index):return blueprint(next(s for s in SCENES if s['scene_id']==scene),index)
def checks(case,sim):return {r['check_id']:r for r in grade_rules(case,sim)}
def reference_turn(case,sim,index):
    turn=case['reference']['turns'][index];sim.begin_turn(turn['node_id'])
    for e in turn['calls']:sim.call(e['call']['tool_name'],e['call']['arguments'])
    sim.end_turn(turn['node_id'])

class TypedStateTests(unittest.TestCase):
    def test_equal_instant_fraction_and_offset(self):
        a={'when':when('2026-12-02T07:00:00+08:00')}
        for value in ['2026-12-02T07:00:00.000+08:00','2026-12-01T23:00:00Z']:
            b=copy.deepcopy(a);b['when']['at']=value;self.assertTrue(equivalent(a,b))
        b=copy.deepcopy(a);b['when']['at']='2026-12-02T07:00:01+08:00';self.assertFalse(equivalent(a,b))
        b['when']['at']='2026-12-02T07:00:00';self.assertFalse(equivalent(a,b))
    def test_unordered_lists_preserve_multiplicity_and_recurrence_zone(self):
        self.assertTrue(equivalent({'when':{'weekdays':[1,3,5]}},{'when':{'weekdays':[5,1,3]}}))
        self.assertFalse(equivalent({'tasks':[{'status':'pending'}]},{'tasks':[{'status':'pending'},{'status':'pending'}]}))
        self.assertFalse(equivalent({'when':{'local_time':'07:00:00','timezone':'Asia/Taipei'}},{'when':{'local_time':'07:00:00','timezone':'UTC'}}))
        self.assertFalse(equivalent({'power':True},{'power':1}))
        self.assertFalse(equivalent({'message':'1'},{'message':1}))
    def test_wrong_datetime_fails_real_checkpoint(self):
        c=make('T21',1)
        for instant,expected in [('2026-12-02T07:00:00.000+08:00',True),('2026-12-02T08:00:00+08:00',False)]:
            s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1')
            for e in c['reference']['turns'][0]['calls']:
                a=copy.deepcopy(e['call']['arguments'])
                if e['call']['tool_name']=='schedule_create':a['when']['at']=instant
                s.call(e['call']['tool_name'],a)
            s.end_turn('U1');self.assertEqual(checks(c,s)['S1']['passed'],expected)

class TurnAuthorizationTests(unittest.TestCase):
    def test_wrong_value_then_restored_is_detected(self):
        c=make('T06',1);s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1')
        s.call('device_set',{'device_id':'light_living','changes':{'power':True,'brightness_pct':99}})
        s.call('device_set',{'device_id':'light_living','changes':{'brightness_pct':20}});s.end_turn('U1')
        r=checks(c,s);self.assertTrue(r['S1']['passed']);self.assertFalse(r['NO_EXTRA']['passed'])
    def test_future_authorization_does_not_apply_to_read_only_turn(self):
        c=make('T07',17);s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1')
        s.call('device_set',{'device_id':'light_living','changes':{'color_temperature_k':3500}})
        s.call('device_set',{'device_id':'light_living','changes':{'color_temperature_k':4000}});s.end_turn('U1')
        reference_turn(c,s,1);r=checks(c,s)
        self.assertTrue(r['S1']['passed']);self.assertTrue(r['S2']['passed']);self.assertFalse(r['NO_EXTRA']['passed'])
    def test_split_updates_and_extra_queries_are_valid(self):
        c=make('T06',1);s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1')
        s.call('clock_get',{});s.call('device_list',{})
        s.call('device_set',{'device_id':'light_living','changes':{'power':True}})
        s.call('device_set',{'device_id':'light_living','changes':{'brightness_pct':20}});s.end_turn('U1')
        self.assertTrue(all(r['passed'] for r in grade_rules(c,s)))
    def test_previous_value_is_not_authorized_after_correction(self):
        c=make('T06',2);s=Sandbox(c['environment'],ACTOR);reference_turn(c,s,0);s.begin_turn('U2')
        s.call('device_set',{'device_id':'light_living','changes':{'brightness_pct':20}})
        s.call('device_set',{'device_id':'light_living','changes':{'brightness_pct':80}});s.end_turn('U2')
        self.assertTrue(checks(c,s)['S2']['passed']);self.assertFalse(checks(c,s)['NO_EXTRA']['passed'])
    def test_interrupted_turn_keeps_its_own_authorization(self):
        c=make('T07',17);s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1')
        s.call('device_set',{'device_id':'light_living','changes':{'color_temperature_k':3500}})
        self.assertFalse(checks(c,s)['NO_EXTRA']['passed'])
    def test_chat_read_allowed_but_write_is_not(self):
        c=make('C08',1);s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1')
        s.call('sensor_read',{'room_id':'bedroom','metrics':['humidity_pct']});s.end_turn('U1')
        self.assertTrue(all(r['passed'] for r in grade_rules(c,s)))
        s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1')
        s.call('device_set',{'device_id':'ac_living','changes':{'mode':'dry'}});s.end_turn('U1')
        self.assertFalse(checks(c,s)['NO_EXTRA']['passed'])
    def test_explicit_no_query_is_enforced(self):
        c=make('C08',1);c['evaluation']['behavior_policy']=compile_policy(c,[{'node_id':'U1','blocked_read_tools':['sensor_read'],'restriction_evidence':['不要查询湿度。']}])
        s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1');s.call('sensor_read',{'room_id':'bedroom','metrics':['humidity_pct']});s.end_turn('U1')
        self.assertFalse(checks(c,s)['READ_BOUNDARY']['passed'])

class ContractRegressionTests(unittest.TestCase):
    def test_repeated_cancel_new_request_is_semantically_idempotent(self):
        s=Sandbox(fixture('CANCEL',1),ACTOR)
        created=s.call('schedule_create',{'kind':'reminder','when':when('2026-12-02T08:00:00+08:00'),'payload':payload('带钥匙')})['data']
        first=s.call('schedule_cancel',{'schedule_id':created['id']},'cancel1');second=s.call('schedule_cancel',{'schedule_id':created['id']},'cancel2')
        self.assertTrue(second['ok']);self.assertEqual(first['data'],second['data'])
    def test_completed_schedule_cancel_is_not_cancellable(self):
        s=Sandbox(fixture('DONE',1),ACTOR)
        sid=s.call('schedule_create',{'kind':'reminder','when':when('2026-12-01T18:00:01+08:00'),'payload':payload('提示')})['data']['id']
        s.advance(2000);self.assertEqual(s.call('schedule_cancel',{'schedule_id':sid})['error']['code'],'NOT_CANCELLABLE')
    def test_new_media_stops_old_on_same_device_only(self):
        s=Sandbox(fixture('PLAY',1),ACTOR)
        a=s.call('media_play',{'content_id':'media_1','device_id':'speaker_living'})['data']['id']
        b=s.call('media_play',{'content_id':'media_2','device_id':'speaker_bedroom'})['data']['id']
        new=s.call('media_play',{'content_id':'media_3','device_id':'speaker_living'})
        self.assertTrue(new['ok']);self.assertEqual(s.find('playbacks',a)['status'],'stopped');self.assertEqual(s.find('playbacks',b)['status'],'playing')
    def test_media_replacement_checks_permissions_atomically(self):
        s=Sandbox(fixture('PRIVATE',1),ACTOR);old=s.call('media_play',{'content_id':'media_1','device_id':'speaker_living'})['data']['id']
        s.find('playbacks',old)['owner_id']='other';before=copy.deepcopy(s.state['playbacks'])
        result=s.call('media_play',{'content_id':'media_2','device_id':'speaker_living'})
        self.assertEqual(result['error']['code'],'PERMISSION_DENIED');self.assertEqual(s.state['playbacks'],before)

if __name__=='__main__':unittest.main()
