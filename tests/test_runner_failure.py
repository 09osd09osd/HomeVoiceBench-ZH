import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from homevoice.blueprints import blueprint
from homevoice.catalog import SCENES
from homevoice.runner import execute
class FailureEvidenceTests(unittest.TestCase):
    def test_budget_failure_keeps_every_tool_and_unspoken_response(self):
        c=blueprint(SCENES[0],1);c['variants'][0]['status']='ready'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'input.wav';p.write_bytes(b'infrastructure-test-placeholder')
            c['variants'][0]['audio_assets']=[{'node_id':'U1','path':'input.wav','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]
            response={'raw_output':'<tool_call>{"name":"home_get","arguments":{}}</tool_call>','finish_reason':'stop'}
            with patch('homevoice.runner.ROOT',root),patch('homevoice.runner.post',return_value=response):r=execute(c,'edge_native','unused')
        self.assertEqual(r['execution']['status'],'failed');self.assertEqual(len(r['turns']),0);self.assertEqual(len(r['tool_trace']),4)
        self.assertEqual(len(r['incomplete_turn']['model_raw_responses']),5);self.assertIn('tool_call_budget_exceeded',r['execution']['flags'][0])
