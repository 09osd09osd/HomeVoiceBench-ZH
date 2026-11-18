"""Validate locally exported human annotations without changing any model score."""
import hashlib,json,re
from pathlib import Path

SYSTEMS=('edge_native','qwen35_2b','qwen35_4b')

def read(path):return json.loads(Path(path).read_text('utf-8-sig'))

def collect(document,root):
    root=Path(root);manifest_sha=hashlib.sha256((root/'data/manifest.json').read_bytes()).hexdigest()
    summary=read(root/'reports/summary.json');key='homevoice-review-v2:'+manifest_sha+':'+summary['judge_prompt_sha256']
    if not isinstance(document,dict) or document.get('format')!='homevoice-human-review-v1' or document.get('dataset_key')!=key or document.get('manifest_sha256')!=manifest_sha:
        raise ValueError('Export is from a different dataset or judge protocol')
    case_ids={x['case_id'] for x in read(root/'data/manifest.json')['cases']}
    records=document.get('records');labels={};seen=set()
    if not isinstance(records,list) or len(records)>len(case_ids):raise ValueError('Invalid human record list')
    for row in records:
        cid=row.get('case_id')
        if cid not in case_ids or cid in seen:raise ValueError('Unknown or duplicate human case ID')
        seen.add(cid)
        if not isinstance(row.get('systems',{}),dict):raise ValueError('Invalid human system records')
        for sid,value in row.get('systems',{}).items():
            if sid not in SYSTEMS or not isinstance(value,dict):raise ValueError('Unknown human system ID')
            verdict=value.get('verdict','pending');note=value.get('note','')
            if verdict not in {'pending','pass','fail','uncertain'} or not isinstance(note,str) or len(note)>20000:raise ValueError('Invalid human verdict or reason')
            if verdict=='pending':continue
            evidence=value.get('evidence_sha256');run=read(root/'runs'/sid/(cid+'.json'))
            if not isinstance(evidence,str) or not re.fullmatch('[a-f0-9]{64}',evidence) or evidence!=(run.get('audio_judge') or {}).get('evidence_sha256'):
                raise ValueError('Human label is not bound to the current evidence: '+sid+'/'+cid)
            labels[(sid,cid)]={'system_id':sid,'case_id':cid,'verdict':verdict,'reason':note,'case_note':row.get('note',''),'evidence_sha256':evidence,'reviewed_at':row.get('updated_at')}
    queue=[];missing=[];uncertain=[];conflicts=[]
    for sid in SYSTEMS:
        for p in sorted((root/'runs'/sid).glob('*.json')):
            run=read(p)
            if (run.get('semantic_review') or {}).get('decision_status')!='disputed':continue
            key=(sid,p.stem);label=labels.get(key);queue.append(key)
            if not label or not label['reason'].strip():missing.append({'system_id':sid,'case_id':p.stem});continue
            if label['verdict']=='uncertain':uncertain.append(label)
            failed_rules=[c['check_id'] for c in run['rule_checks'] if not c['passed']]
            if label['verdict']=='pass' and (failed_rules or run['execution']['status']!='completed'):
                conflicts.append({**label,'failed_rule_checks':failed_rules,'execution_status':run['execution']['status']})
    return {'status':'ready_for_calibration_analysis' if not missing and not uncertain and not conflicts else 'needs_human_followup','scope':'Human calibration annotations only; model runs and official labels are unchanged. This does not certify the full dataset.','manifest_sha256':manifest_sha,'required_records':len(queue),'required_cases':len({cid for _,cid in queue}),'resolved_records':len(queue)-len(missing)-len(uncertain)-len(conflicts),'missing_or_no_reason':missing,'uncertain':uncertain,'objective_conflicts':conflicts,'annotations':list(labels.values())}
