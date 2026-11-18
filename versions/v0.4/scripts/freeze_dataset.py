"""Freeze authored, audio-verified inputs before any evaluated model run."""
import datetime,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT,CODE_ROOT
from homevoice.source_lint import issues as source_issues

def freeze():
    cases=[]
    for p in sorted((ROOT/'data/cases').glob('*.json')):
        c=json.loads(p.read_text('utf-8'))
        if c['variants'][0]['status']!='ready':raise ValueError('Unverified audio: '+p.stem)
        cases.append({'case_id':p.stem,'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    expected=100 if ROOT.name=='pilot' else 1000
    if len(cases)!=expected:raise ValueError('Incorrect case count')
    out=ROOT/'data/manifest.json'
    if out.exists():
        old=json.loads(out.read_text('utf-8'))
        if old['cases']!=cases:raise ValueError('Frozen inputs changed; preserve and version before running')
        return old
    for entry in cases:
        c=json.loads((ROOT/entry['path']).read_text('utf-8'))
        if any(source_issues(n['user_text'],c['classification']['category']) for n in c['interaction']['nodes']):raise ValueError('Spoken-source lint failed: '+entry['case_id'])
    reused=[];existing=[p for s in ['edge_native','qwen35_2b','qwen35_4b'] for p in (ROOT/'runs'/s).glob('*.json')]
    if existing:
        authorization=CODE_ROOT/'docs/FULL_RUN_AUTHORIZATION.json'
        if ROOT.name!='pilot' or not authorization.exists():raise ValueError('Cannot freeze after model runs')
        auth=json.loads(authorization.read_text('utf-8'));archive=CODE_ROOT/auth['archive'];old=json.loads((archive/'data/manifest.json').read_text('utf-8'));old_hashes={x['case_id']:x['sha256'] for x in old['cases']};new_hashes={x['case_id']:x['sha256'] for x in cases}
        for p in existing:
            if p.stem in auth['changed_cases'] or old_hashes.get(p.stem)!=new_hashes.get(p.stem):raise ValueError('Cannot reuse a run whose input was repaired')
            previous=archive/p.relative_to(ROOT)
            if p.read_bytes()!=previous.read_bytes():raise ValueError('Unchanged-case run differs from preserved source')
            reused.append(p.relative_to(ROOT).as_posix())
    policy=ROOT/'spec/scoring_policy.json'
    data={'version':'0.4.0','protocol_revision':3,'split':'development' if ROOT.name=='pilot' else 'test','status':'frozen_revision_with_preserved_unchanged_cases' if reused else 'frozen_before_scoring','reused_unchanged_run_paths':reused,'scoring_policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest() if policy.exists() else None,'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':cases}
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8');return data
if __name__=='__main__':print(json.dumps({'frozen':len(freeze()['cases'])}))
