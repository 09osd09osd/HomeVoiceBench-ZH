"""One isolated native Edge model per worker. No external ASR/TTS or GT transcript."""
import argparse,concurrent.futures,copy,functools,hashlib,json,os,queue,re,subprocess,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT,SHARED_ROOT;sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.speech_text import normalize,VERSION
from homevoice.paths import model_path
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HOME']=str(ROOT/'runtime/hf');os.environ['HF_MODULES_CACHE']=str(ROOT/'runtime/hf_modules')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=18931);ap.add_argument('--batch-size',type=int,default=4);args=ap.parse_args()
    import numpy as np,soundfile as sf,torch,transformers
    from transformers import AutoModel,AutoProcessor
    from transformers.dynamic_module_utils import get_class_from_dynamic_module
    torch.set_num_threads(4);torch.manual_seed(42)
    modeldir=model_path('edge_model')
    processor=AutoProcessor.from_pretrained(str(modeldir),trust_remote_code=True,local_files_only=True)
    started=time.monotonic()
    model,info=AutoModel.from_pretrained(str(modeldir),trust_remote_code=True,local_files_only=True,dtype='auto',device_map='cuda:0',attn_implementation='sdpa',output_loading_info=True)
    if any(info.get(k) for k in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']):raise ValueError('checkpoint loading mismatch')
    model.eval().requires_grad_(False)
    Session=get_class_from_dynamic_module('duplex_edgeinstant.DuplexSession',str(modeldir),local_files_only=True)
    native=sys.modules[Session.__module__]
    with torch.inference_mode():session=Session(model,processor,trace=False)
    session.close() # Keep the model's prepared codec/talker; no live microphone threads.
    torch.cuda.empty_cache()
    config={'model':'EdgeInstant-Omni-2B-1106-Preview','native_audio_input':True,'native_audio_output':True,'external_asr':False,'external_tts':False,'torch':torch.__version__,'transformers':transformers.__version__,'cuda':torch.version.cuda,'dtype':'published mixed BF16/FP32, auto','attention':'sdpa','max_new_tokens':256,'do_sample':False,'seed':42,'normalizer_version':VERSION,'context_limit':8192,'port':args.port,'pid':os.getpid(),'load_seconds':time.monotonic()-started,'batch_size_per_worker':1,'parallelism':'independent model workers; no shared mutable talker state'}
    config.update(batch_size_per_worker=args.batch_size,parallelism='batched native audio/text inference, serialized native talker; one weight copy',batch_wait_ms=10)
    (ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports'/f'edge_worker_{args.port}.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),'utf-8')
    lock=threading.Lock();ffmpeg=model_path('ffmpeg')
    @functools.lru_cache(maxsize=512)
    def decoded_audio(path_string,mtime,size):
        path=Path(path_string)
        w=np.frombuffer(subprocess.check_output([str(ffmpeg),'-v','error','-i',str(path),'-ac','1','-ar','16000','-f','f32le','pipe:1']),dtype=np.float32).copy()
        features=processor.audio_features(w,sampling_rate=16000,return_tensors='pt')
        count=processor.audio_token_count(int(features['attention_mask'].sum()))
        return w,count,hashlib.sha256(path.read_bytes()).hexdigest()
    def pcm(path):
        path=Path(path).resolve()
        if not path.is_relative_to((ROOT/'assets').resolve()):raise ValueError('audio path outside benchmark assets')
        stat=path.stat();return decoded_audio(str(path),stat.st_mtime_ns,stat.st_size)
    processor.tokenizer.padding_side='left'
    if processor.tokenizer.pad_token_id is None:processor.tokenizer.pad_token=processor.tokenizer.eos_token
    def prepare(messages,tools):
        messages=copy.deepcopy(messages);waves=[];evidence=[]
        for m in messages:
            for tc in m.get('tool_calls',[]):
                if isinstance(tc['function'].get('arguments'),str):tc['function']['arguments']=json.loads(tc['function']['arguments'])
            if not isinstance(m.get('content'),list):continue
            parts=[]
            for part in m['content']:
                if part['type']!='audio':raise ValueError('native user input must be audio only')
                path=Path(part['audio']);w,count,digest=pcm(path)
                waves.append(w);parts.append('<|audio_start|>'+'<|audio_pad|>'*count+'<|audio_end|>');evidence.append({'sha256':digest,'seconds':len(w)/16000})
            m['content']=''.join(parts)
        rendered=processor.tokenizer.apply_chat_template(messages,tools=tools or None,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        length=len(processor.tokenizer.encode(rendered,add_special_tokens=False))
        if length+256>8192:raise ValueError('context_budget_exceeded')
        return rendered,waves,evidence,length
    pending=queue.Queue();batch_counter=0
    def infer_batches():
        nonlocal batch_counter
        while True:
            jobs=[pending.get()];deadline=time.monotonic()+.01
            while len(jobs)<args.batch_size:
                try:jobs.append(pending.get(timeout=max(.0001,deadline-time.monotonic())))
                except queue.Empty:break
                if time.monotonic()>=deadline:break
            valid=[];prepared=[]
            try:
                with lock,torch.inference_mode():
                    for data,future in jobs:
                        try:prepared.append(prepare(data['messages'],data.get('tools',[])));valid.append((data,future))
                        except Exception as e:future.set_exception(e)
                    if not valid:continue
                    before=time.monotonic();batch_counter+=1;rendered=[x[0] for x in prepared];waves=[w for x in prepared for w in x[1]]
                    inputs=processor.tokenizer(rendered,padding=True,return_tensors='pt',add_special_tokens=False)
                    if waves:
                        f=processor.audio_features(waves,sampling_rate=16000,return_tensors='pt');inputs['input_features']=f['input_features'];inputs['feature_attention_mask']=f['attention_mask']
                    inputs={k:v.to('cuda:0') for k,v in inputs.items()};padded=inputs['input_ids'].shape[1];torch.manual_seed(42)
                    output=model.generate(**inputs,max_new_tokens=256,do_sample=False);sequences=output[:,padded:].cpu().tolist();eos=model.config.eos_token_id;eos=set(eos if isinstance(eos,list) else [eos]);torch.cuda.synchronize()
                    members=[hashlib.sha256((x[0]+json.dumps(x[2],sort_keys=True)).encode()).hexdigest() for x in prepared]
                    results=[]
                    for i,seq in enumerate(sequences):
                        end=next((j+1 for j,token in enumerate(seq) if token in eos),len(seq));tokens=seq[:end];ended=bool(tokens and tokens[-1] in eos)
                        raw=processor.decode(tokens,skip_special_tokens=False);raw=re.split(r'<\|im_end\|>|<\|endoftext\|>',raw)[0].strip()
                        results.append({'raw_output':raw,'input_tokens':prepared[i][3],'padded_input_tokens':padded,'generated_tokens':len(tokens),'finish_reason':'stop' if ended or len(tokens)<256 else 'length','audio_evidence':prepared[i][2],'external_asr':False,'batch_size':len(valid),'batch_id':f'{os.getpid()}_{batch_counter}','batch_index':i,'batch_members':members,'batch_wall_seconds':time.monotonic()-before,'gpu_allocated_bytes':torch.cuda.memory_allocated(),'gpu_reserved_bytes':torch.cuda.memory_reserved()})
                    for result in results:result['audio_decode_cache']=decoded_audio.cache_info()._asdict()
                    del inputs,output
                for (_,future),result in zip(valid,results):future.set_result(result)
            except Exception as e:
                torch.cuda.empty_cache()
                for _,future in jobs:
                    if not future.done():future.set_exception(e)
    threading.Thread(target=infer_batches,daemon=True).start()
    def speak(raw):
        text=normalize(raw);key=hashlib.sha256((VERSION+'\n'+text).encode()).hexdigest();path=ROOT/'assets/audio/edge'/f'{key}.wav';meta_path=ROOT/'runs/edge_audio'/f'{key}.json'
        if meta_path.exists() and path.exists():return json.loads(meta_path.read_text('utf-8'))
        before=time.monotonic();torch.manual_seed(42);language='chinese' if re.search('[一-鿿]',text) else 'english';body=processor.tokenizer.encode(text,add_special_tokens=False)
        model.talker.text_embedding.table=model.reply_features(body,language);model.codec_stream.reset();talk=model.talker.new_state(language=language)
        for i in range(len(body)):talk.push_token(i)
        talk.end_input();sent=0;parts=[];limit=min(1024,native.FRAMES_PER_TOKEN*len(body)+native.FRAMES_SLACK)
        while not talk.ended and len(talk.frames)<=limit:
            talk.advance(max_new_frames=4)
            if len(talk.frames)>sent:
                parts.append(model.codec_stream(torch.stack(talk.frames[sent:]).unsqueeze(0)).reshape(-1).cpu().numpy());sent=len(talk.frames)
        wave=np.concatenate(parts) if parts else np.zeros(0,dtype=np.float32)
        if not wave.size or not np.isfinite(wave).all():raise ValueError('invalid native waveform')
        path.parent.mkdir(parents=True,exist_ok=True);sf.write(str(path),wave,model.codec.sample_rate,subtype='PCM_16')
        meta={'raw_text':raw,'spoken_text':text,'normalizer_version':VERSION,'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'duration_s':len(wave)/model.codec.sample_rate,'sample_rate_hz':model.codec.sample_rate,'model':config['model'],'external_tts':False,'ended':talk.ended,'hit_frame_budget':not talk.ended,'wall_seconds':time.monotonic()-before}
        meta_path.parent.mkdir(parents=True,exist_ok=True);meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2),'utf-8');return meta
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def reply(self,code,data):
            b=json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        def do_GET(self):self.reply(200,{'status':'ready','config':config}) if self.path=='/health' else self.reply(404,{'error':'unknown_route'})
        def do_POST(self):
            try:
                size=int(self.headers.get('Content-Length',0))
                if not 0<size<=4*1024*1024:raise ValueError('request_size')
                data=json.loads(self.rfile.read(size));before=time.monotonic()
                if self.path=='/infer':
                    future=concurrent.futures.Future();pending.put((data,future));result=future.result(timeout=180)
                elif self.path=='/speak':
                    with lock,torch.inference_mode():
                        result=speak(data['text']);torch.cuda.synchronize();torch.cuda.empty_cache()
                else:raise ValueError('unknown_route')
                result['worker_wall_seconds']=time.monotonic()-before
                self.reply(200,result)
            except Exception as e:self.reply(500,{'error':str(e),'type':type(e).__name__})
    print(json.dumps({'edge_ready':args.port,'pid':os.getpid(),'load_seconds':config['load_seconds']}),flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
if __name__=='__main__':main()
