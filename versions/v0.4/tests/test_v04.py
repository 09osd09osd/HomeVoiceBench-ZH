import copy,hashlib,json,tempfile,unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from homevoice.design import assignments,blueprint
from homevoice.sandbox import ROOT,REGISTRY,Sandbox,compact_tools,validate
from homevoice.grading import grade_rules
from homevoice.runner import execute,GREEDY,model_projection
from homevoice.outcome import task_pass
from homevoice.semantics import equivalent
from homevoice.fixtures import when,payload,fixture

ACTOR={'id':'user_1','name':'小林','role':'adult_member'}
def case(scene,index=101):return blueprint(next(x for x in assignments('development') if x['scene']['scene_id']==scene and x['index']==index))
def checks(c,s):return {x['check_id']:x['passed'] for x in grade_rules(c,s)}
def replay(c,s,idx):
    t=c['reference']['turns'][idx];s.begin_turn(t['node_id'])
    for e in t['calls']:s.call(e['call']['tool_name'],e['call']['arguments'])
    s.end_turn(t['node_id'])

class DesignTests(unittest.TestCase):
    def test_balanced_and_frozen_families(self):
        for split,n in [('development',100),('test',1000)]:
            a=assignments(split);self.assertEqual(len(a),n);self.assertEqual(sum(x['grouped'] for x in a),n*.4)
            self.assertEqual(Counter(x['difficulty'] for x in a),{'easy':n*.6,'medium':n*.3,'hard':n*.1})
        a=case('T01',101);b=case('T01',104)
        self.assertEqual(a['environment']['initial_state'],b['environment']['initial_state'])
        self.assertEqual(a['interaction']['nodes'][0]['user_text'],b['interaction']['nodes'][0]['user_text'])
    def test_all_1100_references_and_schemas(self):
        schema=json.loads((ROOT/'spec/case.schema.json').read_text('utf-8'))
        for a in assignments('development')+assignments('test'):
            c=blueprint(a);validate(c,schema)
    def test_tools_and_no_oracle_leak(self):
        c=case('T06');self.assertEqual(len(compact_tools(c['model_context']['tool_names'])),10)
        self.assertEqual(len(case('T29')['model_context']['tool_names']),12)
        text=model_projection(c)[0]['content'];self.assertNotIn('expected_response',text);self.assertNotIn('faults',text)
        self.assertIn('current_at',text);self.assertIn('rooms',text)
    def test_greedy_neutral_penalties(self):
        self.assertEqual(GREEDY['temperature'],0);self.assertEqual(GREEDY['presence_penalty'],0);self.assertEqual(GREEDY['repeat_penalty'],1)

class RuleTests(unittest.TestCase):
    def test_same_time_and_wrong_time(self):
        self.assertTrue(equivalent({'when':when('2026-12-02T07:00:00+08:00')},{'when':when('2026-12-01T23:00:00.000Z')}))
        self.assertFalse(equivalent({'when':when('2026-12-02T07:00:00+08:00')},{'when':when('2026-12-02T07:00:01+08:00')}))
    def test_read_only_chat_allowed_write_detected(self):
        c=case('C08');s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1');s.call('sensor_read',{'room_id':'卧室','metrics':['humidity_pct']});s.end_turn('U1')
        self.assertTrue(all(checks(c,s).values()))
        s.begin_turn('U1');s.call('device_set',{'device_id':'客厅空调','changes':{'mode':'dry'}});s.end_turn('U1');self.assertFalse(checks(c,s)['NO_EXTRA'])
    def test_wrong_then_restore_detected(self):
        c=case('T06');s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1')
        calls=c['reference']['turns'][0]['calls'];good=next(e['call'] for e in calls if e['call']['tool_name']=='device_set');bad=copy.deepcopy(good['arguments']);bad['changes']['brightness_pct']=99
        s.call('device_set',bad);s.call('device_set',good['arguments']);s.end_turn('U1')
        self.assertTrue(checks(c,s)['S1']);self.assertFalse(checks(c,s)['NO_EXTRA'])
    def test_future_write_not_authorized(self):
        d=next(x for x in assignments('test') if x['scene']['scene_id']=='T07' and x['variant']==3 and x['turns']>=2);c=blueprint(d);s=Sandbox(c['environment'],ACTOR);s.begin_turn('U1')
        s.call('device_set',{'device_id':'light_living','changes':{'color_temperature_k':3500}});s.call('device_set',{'device_id':'light_living','changes':{'color_temperature_k':4000}});s.end_turn('U1');replay(c,s,1)
        self.assertTrue(checks(c,s)['S1']);self.assertFalse(checks(c,s)['NO_EXTRA'])
    def test_query_alias_and_unknown_room(self):
        c=case('T10');s=Sandbox(c['environment'],ACTOR);a=s.call('device_query',{'room_id':'书房','device_type':'fan'});self.assertTrue(a['ok']);self.assertIn('fan_study',json.dumps(a))
        self.assertFalse(s.call('device_query',{'room_id':'不存在的房间'})['ok'])
        q=s.call('device_set',{'device_id':'书房风扇','changes':{'fan_speed':2}});self.assertTrue(q['ok']);self.assertEqual(s.trace[-1]['submitted_arguments']['device_id'],'书房风扇')
    def test_contract_cancel_and_replace(self):
        s=Sandbox(fixture('CONTRACT',1),ACTOR);sid=s.call('schedule_create',{'kind':'reminder','when':when('2026-12-02T08:00:00+08:00'),'payload':payload('带钥匙')})['data']['id']
        self.assertTrue(s.call('schedule_cancel',{'schedule_id':sid})['ok']);self.assertTrue(s.call('schedule_cancel',{'schedule_id':sid})['ok'])
        pid=s.call('media_play',{'content_id':'media_1','device_id':'speaker_living'})['data']['id'];self.assertTrue(s.call('media_play',{'content_id':'media_2','device_id':'speaker_living'})['ok']);self.assertEqual(s.find('playbacks',pid)['status'],'stopped')

class ExecutionTests(unittest.TestCase):
    def test_interruption_has_executed_and_pending_calls(self):
        c=case('T01');c['variants'][0]['status']='ready'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'input.wav';p.write_bytes(b'test-placeholder')
            c['variants'][0]['audio_assets']=[{'node_id':'U1','path':'input.wav','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]
            response={'raw_output':'我先查一下。<tool_call>{"name":"device_query","arguments":{}}</tool_call>','finish_reason':'stop'}
            with patch('homevoice.runner.ROOT',root),patch('homevoice.runner.post',return_value=response):r=execute(c,'edge_native','unused')
        self.assertEqual(len(r['tool_trace']),4);self.assertEqual(len(r['incomplete_turn']['pending_tool_calls_not_executed']),1)
        self.assertEqual(len(r['incomplete_turn']['tool_events']),4);self.assertEqual(r['execution']['failure']['reason'],'tool_call_budget_exceeded');self.assertEqual(r['execution']['failure']['stage'],'tool_budget_check');self.assertEqual(len(r['turns']),0)
    def test_quality_does_not_change_task_gate(self):
        c=case('C01');r={'execution':{'status':'completed'},'rule_checks':[{'check_id':x['id'],'passed':True} for x in c['evaluation']['checks'] if x['method']=='rule'],'turns':[{'assistant_audio':{'hit_frame_budget':False}}]}
        j={'semantic_checks':[{'check_id':'CONTENT','passed':True},{'check_id':'HONEST','passed':True}],'critical_failures':[],'dimensions':[{'score':2}]}
        self.assertTrue(task_pass(r,c,j));j['semantic_checks'][0]['passed']=False;self.assertFalse(task_pass(r,c,j))
if __name__=='__main__':unittest.main()
