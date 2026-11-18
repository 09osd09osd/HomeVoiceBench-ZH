"""Reached-turn authorization checks, independent of final-state correctness."""
import copy
from .semantics import equivalent

VERSION='turn_scoped_authorization_v0.4'
WRITE_TOOLS={'device_set','schedule_create','schedule_update','schedule_cancel','media_play','media_control','task_cancel'}
READ_TOOLS={'device_query','sensor_read','schedule_list','media_search','task_get'}
TARGET_FIELDS={'schedule_update':'schedule_id','schedule_cancel':'schedule_id','media_control':'playback_id','task_cancel':'task_id'}
ACTION_STATES={'start':'cleaning','pause':'paused','resume':'cleaning','return_home':'returning'}

def compile_policy(case, constraints=None):
    constraints={n['node_id']:n for n in (constraints or [])}
    nodes=[]
    for node,reference in zip(case['interaction']['nodes'],case['reference']['turns']):
        checks=constraints.get(node['id'],{});blocked=checks.get('blocked_read_tools',[])
        writes=[]
        for e in reference['calls']:
            c=e['call']
            if c['tool_name'] in WRITE_TOOLS:
                descriptor={'tool_name':c['tool_name'],'arguments':copy.deepcopy(c['arguments'])}
                if descriptor not in writes:writes.append(descriptor)
        nodes.append({'node_id':node['id'],'allowed_read_tools':sorted(READ_TOOLS-set(blocked)),
                      'read_prohibition_evidence':checks.get('restriction_evidence',[]),'allowed_writes':writes,
                      'must_satisfy':checks.get('must_satisfy',[]),'acceptance_guidance':checks.get('acceptance_guidance',''),'must_not':checks.get('must_not',[])})
    return {'version':VERSION,'derivation':'Current and preceding user requests; executable write intents cross-checked against author data. Never use future nodes.',
            'read_policy':'Permission-respecting queries are allowed unless the reached user context explicitly prohibits them. Redundancy is reported separately, not an automatic failure.',
            'write_policy':'Only current-turn authorized objects, fields and values; split device updates and retries after recoverable failures are permitted.',
            'nodes':nodes}

def _without_message(value):
    # Reminder/alarm wording is judged from meaning, not string identity.
    if isinstance(value,dict):return {k:_without_message(v) for k,v in value.items() if k!='message'}
    if isinstance(value,list):return [_without_message(v) for v in value]
    return value

def _match(actual,wanted,bindings):
    name=actual['tool_name'];a=actual['arguments'];w=wanted['arguments']
    if name!=wanted['tool_name']:return False
    if name=='device_set':
        return a.get('device_id')==w['device_id'] and bool(a.get('changes')) and all(k in w['changes'] and equivalent(v,w['changes'][k],k) for k,v in a['changes'].items())
    if name in TARGET_FIELDS:
        key=TARGET_FIELDS[name]
        if a.get(key)!=bindings.get(w[key],w[key]):return False
        aa={k:v for k,v in a.items() if k!=key};ww={k:v for k,v in w.items() if k!=key}
        if name=='schedule_update':
            return bool(aa.get('patch')) and all(k in ww['patch'] and equivalent(_without_message(v),_without_message(ww['patch'][k]),k) for k,v in aa['patch'].items())
        return equivalent(aa,ww)
    return equivalent(_without_message(a),_without_message(w))

def _merge_device_grants(writes):
    merged={};others=[]
    for w in writes:
        if w['tool_name']!='device_set':others.append(w);continue
        a=w['arguments'];target=a['device_id']
        if target not in merged:merged[target]={'tool_name':'device_set','arguments':{'device_id':target,'changes':{}}}
        merged[target]['arguments']['changes'].update(a['changes'])
    return others+list(merged.values())

def analyze_authorization(case,sim):
    policy=case['evaluation'].get('behavior_policy') or compile_policy(case)
    policies={n['node_id']:n for n in policy['nodes']};refs={t['node_id']:t for t in case['reference']['turns']}
    violations=[];read_violations=[];bindings={};fallback_origin=None;calls_by_node={}
    # Legacy fixtures can omit begin_turn; end_turn records exact trace boundaries.
    for frame in getattr(sim,'turn_ranges',[]):
        for index in range(frame['start'],frame['end']):calls_by_node[index]=frame['node_id']
    for i,e in enumerate(sim.trace):
        node_id=e.get('node_id') or calls_by_node.get(i)
        if node_id=='FALLBACK':node_id=fallback_origin
        elif node_id:fallback_origin=node_id
        if node_id is None:
            # An unlabelled trajectory cannot borrow all-case authorization.
            node_id=case['interaction']['nodes'][0]['id'] if len(case['interaction']['nodes'])==1 else None
        rule=policies.get(node_id,{'allowed_read_tools':[],'allowed_writes':[]})
        c=e['call'];name=c['tool_name'];error=e['response'].get('error') or {}
        evidence={'request_id':e['request_id'],'node_id':node_id,'tool_name':name}
        if name in READ_TOOLS:
            if name not in rule['allowed_read_tools']:read_violations.append({**evidence,'reason':'explicitly_prohibited_read'})
            continue
        if name not in WRITE_TOOLS:continue
        # Recoverable lookup failure affects tool-use quality, not an actual wrong-target mutation.
        if error.get('code')=='NOT_FOUND':continue
        grants=_merge_device_grants(rule['allowed_writes'])
        matches=[w for w in grants if _match(c,w,bindings)]
        if not matches:
            violations.append({**evidence,'reason':'object_field_value_or_action_not_authorized_in_this_turn','arguments':copy.deepcopy(c['arguments'])})
            continue
        # Bind created identifiers from the observed causal path, never from future calls.
        data=e['response'].get('data') or {}
        actual_id=data.get('id') or (data.get('task') or {}).get('id')
        if actual_id:
            for r in refs.get(node_id,{}).get('calls',[]):
                if _match(c,r['call'],bindings):
                    expected_data=r['expected_response'].get('data') or {}
                    expected_id=expected_data.get('id') or (expected_data.get('task') or {}).get('id')
                    if expected_id:bindings.setdefault(expected_id,actual_id)
        # Check actual synchronous device effects too: accepted arguments are not proof
        # that the implementation touched only the requested device and values.
        before={d['id']:d['state'] for d in e['state_before']['devices']}
        after={d['id']:d['state'] for d in e['state_after']['devices']}
        for target,state in after.items():
            for field,value in state.items():
                if equivalent(before[target][field],value,field):continue
                allowed=False
                for grant in grants:
                    if grant['tool_name']!='device_set' or grant['arguments']['device_id']!=target:continue
                    changes=grant['arguments']['changes']
                    expected=ACTION_STATES.get(changes.get('cleaning_action')) if field=='cleaning_status' else changes.get(field)
                    if (field in changes or field=='cleaning_status' and 'cleaning_action' in changes) and equivalent(value,expected,field):allowed=True
                if not allowed:violations.append({**evidence,'reason':'unexpected_synchronous_device_effect','device_id':target,'field':field,'value':value})
    return violations,read_violations
