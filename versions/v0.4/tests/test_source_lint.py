import unittest
from homevoice.source_lint import issues,naturalize

class SpokenSourceTests(unittest.TestCase):
    def test_ascii_identifiers_touching_chinese_are_caught(self):
        self.assertEqual(issues('把mode设为auto模式，sleep是睡眠', 'tool'), ['auto','mode','sleep'])
    def test_natural_household_request_is_not_code(self):
        self.assertEqual(issues('打开客厅净化器，设成自动模式。', 'tool'), [])
    def test_naturalization_preserves_numeric_targets(self):
        self.assertEqual(naturalize('把brightness_pct设为65%，mode设为auto模式（sleep=睡眠，manual=手动，auto=自动）。'),'把亮度设为65%，运行模式设为自动模式。')
    def test_english_chat_and_larger_words_are_not_field_leaks(self):
        self.assertEqual(issues('解释sleep和auto的英文意思', 'chat'), [])
        self.assertEqual(issues('播放Sleepy和Automatic这两首歌', 'tool'), [])
