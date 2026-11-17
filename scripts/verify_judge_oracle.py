"""Regression audit of the discovered wrong-ID judging error, using actual audio.

These are existing benchmark cases inspected after the error was found, not an
independent validation set or a human calibration. Model outputs are unchanged.
"""
import concurrent.futures,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.judge_runs import evaluate,EVIDENCE_VERSION

expected={'T03_007':False,'T18_001':False,'T19_011':False,'T05_006':True}
with concurrent.futures.ThreadPoolExecutor(4) as pool:
    futures={pool.submit(evaluate,ROOT/'runs/edge_native'/f'{cid}.json',{}):cid for cid in expected}
    for f in concurrent.futures.as_completed(futures):print(json.dumps({'case':futures[f],'status':f.result()}),flush=True)
checks=[]
for cid,want in expected.items():
    r=json.loads((ROOT/'runs/edge_native'/f'{cid}.json').read_text('utf-8'))
    check=next(c for c in r['audio_judge']['result']['semantic_checks'] if c['check_id']=='CONTENT')
    checks.append({'case_id':cid,'expected_content_pass':want,'actual_content_pass':check['passed'],'reason':check['reason'],'regression_passed':check['passed']==want})
report={'evidence_version':EVIDENCE_VERSION,'scope':'Post-discovery regression audit on actual benchmark audio; not independent validation or human review','model_outputs_changed':False,'checks':checks,'status':'passed' if all(c['regression_passed'] for c in checks) else 'needs_inspection'}
(ROOT/'reports/judge_oracle_regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8');print(json.dumps(report,ensure_ascii=False))
if report['status']!='passed':raise SystemExit(1)
