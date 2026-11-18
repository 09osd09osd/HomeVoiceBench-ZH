"""Versioned inputs and deterministic replay; no counterfactual model outputs."""
import copy,hashlib,json
from .sandbox import Sandbox,compact_tools,VERSION as SANDBOX_VERSION
from .grading import grade_rules,VERSION as GRADING_VERSION
from .authorization import VERSION as AUTH_VERSION
from .semantics import VERSION as COMPARISON_VERSION

def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def input_projection(case):
    return {'model_context':case['model_context'],'environment':case['environment'],
            'interaction':case['interaction'],
            'input_audio':[{k:a[k] for k in ('node_id','sha256')} for a in case['variants'][0]['audio_assets']]}

def protocol_metadata(case,origin):
    return {'benchmark_version':'0.4.0','execution_origin':origin,'input_projection_sha256':digest(input_projection(case)),
            'model_visible_tools_sha256':digest(compact_tools(case['model_context']['tool_names'])),'sandbox_version':SANDBOX_VERSION,
            'grading_version':GRADING_VERSION,'authorization_version':AUTH_VERSION,'comparison_version':COMPARISON_VERSION}

def replay(case,run):
    sim=Sandbox(case['environment'],case['model_context']['actor']);index=0;differences=[];origin=None
    def call(event):
        nonlocal index
        sim.call(event['call']['tool_name'],event['call']['arguments'],event['request_id'])
        actual=sim.trace[-1]
        for field in ('response','state_before','state_after'):
            if actual[field]!=event[field]:
                differences.append({'event_index':index,'node_id':sim.current_node_id,'field':field,
                                    'old_sha256':digest(event[field]),'new_sha256':digest(actual[field]),
                                    'tool_name':event['call']['tool_name']})
        index+=1
    for turn in run['turns']:
        node=turn['node_id'];sim.begin_turn(node,turn['user_turn_index'])
        if node!='FALLBACK':origin=node
        for event in turn['tool_events']:
            if event['call']!=run['tool_trace'][index]['call']:raise ValueError('turn/trace disagreement')
            call(run['tool_trace'][index])
        sim.end_turn(origin if node=='FALLBACK' else node)
    incomplete=run.get('incomplete_turn')
    if incomplete:
        if index!=incomplete['first_tool_event_index']:raise ValueError('incomplete trace boundary mismatch')
        sim.begin_turn(incomplete['node_id'],len(run['turns'])+1)
        for event in run['tool_trace'][index:]:call(event)
    if index!=len(run['tool_trace']):raise ValueError('unattributed tool trace')
    if sim.state!=run['final_state']:
        differences.append({'field':'final_state','old_sha256':digest(run['final_state']),'new_sha256':digest(sim.state)})
    return sim,differences

def reuse_compatible(case,old,old_file_hash):
    sim,differences=replay(case,old)
    if differences:raise ValueError('Changed model-visible sandbox response/state requires actual rerun')
    run=copy.deepcopy(old);run.update(schema_version='0.3.0',case_sha256=digest(case),rule_checks=grade_rules(case,sim),
                                    audio_judge=None,case_pass=None,task_achieved=None,judge_status='pending_v0.3_uniform_rejudge')
    run['revision']={**protocol_metadata(case,'v0.2_audio_reused_after_exact_trace_replay'),
                     'source_run_file_sha256':old_file_hash,'sandbox_replay':'all responses, pre/post states and final state exactly equal',
                     'original_case_sha256':old['case_sha256']}
    # Preserve original observed tool evidence. Add attribution only, never replace it with new returns.
    index=0
    for t in run['turns']:
        for e in t['tool_events']:
            e.update(node_id=t['node_id'],user_turn_index=t['user_turn_index'])
            run['tool_trace'][index].update(node_id=t['node_id'],user_turn_index=t['user_turn_index']);index+=1
    if run.get('incomplete_turn'):
        for e in run['tool_trace'][index:]:e.update(node_id=run['incomplete_turn']['node_id'],user_turn_index=len(run['turns'])+1)
    return run
