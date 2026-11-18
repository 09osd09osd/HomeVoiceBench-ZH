"""Batched local ASR/TTS in their original isolated environments."""
import argparse,gc,hashlib,json,os,shutil,sys,tempfile,time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT,SHARED_ROOT
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.speech_text import normalize,VERSION
from homevoice.paths import model_path
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HOME']=str(ROOT/'runtime/hf');os.environ['NUMBA_CACHE_DIR']=str(ROOT/'runtime/numba')
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),'utf-8');tmp.replace(p)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['asr','tts']);ap.add_argument('--batch-size',type=int,default=8,help='Initial batch size; ASR and pilot use this fixed size');ap.add_argument('--max-batch-size',type=int,default=64,help='TTS may grow up to this size after measured low-memory batches; set equal to batch-size to disable growth');ap.add_argument('--limit',type=int,default=0);ap.add_argument('--pilot',action='store_true');ap.add_argument('--diagnose');args=ap.parse_args()
    if args.batch_size<1 or args.max_batch_size<1:raise ValueError('Batch sizes must be positive')
    import numpy as np,soundfile as sf,torch,transformers
    torch.set_num_threads(6);torch.manual_seed(42)
    gpu_memory_fraction=.70
    torch.cuda.set_per_process_memory_fraction(gpu_memory_fraction,0)
    if args.mode=='asr':
        import importlib.util
        src=Path(importlib.util.find_spec('nagisa').submodule_search_locations[0]);temp=Path(tempfile.gettempdir())/'homevoice_nagisa'
        shutil.copytree(src,temp/'nagisa',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'));sys.path.insert(0,str(temp))
        from qwen_asr import Qwen3ASRModel
        asr_budget=1024 if os.getenv('HOMEVOICE_ASR_OUTPUTS')=='1' else 256
        model=Qwen3ASRModel.from_pretrained(str(model_path('asr_model')),dtype=torch.bfloat16,device_map='cuda:0',attn_implementation='sdpa',local_files_only=True,max_inference_batch_size=args.batch_size,max_new_tokens=asr_budget)
        tasks=[]
        referenced={a['sha256'] for p in (ROOT/'data/cases').glob('*.json') for a in json.loads(p.read_text('utf-8'))['variants'][0]['audio_assets'] if a.get('sha256')}
        for p in sorted((ROOT/'data/audio').glob('*.json')):
            m=json.loads(p.read_text('utf-8'))
            if m['status']=='verified' and m['sha256'] in referenced:tasks.append({'path':ROOT/m['path'],'sha256':m['sha256']})
        if args.pilot:
            p=ROOT/'assets/audio/pilot/user.wav';tasks=[{'path':p,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]*args.batch_size
        if args.diagnose:
            p=ROOT/args.diagnose;tasks=[{'path':p,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]
        if os.getenv('HOMEVOICE_ASR_OUTPUTS')=='1':
            tasks=[];lookup={}
            for p in (ROOT/'runs/tts').glob('*.json'):
                m=json.loads(p.read_text('utf-8'));lookup[m['text']]=m
            # Transcribe only audio used by current cases, not orphaned cached
            # answers from archived development protocols or performance probes.
            for system in ['edge_native','qwen35_2b','qwen35_4b']:
                for p in (ROOT/'runs'/system).glob('*.json'):
                    r=json.loads(p.read_text('utf-8'))
                    for t in r['turns']:
                        m=t.get('assistant_audio') or (lookup.get(t['assistant_text'].strip()) if system.startswith('qwen35_') else None)
                        if m:tasks.append({'path':ROOT/m['path'],'sha256':m['sha256']})
            tasks=list({t['sha256']:t for t in tasks}.values())
        outdir=ROOT/('runs/output_asr' if os.getenv('HOMEVOICE_ASR_OUTPUTS')=='1' else 'runs/asr');tasks=[t for t in tasks if args.pilot or not (outdir/(t['sha256']+'.json')).exists()]
        model_id='Qwen/Qwen3-ASR-0.6B';generation={'max_new_tokens':asr_budget,'language':'Chinese','purpose':'independent_output_audio_evidence' if os.getenv('HOMEVOICE_ASR_OUTPUTS')=='1' else 'baseline_input_transcription'}
    else:
        from qwen_tts import Qwen3TTSModel
        modeldir=model_path('tts_model')
        generation=json.loads((modeldir/'generation_config.json').read_text('utf-8'));generation['max_new_tokens']=1024
        model=Qwen3TTSModel.from_pretrained(str(modeldir),dtype=torch.bfloat16,device_map='cuda:0',attn_implementation='sdpa',local_files_only=True)
        termination=[];original_generate=model.model.talker.generate
        def observed_generate(*positional,**kwargs):
            # Observe the original result without changing inputs, sampling or weights.
            result=original_generate(*positional,**kwargs);sequences=result.sequences.detach().cpu().tolist();eos=kwargs['eos_token_id'];eos=set(eos if isinstance(eos,list) else [eos]);termination.clear()
            for seq in sequences:
                first=next((i for i,t in enumerate(seq) if t in eos),None)
                termination.append({'termination_evidence_version':'tts_token_eos_v1','ended':first is not None,'hit_frame_budget':first is None and len(seq)>=kwargs['max_new_tokens'],'codec_generated_tokens':first+1 if first is not None else len(seq),'max_codec_tokens':kwargs['max_new_tokens']})
            return result
        model.model.talker.generate=observed_generate
        texts=set()
        for p in (ROOT/'runs').glob('qwen35_*/*.json'):
            d=json.loads(p.read_text('utf-8'))
            for t in d.get('turns',[]):
                if t.get('assistant_text','').strip():texts.add(t['assistant_text'].strip())
        if args.pilot:texts={f'{x}，客厅灯已经打开，亮度调到了百分之四十。' for x in ['好的','收到','没问题','已处理','现在','你看','可以','设置完成'][:args.batch_size]}
        tasks=[{'text':t,'spoken_text':normalize(t),'key':hashlib.sha256(json.dumps({'text':t,'model':'Qwen3-TTS-0.6B','speaker':'Vivian','generation':generation,'seed':42,'normalizer':VERSION,'termination_evidence':'tts_token_eos_v1'},sort_keys=True,ensure_ascii=False).encode()).hexdigest()} for t in sorted(texts,key=lambda t:(len(t),t))]
        outdir=ROOT/'runs/tts';tasks=[t for t in tasks if args.pilot or not (outdir/(t['key']+'.json')).exists()]
        model_id='Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice'
    if args.mode=='asr' and os.getenv('HOMEVOICE_ASR_OUTPUTS')=='1':
        # Auxiliary output transcription only: group by observed waveform length
        # to reduce padding. Baseline input ASR and all model answers are unchanged.
        for task in tasks:task['duration_s']=float(sf.info(str(task['path'])).duration)
        tasks.sort(key=lambda task:(task['duration_s'],task['sha256']))
    if args.limit:tasks=tasks[:args.limit]
    maximum_batch=max(args.batch_size,args.max_batch_size) if args.mode=='tts' and not args.pilot else args.batch_size
    metadata={'model':model_id,'batch_size':args.batch_size,'adaptive_max_batch_size':maximum_batch,'torch':torch.__version__,'transformers':transformers.__version__,'cuda':torch.version.cuda,'dtype':'bfloat16','attention':'sdpa','seed':42,'generation':generation,'timing_scope':'offline_batch_inference_not_realtime_latency','pilot':args.pilot}
    metadata['allocator_cache_policy']='release_unused_after_each_batch'
    metadata['cuda_allocator_memory_fraction']=gpu_memory_fraction
    if args.mode=='asr':metadata['batch_order']='wave_duration_then_sha256' if os.getenv('HOMEVOICE_ASR_OUTPUTS')=='1' else 'input_metadata_order'
    stage='output_asr' if args.mode=='asr' and os.getenv('HOMEVOICE_ASR_OUTPUTS')=='1' else args.mode
    if not args.diagnose:save(ROOT/'reports'/f'{stage}_effective.json',metadata)
    print(json.dumps({'ready':args.mode,'tasks':len(tasks),'batch_size':args.batch_size}),flush=True)
    started=time.monotonic();invocation=time.time_ns();batches=[];resource_retries=[];batch_adjustments=[];active_batch=args.batch_size;offset=0;growth_allowed=True
    with torch.inference_mode():
        while offset<len(tasks):
            batch=tasks[offset:offset+active_batch]
            if args.mode=='tts':
                length=len(batch[0]['spoken_text']);batch=[t for t in batch if len(t['spoken_text'])<=max(length*1.5,length+40)]
            t0=time.monotonic();torch.cuda.reset_peak_memory_stats()
            if args.mode=='asr':
                outputs=model.transcribe(audio=[str(t['path']) for t in batch],language='Chinese')
                if len(outputs)!=len(batch):raise ValueError('ASR batch output count mismatch')
                if args.diagnose:print(json.dumps({'diagnostic_transcriptions':[o.text for o in outputs]},ensure_ascii=False),flush=True)
                for t,o in zip(batch,outputs):save(outdir/(t['sha256']+'.json'),{'audio_sha256':t['sha256'],'text':o.text,'language':o.language,'model':model_id,'ground_truth_supplied':False})
            else:
                # Fixed order + batch membership are recorded; batched sampling is reproducible only with both.
                torch.manual_seed(42+offset)
                try:
                    waves,sr=model.generate_custom_voice(text=[t['spoken_text'] for t in batch],language='Chinese',speaker='Vivian',non_streaming_mode=True,**generation)
                except (torch.OutOfMemoryError,MemoryError) as exc:
                    # No output in this batch has been saved or scored. Retry only
                    # a measured resource failure, never an answer-quality failure.
                    attempt={'mode':'tts','offset':offset,'attempted_batch_size':len(batch),'batch_keys':[t['key'] for t in batch],'batch_seed':42+offset,'reason':type(exc).__name__+': '+str(exc),'peak_gpu_bytes':torch.cuda.max_memory_allocated(),'retry_batch_size':max(1,len(batch)//2)}
                    resource_retries.append(attempt);save(ROOT/'reports/speech_resource_attempts'/f'tts_{time.time_ns()}.json',attempt)
                    if len(batch)==1:raise
                    active_batch=attempt['retry_batch_size'];growth_allowed=False;exc.__traceback__=None;gc.collect();torch.cuda.empty_cache()
                    print(json.dumps({'tts_resource_retry':attempt['offset'],'batch_size':active_batch}),flush=True);continue
                if len(waves)!=len(batch) or len(termination)!=len(batch):raise ValueError('TTS batch output/evidence count mismatch')
                for t,w,stop in zip(batch,waves,termination):
                    w=np.asarray(w,dtype=np.float32)
                    if not w.size or not np.isfinite(w).all():raise ValueError('invalid local TTS waveform')
                    p=ROOT/'assets/audio/baseline'/f'{t["key"]}.wav';p.parent.mkdir(parents=True,exist_ok=True);sf.write(str(p),w,sr,subtype='PCM_16')
                    save(outdir/(t['key']+'.json'),{'text':t['text'],'spoken_text':t['spoken_text'],'normalizer_version':VERSION,'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'duration_s':len(w)/sr,'sample_rate_hz':sr,'model':model_id,'external_cloud_tts':False,'batch_offset':offset,'batch_seed':42+offset,'batch_keys':[b['key'] for b in batch],**stop})
            torch.cuda.synchronize();elapsed=time.monotonic()-t0;batches.append({'offset':offset,'n':len(batch),'seconds':elapsed,'peak_gpu_bytes':torch.cuda.max_memory_allocated(),'reserved_gpu_bytes_before_release':torch.cuda.memory_reserved()})
            # Variable codec lengths can fragment the allocator and retain far
            # more reserved memory than active tensors on Windows WDDM.
            # Release unused allocations only; model tensors and sampling stay unchanged.
            torch.cuda.empty_cache();batches[-1]['reserved_gpu_bytes_after_release']=torch.cuda.memory_reserved()
            print(json.dumps({'mode':args.mode,'done':offset+len(batch),'total':len(tasks),'batch_seconds':round(elapsed,3),'peak_gpu_gib':round(torch.cuda.max_memory_allocated()/2**30,2)}),flush=True)
            offset+=len(batch)
            save(ROOT/'reports/speech_batches'/f'{stage}_{invocation}.json',{**metadata,'status':'running','tasks':len(tasks),'completed_tasks':offset,'wall_seconds':time.monotonic()-started,'batches':batches,'resource_retries':resource_retries,'batch_adjustments':batch_adjustments})
            # Grow only after actual successful low-memory batches. This changes
            # throughput/membership, not model parameters or score-based selection.
            if args.mode=='tts' and not args.pilot and growth_allowed and len(batches)>=2 and offset<len(tasks) and active_batch<maximum_batch and torch.cuda.max_memory_allocated()<6*2**30 and torch.cuda.mem_get_info()[0]>8*2**30:
                change={'offset':offset,'from':active_batch,'to':min(maximum_batch,active_batch*2),'reason':'two_or_more_successful_batches_and_measured_gpu_headroom','previous_peak_gpu_bytes':torch.cuda.max_memory_allocated()}
                active_batch=change['to'];batch_adjustments.append(change);save(ROOT/'reports/speech_batch_adjustments'/f'tts_{time.time_ns()}.json',change);print(json.dumps({'tts_batch_growth':change}),flush=True)
    report={**metadata,'status':'completed','tasks':len(tasks),'completed_tasks':offset,'wall_seconds':time.monotonic()-started,'batches':batches,'final_batch_size':active_batch,'resource_retries':resource_retries,'batch_adjustments':batch_adjustments}
    save(ROOT/'reports/speech_batches'/f'{stage}_{invocation}.json',report)
    save(ROOT/'reports'/f'{stage}_{"diagnostic" if args.diagnose else "pilot" if args.pilot else "batches"}.json',report)
if __name__=='__main__':main()
