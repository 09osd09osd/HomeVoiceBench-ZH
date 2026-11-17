"""Audit every original trajectory before selecting symmetric reruns."""
import argparse,collections,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.revision import digest,input_projection,replay,reuse_compatible
from homevoice.sandbox import compact_tools
from scripts.migrate_revision_dataset import save
OLD=ROOT/'.local/archive/v0.2.0-before-v0.3'
SYSTEMS=['edge_native','qwen35_2b','qwen35_4b']

def read(p):return json.loads(p.read_text('utf-8'))
def legacy_tools():
    types=read(OLD/'spec/types.schema.json');catalog=read(OLD/'spec/sandbox.json')
    def expand(s):
        if isinstance(s,list):return [expand(x) for x in s]
        if not isinstance(s,dict):return s
        if '$ref' in s:return expand(types['$defs'][s['$ref'].split('/')[-1]])
        return {k:expand(v) for k,v in s.items() if k!='description'}
    return [{'type':'function','function':{'name':t['name'],'description':t['description'],'parameters':expand(t['input_schema'])}} for t in catalog['tools']]

def plan():
    start=time.monotonic();changes={};records=[]
    if legacy_tools()!=compact_tools():raise ValueError('Model-visible tools changed; selective reuse is not valid')
    cases={p.stem:read(p) for p in sorted((ROOT/'data/cases').glob('*.json'))}
    for cid,c in cases.items():
        old=read(OLD/'data/cases'/f'{cid}.json')
        if input_projection(old)!=input_projection(c):changes[cid]=['model_input_changed']
    for system in SYSTEMS:
        for i,(cid,c) in enumerate(cases.items()):
            source=OLD/'runs'/system/f'{cid}.json';old=read(source);sim,diff=replay(c,old)
            if diff:changes.setdefault(cid,[]).append('sandbox_response_changed:'+system)
            records.append({'system_id':system,'case_id':cid,'source_file_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                            'sandbox_compatible':not diff,'differences':diff})
            if (i+1)%200==0:print(json.dumps({'replayed':system,'count':i+1}),flush=True)
    out={'version':'0.3.0','selection':'Changes in author inputs or exact tool return/state replay; never model scores. Union applied to all three systems.',
         'model_visible_tools_sha256':digest(compact_tools()),'rerun_cases':dict(sorted(changes.items())),
         'rerun_case_count':len(changes),'rerun_system_case_count':len(changes)*3,'replay_records':records,'seconds':time.monotonic()-start}
    save(ROOT/'reports/revision/replay_plan.json',out);print(json.dumps({k:v for k,v in out.items() if k not in ['replay_records','rerun_cases']}),flush=True)

def apply():
    p=read(ROOT/'reports/revision/replay_plan.json');rerun=set(p['rerun_cases']);counts=collections.Counter()
    evidence={(r['system_id'],r['case_id']):r for r in p['replay_records']}
    for system in SYSTEMS:
        for source in sorted((OLD/'runs'/system).glob('*.json')):
            cid=source.stem;target=ROOT/'runs'/system/source.name;h=hashlib.sha256(source.read_bytes()).hexdigest()
            if h!=evidence[(system,cid)]['source_file_sha256']:raise ValueError('Archive changed')
            if target.exists() and read(target).get('revision',{}).get('benchmark_version')=='0.3.0':continue
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=h:raise ValueError('Current run differs from archived source: '+str(target))
            if cid in rerun:
                # Verified immutable backup exists; only this exact file is removed to enable resumption.
                if target.exists():target.unlink()
                counts['runs_marked_for_regeneration']+=1
            else:
                c=read(ROOT/'data/cases'/source.name);save(target,reuse_compatible(c,read(source),h));counts['reused_outputs_regraded']+=1
    save(ROOT/'reports/revision/replay_applied.json',dict(counts));print(json.dumps(counts),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['plan','apply']);args=ap.parse_args()
    plan() if args.mode=='plan' else apply()
