"""Overlap unchanged semantic reviews/adjudication with GPU and audio judging."""
import argparse,collections,concurrent.futures,json,os,subprocess,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT,CODE_ROOT
from homevoice.cloud import redact
from scripts.judge_runs import save
from scripts.review_semantics import process as review
from scripts.adjudicate_audio import process as adjudicate

def read(p):
    try:return json.loads(p.read_text('utf-8'))
    except (FileNotFoundError,json.JSONDecodeError):return {}

def process(path):
    # One owner handles both mutations in order. Each function preserves its
    # own first schema-valid request, prompt hash and evidence signature.
    first=review(path);second=adjudicate(path)
    return first,second

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=8);a=ap.parse_args()
    path=ROOT/'reports/scoring_followup_stream.json';previous=read(path)
    if previous.get('status')=='running' and time.time()-previous.get('heartbeat',0)<30:raise RuntimeError('A live follow-up stream already owns this split')
    state={'status':'running','phase':'overlap','pid':os.getpid(),'workers':a.workers,'started_at_unix':time.time(),'counts':{},'errors':[],'scope':'Unchanged fixed prompts and first-valid-response policy; scheduling only. Maximum 24 primary plus 8 follow-up requests.'}
    lock=threading.Lock();stop=threading.Event()
    def heartbeat():
        while not stop.is_set():
            with lock:save(path,{**state,'heartbeat':time.time()})
            stop.wait(2)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    seen={};active={};counts=collections.Counter();last_print=0
    try:
        with concurrent.futures.ThreadPoolExecutor(a.workers) as pool:
            while True:
                for future in list(active):
                    if not future.done():continue
                    p=active.pop(future);first,second=future.result()
                    counts['review_'+first]+=1;counts['audio_'+second]+=1
                    seen[str(p)]=p.stat().st_mtime_ns
                paths=[p for system in ['edge_native','qwen35_2b','qwen35_4b'] for p in (ROOT/'runs'/system).glob('*.json')]
                busy={str(p) for p in active.values()}
                for p in paths:
                    if len(active)>=a.workers:break
                    key=str(p)
                    if key in busy:continue
                    stamp=p.stat().st_mtime_ns
                    if seen.get(key)==stamp:continue
                    record=read(p)
                    if not record:continue
                    if not record.get('audio_judge'):
                        seen[key]=stamp;continue
                    active[pool.submit(process,p)]=p;busy.add(key)
                with lock:state.update(counts=dict(counts),in_flight=len(active),observed_run_files=len(paths))
                done=counts['review_agreed']+counts['review_disputed']
                if done-last_print>=50:print(json.dumps({'reviewed_during_inference':done,'adjudicated':counts['audio_adjudicated'],'in_flight':len(active)}),flush=True);last_print=done
                primary=read(ROOT/'reports/judge_stream_status.json');asr=read(ROOT/'reports/output_asr_batches.json')
                if primary.get('status')=='completed' and asr.get('status')=='completed' and not active:break
                if read(ROOT/'reports/pipeline.json').get('status')=='failed':raise RuntimeError('Main pipeline stopped; final batch can resume from saved reviews')
                time.sleep(2)
        with lock:state['phase']='numeric_evidence'
        for script,extra in [('check_audio_facts.py',[]),('adjudicate_audio.py',['--workers',str(a.workers)]),('check_audio_facts.py',[])]:
            subprocess.run([sys.executable,'-X','utf8',str(CODE_ROOT/'scripts'/script),*extra],cwd=CODE_ROOT,check=True)
        with lock:state.update(status='completed',phase='finished',finished_at_unix=time.time())
        print(json.dumps({'followup_completed':True,'counts':dict(counts)}),flush=True)
    except BaseException as e:
        with lock:state.update(status='needs_attention',errors=[redact(e)])
        raise
    finally:
        stop.set();thread.join(timeout=5)
        with lock:save(path,{**state,'heartbeat':time.time()})
