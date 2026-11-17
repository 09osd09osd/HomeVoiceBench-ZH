import json,unittest
from homevoice.runner import parse_raw,model_projection
from homevoice.blueprints import blueprint
from homevoice.catalog import SCENES
class ProtocolTests(unittest.TestCase):
    def test_qwen_xml_and_json_equivalent(self):
        xml='<tool_call>\n<function=device_set>\n<parameter=device_id>light_living</parameter>\n<parameter=changes>{"power":true,"brightness_pct":40}</parameter>\n</function>\n</tool_call>'
        j='<tool_call>{"name":"device_set","arguments":{"device_id":"light_living","changes":{"power":true,"brightness_pct":40}}}</tool_call>'
        self.assertEqual(parse_raw(xml),parse_raw(j));self.assertEqual(parse_raw(xml)[0],'')
    def test_reject_malformed(self):
        for text in ['<tool_call>oops</tool_call>','<tool_call>{"name":"device_set"}','<tool_call><function=device_set>garbage</function></tool_call>']:
            with self.subTest(text=text),self.assertRaises(ValueError):parse_raw(text)
    def test_no_truth_leak(self):
        c=blueprint(SCENES[0],5);m=model_projection(c);s=json.dumps(m,ensure_ascii=False)
        for marker in ['reference','expected_response','评分','state_matches',c['identity']['case_id'],c['interaction']['nodes'][0]['user_text']]:self.assertNotIn(marker,s)
        self.assertEqual(len(m),1);self.assertEqual(m[0]['role'],'system')
if __name__=='__main__':unittest.main()
