import unittest
from homevoice.vocoder_batch import decode_in_chunks

class VocoderBatchTests(unittest.TestCase):
    def test_same_global_padding_order_and_unmodified_inputs(self):
        items = [{'id': i, 'audio_codes': [i] * n} for i, n in enumerate([3, 1, 5, 2, 4], 1)]
        sizes = []
        def decoder(batch):
            sizes.append(len(batch))
            self.assertEqual({len(x['audio_codes']) for x in batch}, {5})
            return [[v for v in x['audio_codes'] if v != -1] for x in batch], 24000
        trace = []
        waves, rate = decode_in_chunks(decoder, items, 2, lambda c, n: c + [-1] * (n - len(c)), trace)
        self.assertEqual(sizes, [2, 2, 1])
        self.assertEqual(waves, [x['audio_codes'] for x in items])
        self.assertEqual([len(x['audio_codes']) for x in items], [3, 1, 5, 2, 4])
        self.assertEqual(rate, 24000)
        self.assertEqual([i for x in trace for i in x['sample_indices']], list(range(5)))
