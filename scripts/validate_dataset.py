import collections,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.sandbox import ROOT,Sandbox,validate
from homevoice.grading import grade_rules
from homevoice.speech_text import normalize,VERSION
schema=json.loads((ROOT/'spec/case.schema.json').read_text('utf-8'));errors=[];counts=collections.Counter();rounds=collections.Counter();names=collections.Counter();hashes=collections.defaultdict(list)
for p in sorted((ROOT/'data/cases').glob('*.json')):
    c=json.loads(p.read_text('utf-8'));cid=c['identity']['case_id'];counts[c['classification']['category']]+=1;names[c['classification']['scene_id']]+=1;rounds[len(c['interaction']['nodes'])]+=1
    try:
        validate(c,schema);s=Sandbox(c['environment'],c['model_context']['actor'])
        assert len(c['interaction']['nodes'])<=5 and c['variants'][0]['modality']=='audio'
        for t in c['reference']['turns']:
            for e in t['calls']:
                got=s.call(e['call']['tool_name'],e['call']['arguments']);assert got==e['expected_response'],'reference tool response mismatch'
            s.end_turn(t['node_id'])
        failures=[r for r in grade_rules(c,s) if not r['passed']]
        assert not failures,'reference failed own rules: '+str([x['check_id'] for x in failures])
        assert len(s.trace)<=c['interaction']['budget']['max_tool_calls']
        for n in c['interaction']['nodes']:assert normalize(normalize(n['user_text']))==normalize(n['user_text'])
        key=hashlib.sha256(json.dumps([x['user_text'] for x in c['interaction']['nodes']],ensure_ascii=False).encode()).hexdigest();hashes[key].append(cid)
    except Exception as e:errors.append({'case_id':cid,'error':str(e)[:1200]})
report={'case_count':sum(counts.values()),'category_counts':counts,'scene_count':len(names),'scene_counts':names,'turn_counts':rounds,'errors':errors,'exact_duplicate_dialogue_groups':[g for g in hashes.values() if len(g)>1],'normalizer_version':VERSION,'human_review':'not_performed','status':'passed' if not errors and counts=={'tool':600,'chat':400} and all(n==20 for n in names.values()) else 'failed'}
(ROOT/'reports/dataset_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
if report['status']!='passed':raise SystemExit(1)
