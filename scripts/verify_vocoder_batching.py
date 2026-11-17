"""Compare identical codec samples decoded at batch 8 and batch 2; no run writes."""
import json, math, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from homevoice.paths import model_path
from homevoice.vocoder_batch import decode_in_chunks
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import numpy as np
import torch
from qwen_tts import Qwen3TTSModel

torch.set_num_threads(6)
torch.manual_seed(42)
modeldir = model_path('tts_model')
generation = json.loads((modeldir/'generation_config.json').read_text('utf-8'))
generation['max_new_tokens'] = 1024
model = Qwen3TTSModel.from_pretrained(str(modeldir), dtype=torch.bfloat16, device_map='cuda:0', attn_implementation='sdpa', local_files_only=True)
tokenizer = model.model.speech_tokenizer
assert tokenizer.get_model_type() == 'qwen3_tts_tokenizer_12hz'
original = tokenizer.decode
comparisons = []
def measure(fn):
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    result = fn()
    torch.cuda.synchronize()
    return result, {'seconds': time.monotonic()-started, 'peak_gpu_bytes': torch.cuda.max_memory_allocated()}

def compare(encoded, label):
    (full, rate), full_stats = measure(lambda: original(encoded))
    trace = []
    (bounded, other_rate), bounded_stats = measure(lambda: decode_in_chunks(original, encoded, 2, lambda c,n: torch.nn.functional.pad(c,(0,0,0,n-len(c)),value=-1), trace))
    assert rate == other_rate
    differences = []
    for a,b in zip(full,bounded):
        a,b = np.asarray(a), np.asarray(b)
        same_length = a.shape == b.shape
        delta = a.astype(np.float64)-b.astype(np.float64) if same_length else np.array([np.inf])
        differences.append({'frames': len(a), 'same_length': same_length, 'float_identical': bool(np.array_equal(a,b)), 'max_absolute_difference': float(np.max(np.abs(delta))), 'rmse': float(np.sqrt(np.mean(delta**2)))})
    entry = {'label': label, 'codec_lengths': [len(x['audio_codes']) for x in encoded], 'full_batch': full_stats, 'bounded_batch': bounded_stats, 'chunks': trace, 'differences': differences, 'passed': len(full)==len(bounded)==len(encoded) and all(d['same_length'] and d['rmse']<=1e-4 and d['max_absolute_difference']<=.002 for d in differences)}
    comparisons.append(entry)
    print(json.dumps(entry), flush=True)
    return bounded, rate

def probe(encoded):
    result = compare(encoded, 'eight_actual_pilot_utterances')
    stress = [{**x, 'audio_codes': x['audio_codes'].clone()} for x in encoded]
    codes = stress[0]['audio_codes']
    stress[0]['audio_codes'] = codes.repeat(math.ceil(1024/len(codes)),1)[:1024]
    compare(stress, 'synthetic_1024_codec_frame_memory_probe_not_benchmark_audio')
    return result

tokenizer.decode = probe
texts = sorted([f'{x}，客厅灯已经打开，亮度调到了百分之四十。' for x in ['好的','收到','没问题','已处理','现在','你看','可以','设置完成']],key=lambda t:(len(t),t))
with torch.inference_mode():
    model.generate_custom_voice(text=texts, language='Chinese', speaker='Vivian', non_streaming_mode=True, **generation)
report = {'status': 'passed' if all(c['passed'] for c in comparisons) else 'needs_inspection', 'policy': 'same_global_padding_batch_axis_split_v1', 'vocoder_max_batch_size': 2, 'tokenizer_type': tokenizer.get_model_type(), 'generation': generation, 'seed':42, 'thresholds':{'rmse_max':1e-4,'absolute_difference_max':.002}, 'note':'Identical generated codec inputs; global padding and official temporal decoder chunking unchanged. Stress audio is not a benchmark answer. No model run or cached audio overwritten.', 'comparisons':comparisons}
(ROOT/'reports/tts_vocoder_pilot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
if report['status']!='passed':raise SystemExit('Vocoder comparison requires inspection')
