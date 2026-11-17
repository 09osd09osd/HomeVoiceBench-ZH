"""Apply a source-only constraint amendment after active judge writers stop.

No user audio, model-visible context, tool behavior or model output changes.
Every affected system receives the same amended case and a fresh audio judgment.
"""
import copy, datetime, hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.revision import digest, input_projection, replay
from homevoice.grading import grade_rules
from scripts.judge_runs import save as atomic_save

def read(path):return json.loads(path.read_text('utf-8'))
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    atomic_save(path,data)

def main():
    stream=ROOT/'reports/judge_stream_status.json'
    if stream.exists() and read(stream).get('status')=='running':
        raise RuntimeError('Wait for the active judge stream to finish before amending evidence.')
    plan=read(ROOT/'data/revision/read_claim_clarifications.json')
    archive=ROOT/'.local/archive/v0.3-before-read-claim-clarification'
    manifest=read(ROOT/'data/manifest.json');before_manifest=digest(manifest)
    if any(a['version']==plan['version'] for a in manifest.get('amendments',[])):
        for cid in plan['replacements']:
            path=ROOT/'data/cases'/f'{cid}.json';item=next(x for x in manifest['cases'] if x['case_id']==cid)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=item['file_sha256']:raise ValueError('Amended manifest mismatch')
        print(json.dumps({'status':'already_applied'}));return
    changes=[]
    for cid,pairs in plan['replacements'].items():
        path=ROOT/'data/cases'/f'{cid}.json';case=read(path);before=copy.deepcopy(case)
        oldcase=archive/'data/cases'/path.name
        if case['identity']['case_version']=='2.0.1':
            if not oldcase.exists():raise ValueError('Cannot resume without original case backup')
            before=read(oldcase)
        else:
            for old,new in pairs:
                count=0
                for node in case['evaluation']['behavior_policy']['nodes']:
                    for i,text in enumerate(node['must_not']):
                        if text==old:node['must_not'][i]=new;count+=1
                if count!=1:raise ValueError(f'{cid}: expected exactly one constraint match, got {count}')
                for turn in case['reference']['turns']:
                    turn['assistant_text']=turn['assistant_text'].replace(old,new)
            case['identity']['case_version']='2.0.1'
            case['provenance']['source_refs'].append('data/revision/read_claim_clarifications.json')
        if input_projection(before)!=input_projection(case):raise ValueError('Model input changed')
        prepared=[]
        for system in ['edge_native','qwen35_2b','qwen35_4b']:
            runpath=ROOT/'runs'/system/f'{cid}.json';run=read(runpath)
            sim,differences=replay(case,run)
            if differences or grade_rules(case,sim)!=run['rule_checks']:
                raise ValueError('Expected a semantic-only amendment: '+system+'/'+cid)
            prepared.append((runpath,run))
        if not oldcase.exists():
            oldcase.parent.mkdir(parents=True,exist_ok=True);oldcase.write_bytes(path.read_bytes())
        save(path,case)
        for runpath,run in prepared:
            backup=archive/'runs'/runpath.parent.name/runpath.name
            if not backup.exists():
                backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(runpath.read_bytes())
            run['case_sha256']=digest(case)
            run['revision']['constraint_amendment']=plan['version']
            # Keep the prior judge object until evaluate archives it. Its full
            # evidence hash is now stale, so reports cannot reuse its decision.
            run.update(case_pass=None,task_achieved=None,judge_status='pending_read_claim_clarification')
            save(runpath,run)
        item=next(x for x in manifest['cases'] if x['case_id']==cid)
        item.update(file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),canonical_sha256=digest(case))
        changes.append({'case_id':cid,'old_case_sha256':digest(before),'new_case_sha256':digest(case),'replacements':[{'old':a,'new':b} for a,b in pairs]})
    if not changes:print(json.dumps({'status':'already_applied'}));return
    manifest.setdefault('amendments',[]).append({'version':plan['version'],'applied_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prior_manifest_sha256':before_manifest,'cases':list(plan['replacements']),'model_inputs_unchanged':True,'all_affected_systems_rejudged_required':True,'reason':plan['selection_basis']})
    manifest['meaning']='Model-visible inputs frozen before symmetric runs. Seven semantic read-claim constraints clarified after UI/source audit; affected case hashes updated and all three systems rejudged. No score-based case selection; no independent human calibration.'
    save(ROOT/'data/manifest.json',manifest)
    save(ROOT/'reports/revision/read_claim_clarification.json',{'version':plan['version'],'changes':changes,'model_inputs_and_outputs_unchanged':True,'deterministic_rules_unchanged':True,'required_rejudgments':len(changes)*3,'selection_basis':plan['selection_basis']})
    print(json.dumps({'amended_cases':len(changes),'required_rejudgments':len(changes)*3}))

if __name__=='__main__':main()
