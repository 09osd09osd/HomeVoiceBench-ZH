"""Verify the real eight-utterance TTS probe and EOS instrumentation."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
texts={f'{x}，客厅灯已经打开，亮度调到了百分之四十。' for x in ['好的','收到','没问题','已处理','现在','你看','可以','设置完成']}
old={};new={}
for p in (ROOT/'runs/tts').glob('*.json'):
    d=json.loads(p.read_text('utf-8'))
    if d['text'] in texts:
        (new if d.get('termination_evidence_version')=='tts_token_eos_v1' else old)[d['text']]=d
if set(new)!=texts:raise ValueError('Incomplete actual TTS instrumentation probe')
if any(not d['ended'] or d['hit_frame_budget'] or d['codec_generated_tokens']>=d['max_codec_tokens'] for d in new.values()):raise ValueError('Inspect actual TTS termination evidence before full run')
compared=[{'text':t,'identical_wave_sha256':new[t]['sha256']==old[t]['sha256'],'old_batch_seed':old[t]['batch_seed'],'new_batch_seed':new[t]['batch_seed']} for t in sorted(texts & old.keys())]
report={'record_kind':'infrastructure_probe_not_benchmark_score','utterances':len(new),'all_eos_observed':True,'max_codec_tokens_observed':max(d['codec_generated_tokens'] for d in new.values()),'comparison_with_preinstrumentation_probe':compared,'generation_parameters_changed':False,'status':'passed'}
(ROOT/'reports/tts_termination_pilot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps(report,ensure_ascii=False))
