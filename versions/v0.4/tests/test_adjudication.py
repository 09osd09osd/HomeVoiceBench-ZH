import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import adjudicate_audio as adjudicator
from scripts.adjudicate_audio import outcome

class AdjudicationTests(unittest.TestCase):
    def test_semantic_adjudication_cannot_override_objective_failure(self):
        case={'evaluation':{'checks':[{'id':'STATE','required':True},{'id':'CONTENT','required':True}]}}
        run={'execution':{'status':'completed'},'rule_checks':[{'check_id':'STATE','passed':False}],'turns':[]}
        result={'semantic_checks':[{'check_id':'CONTENT','passed':True}],'critical_failures':[],'numeric_checks':[]}
        self.assertFalse(outcome(case,run,result));run['rule_checks'][0]['passed']=True;self.assertTrue(outcome(case,run,result))
        result['numeric_checks']=[{'passed':False}];self.assertFalse(outcome(case,run,result))

    def test_format_recovery_preserves_invalid_attempts_and_first_valid_failure(self):
        case={'evaluation':{'dimensions':[{'id':'relevance'}]}}
        run={'turns':[]}
        decision={'dimensions':[{'dimension_id':'relevance','score':2,'reason':'Required content absent','evidence':[]}],
                  'semantic_checks':[{'check_id':key,'passed':key=='HONEST','reason':'Evidence','evidence':[]} for key in ['CONTENT','HONEST']],
                  'critical_failures':[],'heard_turns':[],'task_achieved':False,'numeric_checks':[]}
        response={'choices':[{'message':{'content':json.dumps(decision)}}]}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cache=root/'runs/audio_adjudication_requests';cache.mkdir(parents=True)
            originals={}
            for i in range(4):
                p=cache/f'fixed_{i}.json'
                adjudicator.save(p,{'choices':[{'message':{'content':'[Dimension] prose, not JSON'}}]})
                originals[p]=p.read_bytes()
            with patch.object(adjudicator,'ROOT',root),patch.object(adjudicator,'observed_context',return_value={}),patch.object(adjudicator,'requirements',return_value=[]),patch.object(adjudicator,'signature',return_value='fixed'),patch.object(adjudicator,'chat',return_value=response) as api:
                first=adjudicator.request(case,run)
                self.assertEqual(first['format_attempts'],5)
                self.assertFalse(first['result']['task_achieved'])
                self.assertEqual(api.call_count,1)
                self.assertIn('required_root_fields_and_types',api.call_args.args[1][-1]['content'])
                second=adjudicator.request(case,run)
                self.assertEqual(second['result'],first['result'])
                self.assertEqual(api.call_count,1)
            self.assertTrue(all(p.read_bytes()==original for p,original in originals.items()))
