"""Overlap cloud audio judging with local inference/TTS, without duplicate case jobs."""
import argparse,collections,concurrent.futures,hashlib,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.judge_runs import evaluate,PROMPT,save,judgment_current,attach_baseline,EVIDENCE_VERSION
from homevoice.speech_text import VERSION
from homevoice.cloud import redact
ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=16);args=ap.parse_args()
report_path=ROOT/'reports/judge_stream_status.json';prompt_hash=hashlib.sha256(PROMPT.encode()).hexdigest()
cases={p.stem:json.loads(p.read_text('utf-8')) for p in (ROOT/'data/cases').glob('*.json')}
if report_path.exists():
    previous=json.loads(report_path.read_text('utf-8'))
    if previous.get('status')=='running' and time.time()-previous.get('heartbeat',0)<60:raise RuntimeError('A current judge stream already owns scoring')
done=set();lookup={};audio_seen=set();attempts=collections.Counter();retry_after={};failures={};counters=collections.Counter();futures={};active=set();started=time.time();last_print=0
def status(state,run_count=0,ready_count=0):
    save(report_path,{'status':state,'pid':os.getpid(),'workers':args.workers,'started_at_unix':started,'heartbeat':time.time(),'prompt_sha256':prompt_hash,'resolved_cases':len(done),'observed_run_files':run_count,'ready_unresolved':ready_count,'in_flight':len(futures),'counts':dict(counters),'persistent_errors':[{'run':k,'attempts':attempts[k],'error':v} for k,v in failures.items() if attempts[k]>=3]})
status('running');print(json.dumps({'judge_stream_ready':args.workers}),flush=True)
try:
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        while True:
            for p in (ROOT/'runs/tts').glob('*.json'):
                if p.name in audio_seen:continue
                d=json.loads(p.read_text('utf-8'));audio_seen.add(p.name)
                if d.get('normalizer_version')==VERSION and d.get('termination_evidence_version')=='tts_token_eos_v1':lookup[d['text']]=d
            for future in list(futures):
                if not future.done():continue
                key=futures.pop(future);active.remove(key)
                try:
                    result=future.result();counters[result]+=1
                    if result!='pending_audio':done.add(key);failures.pop(key,None)
                except Exception as e:
                    failures[key]=redact(e);retry_after[key]=time.time()+30;print(json.dumps({'run':key,'error':failures[key],'attempts':attempts[key]},ensure_ascii=False),flush=True)
            paths=[p for system in ['edge_native','qwen35_2b','qwen35_4b'] for p in (ROOT/'runs'/system).glob('*.json')];ready=0
            for p in paths:
                key=p.relative_to(ROOT).as_posix()
                if key in done or key in active:continue
                # Do not parse gigabytes of unrelated trajectories while all workers
                # are occupied. Completed responses are committed by evaluate itself.
                if len(futures)>=args.workers:break
                r=json.loads(p.read_text('utf-8'));j=r.get('audio_judge')
                attach_baseline(r,lookup)
                if judgment_current(cases[r['case_id']],r):done.add(key);counters['cached']+=1;continue
                if r.get('judge_status') in ['not_applicable_no_completed_audio_turn','not_applicable_empty_response'] and r.get('case_pass') is False:done.add(key);counters['cached_execution_failure']+=1;continue
                eligible=not r['turns'] or any(not t.get('assistant_text','').strip() for t in r['turns']) or all(t.get('assistant_audio') or (r['system_id'].startswith('qwen35_') and t['assistant_text'].strip() in lookup) for t in r['turns'])
                if not eligible:continue
                ready+=1
                if attempts[key]>=3 or time.time()<retry_after.get(key,0) or len(futures)>=args.workers:continue
                attempts[key]+=1;active.add(key);futures[pool.submit(evaluate,p,lookup)]=key
            if len(done)==3000:status('completed',len(paths),ready);break
            permanent={k for k in failures if attempts[k]>=3}
            if len(paths)==3000 and len(done)+len(permanent)==3000 and not futures:status('needs_attention',len(paths),ready);raise RuntimeError('Persistent judge errors require inspection')
            status('running',len(paths),ready)
            if len(done)-last_print>=20:print(json.dumps({'resolved':len(done),'runs_available':len(paths),'in_flight':len(futures),'ready':ready}),flush=True);last_print=len(done)
            time.sleep(1)
except BaseException:
    status('needs_attention');raise
print(json.dumps({'judge_stream_completed':len(done)}),flush=True)
