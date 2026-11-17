import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from homevoice.cloud import chat,CloudError,request
from homevoice.revision import replay,input_projection
from scripts.judge_runs import evidence_hash,observed_context
ROOT=Path(__file__).resolve().parents[1]

class RevisionEvidenceTests(unittest.TestCase):
    def fixture(self):
        c=json.loads((ROOT/'data/cases/C16_001.json').read_text('utf-8'))
        r={'turns':[],'incomplete_turn':None,'tool_trace':[],'execution':{'status':'failed'},'rule_checks':[],'revision':{}}
        return c,r
    def test_cache_invalidates_on_constraints_tools_audio_rules_and_parameters(self):
        c,r=self.fixture();key=evidence_hash(c,r)
        c2=copy.deepcopy(c);c2['interaction']['nodes'][0]['user_text']+=' Changed'
        self.assertNotEqual(key,evidence_hash(c2,r))
        r2=copy.deepcopy(r);r2['rule_checks']=[{'check_id':'NO_EXTRA','passed':False}]
        self.assertNotEqual(key,evidence_hash(c,r2))
        r2=copy.deepcopy(r);r2['revision']['grading_version']='changed'
        self.assertNotEqual(key,evidence_hash(c,r2))
        r2=copy.deepcopy(r);r2['turns']=[{'node_id':'U1','user_turn_index':1,'tool_events':[],
                                       'input_audio_sha256':'user-a','assistant_audio':{'sha256':'answer-a','duration_s':1}}]
        with_audio=evidence_hash(c,r2)
        r2['turns'][0]['assistant_audio']['sha256']='answer-b'
        self.assertNotEqual(with_audio,evidence_hash(c,r2))
        with_changed_answer=evidence_hash(c,r2);r2['turns'][0]['input_audio_sha256']='user-b'
        self.assertNotEqual(with_changed_answer,evidence_hash(c,r2))
        with patch('scripts.judge_runs.PROMPT','new judge instructions'):
            self.assertNotEqual(key,evidence_hash(c,r))
    def test_no_objective_verdict_or_fixed_assistant_script_in_judge_context(self):
        c,r=self.fixture();r['rule_checks']=[{'check_id':'SENTINEL_OBJECTIVE_VERDICT','passed':False}]
        c['reference']['turns'][0]['assistant_text']='SENTINEL_FIXED_REFERENCE'
        encoded=json.dumps(observed_context(c,r))
        self.assertNotIn('SENTINEL_OBJECTIVE_VERDICT',encoded);self.assertNotIn('SENTINEL_FIXED_REFERENCE',encoded)
    def test_deepseek_model_always_routes_to_official_provider(self):
        with patch('homevoice.cloud.config',return_value={'deepseek_base_url':'https://api.deepseek.com','bailian_base_url':'https://wrong.example/v1'}),patch('homevoice.cloud.request',return_value={}) as req:
            chat('deepseek-v4.1-flash',[],temperature=0)
        self.assertEqual(req.call_args.args[0],'https://api.deepseek.com/chat/completions')
        self.assertEqual(req.call_args.args[1],'deepseek');self.assertEqual(req.call_args.args[2]['model'],'deepseek-flash')
    def test_transport_rejects_non_official_deepseek_before_loading_credentials(self):
        with patch('homevoice.cloud.load_key') as load:
            with self.assertRaises(CloudError):request('https://other.example/chat','deepseek',{})
            load.assert_not_called()
