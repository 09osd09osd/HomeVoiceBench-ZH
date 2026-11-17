"""Resume cloud-only work after an inspected scheduler infrastructure failure."""
import datetime,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.judge_runs import save

path=ROOT/'reports/revision/pipeline_status.json';status=json.loads(path.read_text('utf-8'))
failure=ROOT/'reports/revision/judge_windows_lock_recovery.json'
if not failure.exists():save(failure,{'prior_pipeline':status,'reason':'Windows sharing violation while atomically replacing judge_stream_status.json; traceback retained in local log. Completed requests drained before restart. Added bounded atomic-replace retries; no prompt, grading or model-output changes.'})
status.update(status='running',current_stage='audio_judging_resumed');status.pop('error',None)
status['stages'].append({'name':'audio_judging_resumed','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workers':32})
status['policy']='one GPU engine at a time; native microbatch4, Qwen4 slots, TTS18; cloud judge initially16 then32; interrupted status writer resumed without model reruns'
save(path,status)
def run(name,script,*args):
    with (ROOT/'logs'/('v03-resume-'+name+'.log')).open('w',encoding='utf-8') as log:
        p=subprocess.Popen([sys.executable,'-X','utf8','scripts/'+script,*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
        print(json.dumps({'started':name,'pid':p.pid}),flush=True)
        while p.poll() is None:time.sleep(2)
        if p.returncode:raise RuntimeError(name+' failed; inspect its log')
try:
    run('judge-stream','judge_stream.py','--workers','32')
    run('judge-final','judge_runs.py','--workers','16')
    run('summarize','summarize.py')
    if json.loads((ROOT/'reports/summary.json').read_text('utf-8'))['evaluation_status']!='complete':raise RuntimeError('Some judgments remain unresolved')
    status.update(status='completed',current_stage='summarize',finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat());save(path,status)
    print(json.dumps({'evaluation':'completed'}),flush=True)
except Exception as e:
    status.update(status='needs_attention',error=str(e));save(path,status);raise
