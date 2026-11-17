"""After the current pipeline exits, replay the one reviewed transport failure."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'reports/pending_infra_retry.json'
def read(p):return json.loads(p.read_text('utf-8'))
def save(d):
    tmp=PLAN.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf-8');tmp.replace(PLAN)
plan=read(PLAN)
if plan['status']=='completed':raise SystemExit('Reviewed infrastructure retry already complete')
if plan['system']!='qwen35_4b' or plan['case_id']!='T27_009':raise ValueError('Only the reviewed single-case retry is authorized by this plan')
while True:
    state=read(ROOT/'reports/pipeline_status.json')
    if state.get('status')=='completed':break
    if state.get('status')=='needs_attention':raise RuntimeError('Current pipeline needs attention before infrastructure replay')
    time.sleep(10)
if read(ROOT/'reports/judge_stream_status.json')['status']=='running':raise RuntimeError('Scoring still owns the original records')
try:
    original=ROOT/'runs/qwen35_4b/T27_009.json'
    if plan['status']=='planned_after_current_audio_pipeline':
        data=original.read_bytes();record=json.loads(data)
        if not any('URLError' in f and '10060' in f for f in record['execution']['flags']):raise ValueError('Original transport failure evidence changed')
        if hashlib.sha256(data).hexdigest()!=plan['original_sha256']:raise ValueError('Original record changed since review; inspect before retry')
        destination=ROOT/'runs/infra_attempts/loopback_timeout_4b/T27_009.json'
        if not original.resolve().is_relative_to(ROOT.resolve()) or not destination.resolve().is_relative_to(ROOT.resolve()):raise ValueError('Archive outside workspace')
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():raise ValueError('Refusing to overwrite an archived attempt')
        history=ROOT/'reports/runtime_history';history.mkdir(exist_ok=True)
        (history/'qwen_4B_before_transport_retry.json').write_bytes((ROOT/'reports/qwen_4B_runtime.json').read_bytes())
        (ROOT/'reports/pipeline_history/before_transport_retry.json').write_bytes((ROOT/'reports/pipeline_status.json').read_bytes())
        original.replace(destination)
        plan.update(status='archived_original_retry_running',archived_run=destination.relative_to(ROOT).as_posix(),retry_started_at_unix=time.time());save(plan)
    elif plan['status']!='archived_original_retry_running':raise ValueError('Retry plan needs manual inspection')
    result=subprocess.run([sys.executable,'-X','utf8','scripts/complete_evaluation.py'],cwd=ROOT)
    if result.returncode:raise RuntimeError('Retry pipeline failed; all original evidence remains archived')
    result=read(original)
    if any('URLError' in f for f in result['execution']['flags']):raise RuntimeError('Transport failed again; inspect instead of repeating automatically')
    if result.get('case_pass') is None:raise RuntimeError('Actual retry judgment is incomplete')
    plan.update(status='completed',retry_finished_at_unix=time.time(),retry_execution=result['execution'],retry_case_pass=result['case_pass'],retry_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),retry_policy='One reviewed transport retry; genuine model outcome retained without quality-based reruns');save(plan)
    print(json.dumps({'infrastructure_retry':'completed','system':plan['system'],'case_id':plan['case_id'],'case_pass':result['case_pass']}),flush=True)
except Exception as exc:
    plan.update(status='needs_attention',error=str(exc));save(plan);raise
