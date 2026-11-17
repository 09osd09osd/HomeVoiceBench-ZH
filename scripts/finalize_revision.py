"""Finish the authorized v0.3 local delivery after inference/judging stops."""
import datetime, hashlib, json, os, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.judge_runs import save
status={'status':'running','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stages':[]}

def read(path):return json.loads(path.read_text('utf-8'))
def stage(name):
    status['current_stage']=name;status['stages'].append({'name':name,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    save(ROOT/'reports/revision/finalization_status.json',status);print(json.dumps({'stage':name}),flush=True)
def run(name,args):
    stage(name)
    with (ROOT/'logs'/('v03-final-'+name+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(f'{name} failed; inspect its local log')
def py(name,*args):run(name,[sys.executable,'-X','utf8','scripts/'+name+'.py',*args])

try:
    stage('waiting_for_evaluation')
    while True:
        pipeline=read(ROOT/'reports/revision/pipeline_status.json')
        if pipeline.get('status')=='completed':break
        if pipeline.get('status')=='needs_attention':raise RuntimeError('Evaluation pipeline needs attention')
        time.sleep(5)
    py('clarify_read_claims')
    py('judge_runs','--workers','16')
    # All cloud writers are now stopped. Preserve the original usage ledger
    # privately and remove workspace identifiers from the public copy.
    stage('public_usage_ledger')
    ledger=ROOT/'reports/api_usage.jsonl';raw=ledger.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    backup=ROOT/'.local/archive'/('api_usage_before_publication_'+sha[:16]+'.jsonl')
    if not backup.exists():backup.write_bytes(raw)
    records=[json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()];redacted=0
    for record in records:
        host=record.get('endpoint_host')
        if host and host not in ['api.deepseek.com','configured_bailian_workspace']:
            record['endpoint_host']='configured_bailian_workspace';redacted+=1
    ledger.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),'utf-8')
    save(ROOT/'reports/revision/public_ledger_redaction.json',{'source_sha256':sha,'records':len(records),'redacted_workspace_host_records':redacted,'credential_values_included':False})
    py('validate_dataset')
    py('summarize')
    if read(ROOT/'reports/summary.json')['evaluation_status']!='complete':raise RuntimeError('Amended judgments remain incomplete')
    py('diagnostics')
    py('audit_story_duration')
    py('build_revision_report')
    py('audit_release','--require-complete')
    py('build_docs')
    run('build_workbook',[os.getenv('HOMEVOICE_NODE','node'),'--max-old-space-size=4096','scripts/build_workbook.mjs'])
    py('build_site')
    py('package_release','--part','evaluation')
    py('build_delivery_index')
    status.update(status='completed',finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save(ROOT/'reports/revision/finalization_status.json',status);print(json.dumps({'local_finalization':'completed'}),flush=True)
except Exception as e:
    status.update(status='needs_attention',error=str(e));save(ROOT/'reports/revision/finalization_status.json',status);raise
