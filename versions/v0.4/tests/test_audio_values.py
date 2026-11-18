import unittest
from homevoice.audio_facts import contains_value,evaluate,specifications
from test_v04 import case
class AudioValueTests(unittest.TestCase):
    def test_numbers_units_and_token_boundaries(self):
        for text in ['当前温度24℃','温度是二十四摄氏度','二四']:
            self.assertTrue(contains_value(text,24))
        self.assertFalse(contains_value('一百二十四摄氏度',24));self.assertFalse(contains_value('二十四点五摄氏度',24))
        self.assertTrue(contains_value('一百二十二',122));self.assertTrue(contains_value('两百四十七',247))
    def test_transcript_disagreement_needs_review(self):
        c=case('C16');run={'turns':[{'node_id':'U1','user_turn_index':1,'assistant_audio':{'sha256':'x'}}],'audio_judge':{'result':{'heard_turns':[{'user_turn_index':1,'assistant_transcript':'二百四十七'}]}}}
        r=evaluate(c,run,{'x':'二百四十八'});self.assertEqual(r[0]['status'],'needs_review')
    def test_sensor_truth_is_from_frozen_evidence(self):
        specs=specifications(case('T16'));self.assertEqual({s['expected'] for s in specs},{24,65})
if __name__=='__main__':unittest.main()
