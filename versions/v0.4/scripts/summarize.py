"""Rebuild reports from actual files. Pending scores never become zero."""
import collections,datetime,hashlib,json,random,statistics,sys
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT,SHARED_ROOT;sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.catalog import SCENES
from homevoice.speech_text import VERSION
from scripts.judge_runs import PROMPT,EVIDENCE_VERSION,judgment_current
from scripts.review_semantics import current as review_current
from scripts.adjudicate_audio import current as adjudication_current
SYSTEMS=['edge_native','qwen35_2b','qwen35_4b']
def read(p):return json.loads(p.read_text('utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8')
def mean(values):return statistics.mean(values) if values else None
def rate(a,n):return a/n if n else None
def summarize():
    cases=[read(p) for p in sorted((ROOT/'data/cases').glob('*.json'))];byid={c['identity']['case_id']:c for c in cases};assets={a['sha256']:a for c in cases for a in c['variants'][0]['audio_assets'] if a.get('sha256')};rows=[];runrows=[];by_system={}
    for c in cases:
        rows.append({'case_id':c['identity']['case_id'],'category':c['classification']['category'],'scene_id':c['classification']['scene_id'],'title':c['identity']['title'],'difficulty':c['classification']['difficulty'],'group_id':c['classification']['group_id'],'turn_count':len(c['interaction']['nodes']),'user_texts':[n['user_text'] for n in c['interaction']['nodes']],'audio_ready':c['variants'][0]['status']=='ready','audio_assets':len(c['variants'][0]['audio_assets']),'reference_tool_calls':sum(len(t['calls']) for t in c['reference']['turns']),'faults':[f['kind'] for f in c['environment']['faults']],'source_path':f'data/cases/{c["identity"]["case_id"]}.json'})
    for system in SYSTEMS:
        rr=[read(p) for p in sorted((ROOT/'runs'/system).glob('*.json'))];by_system[system]={r['case_id']:r for r in rr}
        for r in rr:
            if r.get('audio_judge') and (not judgment_current(byid[r['case_id']],r) or not review_current(byid[r['case_id']],r)):
                r.update(audio_judge=None,case_pass=None,task_achieved=None,judge_status='pending_current_evidence')
            c=byid[r['case_id']];j=r.get('audio_judge');d=j['result'] if j else None
            runrows.append({'case_id':r['case_id'],'system_id':system,'category':c['classification']['category'],'scene_id':c['classification']['scene_id'],'turn_count':len(r['turns']),'execution_status':r['execution']['status'],'flags':r['execution']['flags'],'rule_pass':all(k['passed'] for k in r['rule_checks']),'case_pass':r.get('case_pass'),'task_achieved':r.get('task_achieved'),'judged':j is not None,'mean_score':mean([s['score'] for s in d['dimensions']]) if d else None,'dimensions':{s['dimension_id']:s['score'] for s in d['dimensions']} if d else {},'critical_failures':d['critical_failures'] if d else None,'judge_status':r.get('judge_status','pending'),'tool_calls':r['execution']['tool_calls'],'wall_seconds_interaction':r['execution']['wall_seconds'],'run_path':f'runs/{system}/{r["case_id"]}.json'})
    for r in rows:r['reporting_partition']=byid[r['case_id']]['evaluation'].get('reporting_partition','standard')
    for r in runrows:
        r['planned_user_turns']=len(byid[r['case_id']]['interaction']['nodes'])
        r['reporting_partition']=byid[r['case_id']]['evaluation'].get('reporting_partition','standard')
        raw=by_system[r['system_id']][r['case_id']]
        r['case_pass_primary']=raw.get('case_pass_primary',raw.get('case_pass'));r['semantic_reviewed']=bool(raw.get('semantic_review'));r['review_proposed_case_pass']=(raw.get('semantic_review') or {}).get('proposed_case_pass');r['semantic_disputed']=(raw.get('semantic_review') or {}).get('decision_status')=='disputed'
        r['evidence_sha256']=(raw.get('audio_judge') or {}).get('evidence_sha256')
        r['audio_adjudicated']=adjudication_current(byid[r['case_id']],raw)
        if r['semantic_disputed'] and not r['audio_adjudicated']:r['case_pass']=None
        r['final_rating_source']='fresh_audio_adjudication' if r['audio_adjudicated'] else 'agreed_audio_and_semantic_review' if r['judged'] else 'execution_failure'
        if raw.get('semantic_review'):r['critical_failures']=raw['semantic_review']['result']['critical_failures']
        if r['audio_adjudicated']:r['critical_failures']=raw['audio_adjudication']['result']['critical_failures']
        r['execution_origin']=raw.get('revision',{}).get('execution_origin')
        r['read_tool_calls']=sum(e['call']['tool_name'] in {'device_query','sensor_read','schedule_list','media_search','task_get'} for e in raw['tool_trace'])
        r['difficulty']=byid[r['case_id']]['classification']['difficulty'];r['grouped']=byid[r['case_id']]['design']['grouped'];r['group_level']=byid[r['case_id']]['design']['level']
        r['failure_detail']=raw['execution'].get('failure');r['audio_fact_review_required']=raw.get('audio_fact_review_required',False)
    stats=[]
    for system in SYSTEMS:
        for category in ['all','tool','chat']:
            target=[c for c in cases if category=='all' or c['classification']['category']==category];rr=[r for r in runrows if r['system_id']==system and (category=='all' or r['category']==category)];decided=[r for r in rr if r['case_pass'] is not None];judged=[r for r in rr if r['judged']];passed=sum(r['case_pass'] is True for r in rr);dims=collections.defaultdict(list)
            for r in judged:
                for k,v in r['dimensions'].items():dims[k].append(v)
            stats.append({'system_id':system,'category':category,'planned':len(target),'run_count':len(rr),'decided_count':len(decided),'judged_count':len(judged),'passed_count':passed,'strict_pass_rate':rate(passed,len(target)) if len(decided)==len(target) else None,'observed_pass_rate':rate(passed,len(decided)),'dimension_mean':{k:mean(v) for k,v in dims.items()},'overall_dimension_mean':mean([r['mean_score'] for r in judged]),'execution_failures':sum(r['execution_status']=='failed' for r in rr),'critical_failure_count':sum(bool(r['critical_failures']) for r in judged),'critical_failure_rate_among_judged':rate(sum(bool(r['critical_failures']) for r in judged),len(judged))})
    turn_stats=[]
    for system in SYSTEMS:
        for category in ['all','tool','chat']:
            for turns in range(1,6):
                ids={c['case_id'] for c in rows if c['turn_count']==turns and (category=='all' or c['category']==category)}
                rr=[r for r in runrows if r['system_id']==system and r['case_id'] in ids]
                known=[r for r in rr if r['case_pass'] is not None];passed=sum(r['case_pass'] is True for r in rr)
                turn_stats.append({'system_id':system,'category':category,'planned_user_turns':turns,'planned':len(ids),'run_count':len(rr),'decided_count':len(known),'passed_count':passed,'strict_pass_rate':rate(passed,len(ids)) if len(known)==len(ids) else None})
            grouped=[g for g in turn_stats if g['system_id']==system and g['category']==category]
            whole=next(g for g in stats if g['system_id']==system and g['category']==category)
            for key in ['planned','run_count','decided_count','passed_count']:
                if sum(g[key] for g in grouped)!=whole[key]:raise ValueError('Planned-turn aggregation mismatch: '+key)
    scene_rows=[]
    for s in SCENES:
        cs=[c for c in rows if c['scene_id']==s['scene_id']];entry={**s,'case_count':len(cs),'ready_cases':sum(c['audio_ready'] for c in cs),'normal_user_turns':sum(c['turn_count'] for c in cs),'systems':{}}
        for system in SYSTEMS:
            rr=[r for r in runrows if r['system_id']==system and r['scene_id']==s['scene_id']];known=[r for r in rr if r['case_pass'] is not None];entry['systems'][system]={'runs':len(rr),'decided':len(known),'passed':sum(r['case_pass'] is True for r in rr),'strict_pass_rate':rate(sum(r['case_pass'] is True for r in rr),len(cs)) if len(known)==len(cs) else None,'mean_score':mean([r['mean_score'] for r in rr if r['mean_score'] is not None])}
        scene_rows.append(entry)
    complete=all(s['decided_count']==s['planned'] for s in stats if s['category']=='all');comparisons=[]
    if complete:
        for a,b in [('edge_native','qwen35_2b'),('edge_native','qwen35_4b'),('qwen35_4b','qwen35_2b')]:
            for category in ['all','tool','chat']:
                groups={s['scene_id']:[int(by_system[a][c['case_id']]['case_pass'])-int(by_system[b][c['case_id']]['case_pass']) for c in rows if c['scene_id']==s['scene_id']] for s in SCENES if category=='all' or s['category']==category};rng=random.Random(42);values=[];strata=[[s['scene_id'] for s in SCENES if s['category']==cat and s['scene_id'] in groups] for cat in ['tool','chat']]
                for _ in range(2000):
                    sampled=[v for ids in strata if ids for id in rng.choices(ids,k=len(ids)) for v in groups[id]];values.append(mean(sampled))
                values.sort();comparisons.append({'system_a':a,'system_b':b,'category':category,'pass_rate_difference':mean([v for g in groups.values() for v in g]),'cluster_bootstrap_95_ci':[values[49],values[1949]],'cluster_unit':'scene','stratification':'tool/chat','replicates':2000,'seed':42})
    usage=collections.defaultdict(lambda:{'requests':0,'prompt_tokens':0,'completion_tokens':0,'reported_total_tokens':0})
    for line in (ROOT/'reports/api_usage.jsonl').read_text('utf-8').splitlines():
        if not line.strip():continue
        d=json.loads(line);m=d.get('requested_model') or d.get('returned_model') or 'unknown';u=d.get('usage') or {};z=usage[m];z['requests']+=1
        z['prompt_tokens']+=u.get('prompt_tokens',u.get('input_tokens',0)) or 0;z['completion_tokens']+=u.get('completion_tokens',u.get('output_tokens',0)) or 0;z['reported_total_tokens']+=u.get('total_tokens',0) or 0
    report={'benchmark':'HomeVoiceBench-ZH','version':'0.2.0','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evaluation_status':'complete' if complete else 'in_progress','dataset':{'cases':len(cases),'tool_cases':sum(c['category']=='tool' for c in rows),'chat_cases':sum(c['category']=='chat' for c in rows),'scenes':len(SCENES),'normal_user_turns':sum(c['turn_count'] for c in rows),'turn_distribution':dict(collections.Counter(c['turn_count'] for c in rows)),'audio_ready_cases':sum(c['audio_ready'] for c in rows),'referenced_verified_unique_audio':len(assets),'referenced_unique_audio_seconds':sum(a.get('duration_s',0) or 0 for a in assets.values()),'normalizer_version':VERSION,'human_review':'not_performed','input_type':'synthetic_clean_mandarin_audio'},'systems':stats,'paired_comparisons':comparisons,'api_usage':dict(usage),'usage_caveat':'Contains authoring, reviews, pilots, regeneration, input QC and response judging; provider pricing/billing may differ. Requests are ledger entries, not unique case costs.','limitations':['Synthetic clean speech, four instructed adult voices; no real-room noise or far-field generalization claim.','Fixed authored follow-ups and bounded clarification; not arbitrary interactive users.','Same-model authoring review is not independent human review.','One seed, one model audio judge; confidence intervals cover scene sampling, not all model/judge uncertainty.','Reference-compatible backbones differ in precision and runtime from native Edge; results compare complete deployed systems.','Offline ASR/TTS caching and batching mean interaction timings are not end-to-end real-time latency.']}
    partition_stats=[]
    for system in SYSTEMS:
        for partition in ['standard','budget_stress']:
            for category in ['all','tool','chat']:
                target=[c for c in rows if c['reporting_partition']==partition and (category=='all' or c['category']==category)]
                if not target:continue
                rr=[r for r in runrows if r['system_id']==system and r['reporting_partition']==partition and (category=='all' or r['category']==category)]
                known=[r for r in rr if r['case_pass'] is not None];passed=sum(r['case_pass'] is True for r in rr)
                partition_stats.append({'system_id':system,'partition':partition,'category':category,'planned':len(target),'decided_count':len(known),'passed_count':passed,'strict_pass_rate':rate(passed,len(target)) if len(known)==len(target) else None})
    report.update(version='0.4.0',split='development' if ROOT.name=='pilot' else 'test',judge_evidence_version=EVIDENCE_VERSION,judge_prompt_sha256=hashlib.sha256(PROMPT.encode()).hexdigest(),by_planned_user_turns=turn_stats,by_reporting_partition=partition_stats,
                  revision={'previous_version':'0.3.0','old_results_preserved':True,'reused_old_model_runs':0,'all_three_greedy':True,'core_tools':10,'extension_tools':2,'task_quality_separate':True,'source_machine_audit':'DeepSeek official API; independent human calibration not performed'},
                  budget_stress_case_ids=[r['case_id'] for r in rows if r['reporting_partition']=='budget_stress'])
    report['limitations'][1]='Fixed purposeful user nodes, no hidden rescue turns. Groups share cumulative prefixes; development and test have separate IDs/families but share scenario templates.'
    report['by_difficulty']=[]
    for system in SYSTEMS:
        for level in ['easy','medium','hard']:
            target=[c for c in rows if c['difficulty']==level];rr=[r for r in runrows if r['system_id']==system and r['difficulty']==level];known=[r for r in rr if r['case_pass'] is not None]
            report['by_difficulty'].append({'system_id':system,'difficulty':level,'planned':len(target),'decided':len(known),'passed':sum(r['case_pass'] is True for r in rr),'pass_rate':rate(sum(r['case_pass'] is True for r in rr),len(target)) if len(target)==len(known) else None})
    report['group_progression']=[]
    report['semantic_consistency_review']={'model':'qwen3.8-omni-flash','temperature':0,'scope':'uniform review of every audible primary decision using its actual heard transcript, user requirements and tool evidence; not a second independent audio listening','primary_results_preserved':True,'systems':[]}
    for system in SYSTEMS:
        rr=[r for r in runrows if r['system_id']==system]
        report['semantic_consistency_review']['systems'].append({'system_id':system,'primary_passed':sum(r['case_pass_primary'] is True for r in rr),'review_proposed_passed':sum(r['review_proposed_case_pass'] is True for r in rr),'agreed_passed':sum(r['case_pass'] is True for r in rr),'disputed':sum(r['semantic_disputed'] for r in rr),'pass_to_fail_disagreements':sum(r['case_pass_primary'] is True and r['review_proposed_case_pass'] is False for r in rr),'fail_to_pass_disagreements':sum(r['case_pass_primary'] is False and r['review_proposed_case_pass'] is True for r in rr),'unresolved_pass_rate_bounds':[sum(r['case_pass'] is True for r in rr)/len(cases),(sum(r['case_pass'] is True for r in rr)+sum(r['semantic_disputed'] for r in rr))/len(cases)]})
    for row in report['semantic_consistency_review']['systems']:
        rr=[r for r in runrows if r['system_id']==row['system_id']];unresolved=sum(r['semantic_disputed'] and not r['audio_adjudicated'] for r in rr)
        row.update(agreed_passed=sum(r['case_pass'] is True and not r['semantic_disputed'] for r in rr),final_passed=sum(r['case_pass'] is True for r in rr),audio_adjudicated=sum(r['audio_adjudicated'] for r in rr),unresolved_disputes=unresolved,unresolved_pass_rate_bounds=[sum(r['case_pass'] is True for r in rr)/len(cases),(sum(r['case_pass'] is True for r in rr)+unresolved)/len(cases)])
    if any(r['semantic_disputed'] and not r['audio_adjudicated'] for r in runrows):report['evaluation_status']='needs_semantic_adjudication'
    report['semantic_consistency_review']['final_policy']='When primary and review disagree or numeric evidence needs review: one blinded fresh audio adjudication. Objective failures remain failures; first schema-valid result, no best-score selection.'
    for system in SYSTEMS:
        families=collections.defaultdict(list)
        for r in runrows:
            if r['system_id']==system and r['grouped']:families[byid[r['case_id']]['classification']['group_id']].append(r)
        for family,rr in families.items():
            rr.sort(key=lambda r:r['group_level']);report['group_progression'].append({'system_id':system,'family':family,'results':[{'case_id':r['case_id'],'level':r['group_level'],'passed':r['case_pass']} for r in rr],'first_failed_level':next((r['group_level'] for r in rr if r['case_pass'] is False),None)})
    review_rows=[]
    for r in runrows:
        if not (r['semantic_disputed'] or r['audio_adjudicated']):continue
        raw=by_system[r['system_id']][r['case_id']];c=byid[r['case_id']]
        primary={x['check_id']:x for x in raw['audio_judge']['result']['semantic_checks']};secondary={x['check_id']:x for x in raw['semantic_review']['result']['checks']}
        review_rows.append({'case_id':r['case_id'],'system_id':r['system_id'],'title':c['identity']['title'],'user_texts':[n['user_text'] for n in c['interaction']['nodes']],'case_pass_primary':r['case_pass_primary'],'review_proposed_case_pass':r['review_proposed_case_pass'],'case_pass_final':r['case_pass'],'audio_adjudicated':r['audio_adjudicated'],'check_disagreements':[{'check_id':k,'primary':primary[k]['passed'],'review':secondary[k]['passed']} for k in primary if primary[k]['passed']!=secondary[k]['passed']],'evidence_sha256':r['evidence_sha256'],'review_url':f'http://127.0.0.1:18788/review/?dataset={ROOT.name}#case={r["case_id"]}&tab=judge'})
    save(ROOT/'reports/scoring_review_overview.json',{'records':len(review_rows),'unique_cases':len({r['case_id'] for r in review_rows}),'human_calibration_performed':False,'rows':review_rows})
    save(ROOT/'reports/summary.json',report);save(ROOT/'reports/case_overview.json',rows);save(ROOT/'reports/run_overview.json',runrows);save(ROOT/'reports/scene_overview.json',scene_rows)
    print(json.dumps({'dataset':report['dataset'],'evaluation_status':report['evaluation_status'],'runs':len(runrows),'judged':sum(r['judged'] for r in runrows)},ensure_ascii=False))
if __name__=='__main__':summarize()
