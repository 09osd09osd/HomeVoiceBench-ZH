import json,unittest
from scripts.judge_runs import observed_context

class JudgeEvidenceTests(unittest.TestCase):
    def test_future_nodes_excluded_interrupted_tools_retained(self):
        case={'classification':{'category':'tool'},'evaluation':{'dimensions':[],'checks':[],'pass_policy':{}},'interaction':{'nodes':[{'id':'U1','user_text':'first'},{'id':'U2','user_text':'second'},{'id':'U3','user_text':'unseen future secret'}]},'reference':{'turns':[{'node_id':'U1','assistant_text':'first guide'},{'node_id':'U2','assistant_text':'second guide'},{'node_id':'U3','assistant_text':'future reference secret'}]}}
        event={'call':{'tool_name':'clock_get','arguments':{}},'response':{'ok':True}}
        case['environment']={'initial_state':{'rooms':[{'id':'living','name':'客厅'}]},'faults':[]}
        case['model_context']={'actor':{'id':'member','role':'adult_member'}}
        for t in case['reference']['turns']:t['calls']=[{'call':{'tool_name':'clock_get','arguments':{}},'expected_response':{'ok':True}}]
        run={'turns':[{'node_id':'U1','user_turn_index':1,'tool_events':[]}],'incomplete_turn':{'node_id':'U2','first_tool_event_index':0,'assistant_parts_not_spoken':['unspoken secret']},'tool_trace':[event],'execution':{'status':'failed'},'rule_checks':[]}
        context=observed_context(case,run);serialized=json.dumps(context)
        self.assertNotIn('future secret',serialized);self.assertNotIn('reference secret',serialized);self.assertNotIn('unspoken secret',serialized)
        self.assertEqual([x['node_id'] for x in context['user_intents']],['U1','U2'])
        self.assertEqual(context['interrupted_turn']['tools'],[event]);self.assertFalse(context['interrupted_turn']['assistant_audio_available'])
        self.assertEqual([x['node_id'] for x in context['reference_tool_evidence']],['U1','U2'])
        self.assertEqual(context['oracle_environment']['initial_state']['rooms'][0]['id'],'living')
        self.assertEqual(context['trusted_actor']['id'],'member')
