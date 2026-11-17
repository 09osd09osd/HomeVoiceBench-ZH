import unittest
from homevoice.speech_text import normalize,integer
class SpeechTextTests(unittest.TestCase):
    def test_numbers(self):
        for a,b in [('122','一百二十二'),('10','十'),('101','一百零一'),('1001','一千零一'),('10001','一万零一'),('100010001','一亿零一万零一'),('0','零'),('-2.05','负二点零五')]:
            with self.subTest(a=a):self.assertEqual(normalize(a),b)
    def test_household_units(self):
        for a,b in [('26℃','二十六摄氏度'),('40%','百分之四十'),('07:30','七点三十分'),('08:00','八点整'),('22:05:09','二十二点五分九秒'),('0.5kWh','零点五千瓦时'),('4000K','四千开尔文'),('800 ppm','百万分之八百'),('300lux','三百勒克斯'),('15m²','十五平方米'),('250mL','二百五十毫升'),('1,200W','一千二百瓦'),('-5℃','负五摄氏度')]:
            with self.subTest(a=a):self.assertEqual(normalize(a),b)
    def test_dates_and_ranges(self):
        self.assertEqual(normalize('2026-12-01T07:30:00+08:00'),'二零二六年十二月一日七点三十分，东八区')
        self.assertEqual(normalize('2026年12月1日'),'二零二六年十二月一日')
        self.assertEqual(normalize('20-30℃'),'二十到三十摄氏度')
        self.assertEqual(normalize('13800138000'),'一三八零零一三八零零零')
    def test_idempotent_and_semantic_preservation(self):
        for s in ['只把亮度设为40%，别改26℃。','明天07:30提醒我带122元。','负二点五摄氏度','任务TASK_T30_001_001']:
            self.assertEqual(normalize(normalize(s)),normalize(s))
        self.assertEqual(normalize('不要关灯。'),'不要关灯。')
if __name__=='__main__':unittest.main()
