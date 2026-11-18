import hashlib,json,tempfile,unittest
from pathlib import Path
from homevoice.human_review import collect

class HumanImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.put('data/manifest.json',{'cases':[{'case_id':'C01_101'}]});self.put('reports/summary.json',{'judge_prompt_sha256':'fixture-prompt'})
        self.run={'execution':{'status':'completed'},'rule_checks':[],'audio_judge':{'evidence_sha256':'a'*64},'semantic_review':{'decision_status':'disputed'}}
        self.put('runs/edge_native/C01_101.json',self.run)
        sha=hashlib.sha256((self.root/'data/manifest.json').read_bytes()).hexdigest()
        self.label={'opinion':'pending','verdict':'pass','note':'第一轮回答了用户的全部要求','evidence_sha256':'a'*64}
        self.export={'format':'homevoice-human-review-v1','manifest_sha256':sha,'dataset_key':'homevoice-review-v2:'+sha+':fixture-prompt','records':[{'case_id':'C01_101','systems':{'edge_native':self.label},'note':''}]}
    def put(self,name,data):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data),'utf-8')
    def test_import_does_not_change_run_and_requires_a_reason(self):
        path=self.root/'runs/edge_native/C01_101.json';before=path.read_bytes()
        result=collect(self.export,self.root);self.assertEqual(result['resolved_records'],1);self.assertEqual(result['status'],'ready_for_calibration_analysis');self.assertEqual(path.read_bytes(),before)
        self.label['note']='';self.assertEqual(collect(self.export,self.root)['resolved_records'],0)
    def test_stale_evidence_and_wrong_dataset_rejected(self):
        self.label['evidence_sha256']='b'*64
        with self.assertRaises(ValueError):collect(self.export,self.root)
        self.label['evidence_sha256']='a'*64;self.export['dataset_key']='wrong'
        with self.assertRaises(ValueError):collect(self.export,self.root)
    def test_uncertain_and_objective_conflict_are_not_resolved(self):
        self.label['verdict']='uncertain';result=collect(self.export,self.root);self.assertEqual(result['resolved_records'],0);self.assertEqual(len(result['uncertain']),1)
        self.label['verdict']='pass';self.run['rule_checks']=[{'check_id':'UNAUTHORIZED_WRITE','passed':False}];self.put('runs/edge_native/C01_101.json',self.run)
        result=collect(self.export,self.root);self.assertEqual(result['resolved_records'],0);self.assertEqual(len(result['objective_conflicts']),1)
    def test_duplicate_case_is_rejected(self):
        self.export['records'].append(self.export['records'][0])
        with self.assertRaises(ValueError):collect(self.export,self.root)
