"""Resumable staged GPU evaluation. Parallel work shares one model per stage."""
import datetime,json,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.paths import model_path
HIDDEN=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
status={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'policy':'one GPU engine at a time; native microbatch4, Qwen4 slots, TTS18 with allocator cap and unused-cache release; overlapping cloud judge16','stages':[]};owned=[]
def save():
    target=ROOT/'reports/revision/pipeline_status.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(status,ensure_ascii=False,indent=2),'utf-8');temp.replace(target)
def stage(name):
    status['current_stage']=name;status['stages'].append({'name':name,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat()});save();print(json.dumps({'stage':name}),flush=True)
def spawn(name,command):
    path=ROOT/'logs'/f'v03-pipeline-{name}.log';path.parent.mkdir(exist_ok=True);log=path.open('w',encoding='utf-8')
    p=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=HIDDEN);owned.append((p,log));return p
def run(name,command):
    p=spawn(name,command)
    while p.poll() is None:time.sleep(3)
    if p.returncode:raise RuntimeError(f'{name} exited {p.returncode}; inspect logs/v03-pipeline-{name}.log')
def health(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=3) as r:return json.load(r)
    except Exception:return None
def wait_health(port,process=None):
    for _ in range(60):
        if health(port):return
        if process and process.poll() is not None:raise RuntimeError('server exited before readiness')
        time.sleep(3)
    raise RuntimeError('server readiness timeout')
def stop_owned_pid(pid,expected):
    # The only externally retained process is our already running Edge worker.
    # psutil belongs to the model environment, not the bundled authoring runtime.
    helper="""import psutil,sys
from pathlib import Path
p=psutil.Process(int(sys.argv[1]));cmd=' '.join(p.cmdline()).replace(chr(92),'/')
if sys.argv[2] not in cmd or Path(p.cwd()).resolve()!=Path(sys.argv[3]).resolve():raise ValueError('refusing to stop a process outside this benchmark')
p.terminate()
try:p.wait(30)
except psutil.TimeoutExpired:p.kill();p.wait(10)
"""
    subprocess.run([str(model_path('edge_python')),'-X','utf8','-c',helper,str(pid),expected,str(ROOT)],check=True,creationflags=HIDDEN)
def ensure_count(system):
    n=len(list((ROOT/'runs'/system).glob('*.json')))
    if n!=1000:raise RuntimeError(f'{system}: {n}/1000 run files')
try:
    manifest=json.loads((ROOT/'data/manifest.json').read_text('utf-8'))
    if len(manifest['cases'])!=1000:raise ValueError('complete frozen dataset required')
    if manifest['version']!='0.3.0':raise ValueError('Freeze v0.3 before execution')
    stream_path=ROOT/'reports/judge_stream_status.json'
    spawn('judge-stream',[sys.executable,'-X','utf8','scripts/judge_stream.py','--workers','16'])
    stage('new_input_asr_batch16')
    run('input-asr',[str(model_path('asr_python')),'-X','utf8','scripts/batch_speech.py','asr','--batch-size','16'])
    stage('edge_native_batch4')
    if len(list((ROOT/'runs/edge_native').glob('*.json')))<1000:
        if not health(18931):spawn('edge-server',[str(model_path('edge_python')),'-X','utf8','scripts/edge_worker.py','--port','18931','--batch-size','4'])
        wait_health(18931);run('edge-runs',[sys.executable,'-X','utf8','scripts/run_models.py','--system','edge_native','--urls','http://127.0.0.1:18931','--workers','4'])
    ensure_count('edge_native')
    if health(18931):stop_owned_pid(json.loads((ROOT/'reports/edge_worker_18931.json').read_text('utf-8'))['pid'],'scripts/edge_worker.py')
    for size in ['2B','4B']:
        system='qwen35_'+size.lower();stage(system)
        if len(list((ROOT/'runs'/system).glob('*.json')))<1000:
            if health(18941):raise RuntimeError('A retained Qwen server is active; verify its model and stop the owned process before resuming.')
            p=spawn('qwen-'+size,[sys.executable,'-X','utf8','scripts/launch_qwen.py','--size',size,'--port','18941','--slots','4']);wait_health(18941,p)
            run('qwen-'+size+'-runs',[sys.executable,'-X','utf8','scripts/run_models.py','--system',system,'--urls','http://127.0.0.1:18941','--workers','4']);ensure_count(system)
            stop_owned_pid(json.loads((ROOT/'reports'/f'qwen_{size}_runtime.json').read_text('utf-8'))['server_pid'],'llama-server.exe');p.wait(30)
        ensure_count(system)
    if not (ROOT/'reports/tts_termination_pilot.json').exists():
        stage('tts_termination_probe');run('tts-probe',[str(model_path('tts_python')),'-X','utf8','scripts/batch_speech.py','tts','--pilot','--batch-size','8']);run('tts-probe-check',[sys.executable,'-X','utf8','scripts/verify_tts_probe.py'])
    stage('baseline_tts_batch18');run('baseline-tts',[str(model_path('tts_python')),'-X','utf8','scripts/batch_speech.py','tts','--batch-size','18','--max-batch-size','18'])
    stage('audio_judging')
    while stream_path.exists():
        stream=json.loads(stream_path.read_text('utf-8'))
        if stream.get('status')!='running':break
        if time.time()-stream.get('heartbeat',0)>120:raise RuntimeError('Judge stream heartbeat is stale; inspect the owned process before resuming')
        time.sleep(5)
    for attempt in range(3):
        run('judge-'+str(attempt+1),[sys.executable,'-X','utf8','scripts/judge_runs.py','--workers','16'])
        unresolved=[]
        for system in ['edge_native','qwen35_2b','qwen35_4b']:
            for p in (ROOT/'runs'/system).glob('*.json'):
                r=json.loads(p.read_text('utf-8'))
                if r.get('case_pass') is None:unresolved.append(system+'/'+p.stem)
        if not unresolved:break
    if unresolved:raise RuntimeError(f'{len(unresolved)} runs still lack actual judgments; inspect judging_status.json')
    stage('summarize');run('summarize',[sys.executable,'-X','utf8','scripts/summarize.py']);status['status']='completed';status['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();print(json.dumps({'status':'completed'}),flush=True)
except Exception as e:
    status.update(status='needs_attention',error=str(e));save();print(json.dumps({'error':str(e)}),flush=True);raise
finally:
    for p,log in owned:
        if p.poll() is not None:log.close()
