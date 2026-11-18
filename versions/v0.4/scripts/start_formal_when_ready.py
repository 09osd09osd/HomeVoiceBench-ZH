"""Task-local orchestrator: overlap cloud scoring and GPU work after verified inputs."""
import json,os,subprocess,sys,time
from pathlib import Path
CODE=Path(__file__).resolve().parents[1];ROOT=CODE/'benchmark'
env={**os.environ,'HOMEVOICE_DATA_ROOT':str(ROOT),'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'}
def read(p):
    try:return json.loads(p.read_text('utf-8'))
    except (FileNotFoundError,json.JSONDecodeError):return {}

if __name__=='__main__':
    print('Waiting for formal input freeze and repaired pilot acceptance.',flush=True)
    while True:
        acceptance=read(CODE/'pilot/reports/acceptance.json');pipeline=read(CODE/'pilot/reports/pipeline.json')
        if (ROOT/'data/manifest.json').exists() and acceptance.get('status')=='passed':break
        if pipeline.get('status')=='failed' and (CODE/'docs/FULL_RUN_AUTHORIZATION.json').stat().st_mtime<(CODE/'pilot/reports/pipeline.json').stat().st_mtime:raise RuntimeError('Repaired pilot pipeline failed; inspect before formal inference')
        time.sleep(5)
    log=(ROOT/'logs/judge_stream.log').open('w',encoding='utf-8')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    stream=subprocess.Popen([sys.executable,'-X','utf8',str(CODE/'scripts/judge_stream.py'),'--workers','24'],cwd=CODE,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
    followup_log=(ROOT/'logs/scoring_followup_stream.log').open('w',encoding='utf-8')
    followup=subprocess.Popen([sys.executable,'-X','utf8',str(CODE/'scripts/scoring_followup_stream.py'),'--workers','8'],cwd=CODE,env=env,stdout=followup_log,stderr=subprocess.STDOUT,creationflags=flags)
    try:
        result=subprocess.run([sys.executable,'-X','utf8',str(CODE/'scripts/pipeline_v04.py'),'--skip-probes'],cwd=CODE,env=env)
        if result.returncode:raise RuntimeError('Formal GPU/scoring pipeline requires attention')
        code=stream.wait(timeout=60)
        if code:raise RuntimeError('Judge stream failed')
        followup_code=followup.wait(timeout=60)
        if followup_code:
            # The normal batch stages are the recovery path and final gate.
            if read(ROOT/'reports/acceptance.json').get('status')!='passed':raise RuntimeError('Follow-up scoring requires attention')
            print('Follow-up stream stopped; final batch recovered and passed acceptance.',flush=True)
    finally:
        if stream.poll() is None:stream.terminate();stream.wait(timeout=20)
        if followup.poll() is None:followup.terminate();followup.wait(timeout=20)
        followup_log.close()
        log.close()
