import copy
import unittest
from homevoice.judge_schema import validate_judgment

class JudgeSchemaTests(unittest.TestCase):
    def fixture(self):
        return {'dimensions':[{'dimension_id':'accuracy','score':4,'reason':'heard evidence','evidence':['turn 1']}],
                'semantic_checks':[{'check_id':'honesty','passed':True,'reason':'no false completion','evidence':[]}],
                'critical_failures':[],'heard_turns':[{'user_turn_index':1,'assistant_transcript':'好的'}],'task_achieved':True}

    def check(self,obj):return validate_judgment(obj,['accuracy'],['honesty'],[1])

    def test_alias_preserves_scores_and_input(self):
        obj=self.fixture();obj['dimensions'][0]['id']=obj['dimensions'][0].pop('dimension_id')
        obj['semantic_checks'][0]['id']=obj['semantic_checks'][0].pop('check_id')
        before=copy.deepcopy(obj);result=self.check(obj)
        self.assertEqual(obj,before);self.assertEqual(result['dimensions'][0]['score'],4)
        self.assertEqual(result['dimensions'][0]['dimension_id'],'accuracy')

    def test_invalid_evidence_or_scores_never_fabricated(self):
        for value in [True,6,-1,3.5,'4',None]:
            with self.subTest(value=value):
                obj=self.fixture();obj['dimensions'][0]['score']=value
                with self.assertRaises(ValueError):self.check(obj)
        for key in ['dimensions','heard_turns','semantic_checks']:
            obj=self.fixture();obj[key]=[]
            with self.assertRaises(ValueError):self.check(obj)
        with self.assertRaises(ValueError):self.check([self.fixture()])

    def test_duplicate_or_unheard_turn_rejected(self):
        obj=self.fixture();obj['dimensions']*=2
        with self.assertRaises(ValueError):self.check(obj)
        obj=self.fixture();obj['heard_turns'][0]['user_turn_index']=2
        with self.assertRaises(ValueError):self.check(obj)
