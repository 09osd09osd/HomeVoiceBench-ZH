import io,struct,unittest,wave
from homevoice.audio import canonical_wav
class AudioTests(unittest.TestCase):
    def test_streaming_header_repair_preserves_pcm(self):
        pcm=struct.pack('<h',123)*4800;out=io.BytesIO()
        with wave.open(out,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(pcm)
        b=bytearray(out.getvalue());struct.pack_into('<I',b,4,0x7fffffff);struct.pack_into('<I',b,40,0x7fffff00)
        fixed,meta=canonical_wav(bytes(b));self.assertEqual(meta['duration_seconds'],.2);self.assertTrue(meta['wav_container']['header_length_repaired'])
        with wave.open(io.BytesIO(fixed),'rb') as w:self.assertEqual(w.getnframes(),4800);self.assertEqual(w.readframes(4800),pcm)
        self.assertEqual(canonical_wav(fixed)[0],fixed)
