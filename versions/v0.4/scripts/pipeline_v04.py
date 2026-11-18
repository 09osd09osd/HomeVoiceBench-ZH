"""Resumable pilot/formal GPU schedule; never co-load benchmark backbones."""
import argparse,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT,CODE_ROOT,model_path

def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),'utf-8')
def health(url):
    try:
        with urllib.request.urlopen(url+'/health',timeout=3) as r:return r.status==200
    except Exception:return False
def launch(args,label,env=None):
    log=(ROOT/'logs'/f'{label}.log').open('w',encoding='utf-8')
    child_env=dict(env or os.environ);child_env['PYTHONUTF8']='1';child_env['PYTHONIOENCODING']='utf-8'
    p=subprocess.Popen([str(x) for x in args],cwd=CODE_ROOT,stdout=log,stderr=subprocess.STDOUT,env=child_env,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
    return p,log
def command(args,label,env=None):
    started=time.monotonic();p,log=launch(args,label,env);code=p.wait();log.close()
    result={'stage':label,'exit_code':code,'seconds':time.monotonic()-started,'log':f'logs/{label}.log'};print(json.dumps(result),flush=True)
    history.append(result);save(ROOT/'reports/pipeline.json',{'status':'running','stages':history})
    if code:raise RuntimeError('stage failed '+label)
    return result
def ready(p,url):
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        if p.poll() is not None:raise RuntimeError('model server exited during load')
        if health(url):return
        time.sleep(2)
    raise TimeoutError('server readiness timeout')
def stop(p,log,system):
    # Only our launcher's recorded child PID is terminated. Never touch other jobs.
    if system!='edge_native':
        report=ROOT/'reports'/f'qwen_{"2B" if system=="qwen35_2b" else "4B"}_runtime.json'
        child=json.loads(report.read_text('utf-8')).get('server_pid')
        if child:subprocess.run(['taskkill','/PID',str(child),'/T','/F'],capture_output=True)
    if p.poll() is None:p.terminate()
    try:p.wait(timeout=30)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    log.close()
def probes(system,url):
    # Fixed before seeing model output: two short tool, two medium tool, two chat.
    cases=[json.loads(p.read_text('utf-8')) for p in sorted((ROOT/'data/cases').glob('*.json'))]
    selected=[]
    for cat,n,count in [('tool',1,2),('tool',3,2),('chat',1,1),('chat',3,1)]:
        selected += [c['identity']['case_id'] for c in cases if c['classification']['category']==cat and len(c['interaction']['nodes'])==n][:count]
    records=[]
    for workers in [4,8]:
        label=f'{system}_workers{workers}'
        directory=ROOT/'runs/performance'/label/system
        if directory.exists() and len(list(directory.glob('*.json')))==len(selected):
            stage=next((s for s in previous_stages if s['stage']==label),None)
            if not stage:raise ValueError('Missing performance timing; do not invent speedup')
        else:stage=command([sys.executable,CODE_ROOT/'scripts/run_models.py','--system',system,'--urls',url,'--workers',str(workers),'--cases',','.join(selected),'--probe-label',label],label)
        rr=[json.loads(p.read_text('utf-8')) for p in directory.glob('*.json')]
        records.append({'workers':workers,'wall_seconds':stage['seconds'],'cases':selected,'infrastructure_errors':sum(bool((r['execution'].get('failure') or {}).get('infra_candidate')) for r in rr),'execution_failures':sum(r['execution']['status']=='failed' for r in rr),'model_calls':sum(r['execution']['model_calls'] for r in rr),'tool_calls':sum(r['execution']['tool_calls'] for r in rr),'cached_speech_caveat':system=='edge_native'})
    chosen=8 if records[1]['infrastructure_errors']==0 and records[1]['wall_seconds']<records[0]['wall_seconds'] else 4
    # Content failures never cause retries or best-answer selection.
    result={'system':system,'probes':records,'selected_workers':chosen,'speed_ratio_4_over_8':records[0]['wall_seconds']/records[1]['wall_seconds'],'scope':'offline pipeline throughput; same frozen six-case set, small diagnostic sample. Edge second probe can reuse speech WAV; this ratio is not native end-to-end speedup.'}
    save(ROOT/'reports'/f'concurrency_{system}.json',result);return chosen

history=[];previous_stages=[]
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--skip-probes',action='store_true');ap.add_argument('--workers',type=int,default=8);ap.add_argument('--start-at',choices=['all','edge','tts','judge'],default='all');a=ap.parse_args()
    old=ROOT/'reports/pipeline.json'
    if old.exists():previous_stages=json.loads(old.read_text('utf-8'))['stages'];history=list(previous_stages)
    paths=list((ROOT/'data/cases').glob('*.json'));expected=100 if ROOT.name=='pilot' else 1000
    if len(paths)!=expected or not all(json.loads(p.read_text('utf-8'))['variants'][0]['status']=='ready' for p in paths):raise ValueError('Input readiness gate requires all '+str(expected)+' cases')
    from scripts.freeze_dataset import freeze
    freeze()
    if ROOT.name=='benchmark':
        accepted=json.loads((CODE_ROOT/'pilot/reports/acceptance.json').read_text('utf-8'))
        if accepted['status']!='passed':raise ValueError('Development technical acceptance required before test inference')
    try:
        if a.start_at=='all':command([model_path('asr_python'),CODE_ROOT/'scripts/batch_speech.py','asr','--batch-size','16'],'input_asr')
        engines=[('qwen35_2b','2B',18941),('qwen35_4b','4B',18942),('edge_native',None,18931)]
        if a.start_at=='edge':engines=engines[-1:]
        if a.start_at in ['tts','judge']:engines=[]
        for system,size,port in engines:
            url=f'http://127.0.0.1:{port}'
            if health(url):raise RuntimeError('Port already owned; will not replace an existing model server')
            args=[model_path('edge_python'),CODE_ROOT/'scripts/edge_worker.py','--port',str(port),'--batch-size','8'] if size is None else [sys.executable,CODE_ROOT/'scripts/launch_qwen.py','--size',size,'--port',str(port),'--slots','8']
            p,log=launch(args,'server_'+system)
            try:
                ready(p,url)
                profile=CODE_ROOT/'pilot/reports'/f'concurrency_{system}.json'
                workers=(json.loads(profile.read_text('utf-8'))['selected_workers'] if profile.exists() else a.workers) if a.skip_probes else probes(system,url)
                save(ROOT/'reports'/f'worker_selection_{system}.json',{'workers':workers,'source':str(profile.relative_to(CODE_ROOT)) if a.skip_probes and profile.exists() else 'same_split_fixed_probe','server_slots':8})
                command([sys.executable,CODE_ROOT/'scripts/run_models.py','--system',system,'--urls',url,'--workers',str(workers)],'main_'+system)
            finally:stop(p,log,system)
        if a.start_at!='judge':
            command([model_path('tts_python'),CODE_ROOT/'scripts/batch_speech.py','tts','--batch-size','12','--max-batch-size','32'],'baseline_tts')
            env=os.environ.copy();env['HOMEVOICE_ASR_OUTPUTS']='1'
            command([model_path('asr_python'),CODE_ROOT/'scripts/batch_speech.py','asr','--batch-size','16'],'output_audio_transcription',env)
        command([sys.executable,CODE_ROOT/'scripts/judge_runs.py','--workers','24'],'audio_judge')
        command([sys.executable,CODE_ROOT/'scripts/review_semantics.py','--workers','24'],'semantic_review')
        command([sys.executable,CODE_ROOT/'scripts/check_audio_facts.py'],'audio_numeric_checks')
        command([sys.executable,CODE_ROOT/'scripts/adjudicate_audio.py','--workers','24'],'fresh_audio_adjudication')
        command([sys.executable,CODE_ROOT/'scripts/check_audio_facts.py'],'verified_audio_numeric_checks')
        command([sys.executable,CODE_ROOT/'scripts/summarize.py'],'summary')
        command([sys.executable,CODE_ROOT/'scripts/validate_completion.py'],'technical_acceptance')
        save(ROOT/'reports/pipeline.json',{'status':'completed','stages':history})
    except Exception as e:
        save(ROOT/'reports/pipeline.json',{'status':'failed','error':str(e),'stages':history});raise
