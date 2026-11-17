"""Retry infrastructure failures only. Preserve genuine model/budget failures."""
import datetime,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];markers=['CUDA out of memory','bad allocation','Local inference HTTP 502','TimeoutError: timed out','WinError 10061','RemoteDisconnected','ConnectionResetError','MemoryError']
records=[];stamp=str(time.time_ns())
for system in ['edge_native','qwen35_2b','qwen35_4b']:
    for p in (ROOT/'runs'/system).glob('*.json'):
        r=json.loads(p.read_text('utf-8'));flags=r['execution']['flags']
        if r['execution']['status']=='failed' and any(marker in flag for flag in flags for marker in markers):
            target=ROOT/'runs/infra_attempts'/('resource_'+stamp)/system/p.name;target.parent.mkdir(parents=True,exist_ok=True)
            if not p.resolve().is_relative_to(ROOT.resolve()) or not target.resolve().is_relative_to(ROOT.resolve()):raise ValueError('unsafe archive path')
            p.replace(target);records.append({'case_id':r['case_id'],'system_id':system,'flags':flags,'archive':target.relative_to(ROOT).as_posix()})
report={'reason':'Shared GPU/system commit exhaustion during concurrent engine pressure test. Re-run only identified infrastructure failures after switching to staged single-engine batching; model correctness and budget failures are retained.','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':records}
(ROOT/'reports'/f'infrastructure_rerun_{stamp}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps({'archived_infrastructure_failures':len(records)}))
