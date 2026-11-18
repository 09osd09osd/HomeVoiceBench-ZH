import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import review_semantics as review

class ConsensusTests(unittest.TestCase):
    def outcome(self,primary,proposal):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data/cases').mkdir(parents=True);(root/'runs/edge_native').mkdir(parents=True)
            case={'evaluation':{'checks':[{'id':'CONTENT','required':True},{'id':'HONEST','required':True}]}}
            run={'audio_judge':{'result':{}},'case_pass':primary,'execution':{'status':'completed'},'rule_checks':[],'turns':[]}
            result={'result':{'checks':[{'check_id':'CONTENT','passed':proposal},{'check_id':'HONEST','passed':True}],'critical_failures':[]}}
            p=root/'runs/edge_native/C01_101.json';p.write_text(json.dumps(run));(root/'data/cases'/p.name).write_text(json.dumps(case))
            with patch.object(review,'ROOT',root),patch.object(review,'current',return_value=False),patch.object(review,'request_review',return_value=result):review.process(p)
            return json.loads(p.read_text())
    def test_disagreement_is_never_silently_selected(self):
        for primary,proposal in [(True,False),(False,True)]:
            r=self.outcome(primary,proposal);self.assertIsNone(r['case_pass']);self.assertEqual(r['case_pass_primary'],primary);self.assertEqual(r['semantic_review']['proposed_case_pass'],proposal);self.assertEqual(r['semantic_review']['decision_status'],'disputed')
    def test_agreed_failure_and_success_remain_observed(self):
        for value in [False,True]:
            r=self.outcome(value,value);self.assertEqual(r['case_pass'],value);self.assertEqual(r['semantic_review']['decision_status'],'agreed')
    def test_list_root_is_a_format_error_not_a_rating(self):
        with self.assertRaises(ValueError):review.validate([])
