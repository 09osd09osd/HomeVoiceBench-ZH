"""Typed, deliberately narrow semantic equality for sandbox state.

Only schema date-time fields and documented unordered collections are normalized.
Multiplicity, arbitrary strings, ordered action lists, nulls and booleans remain
meaningful; invalid timestamps never become equal to valid timestamps.
"""
import datetime, json

VERSION='typed_state_v0.3'
DATETIME_FIELDS={'at','created_at','updated_at','last_triggered_at','observed_at','start_at','current_at','clock_time'}
UNORDERED_FIELDS={'schedules','playbacks','tasks','weekdays','target_room_ids'}

def canonical(value, field=None):
    if isinstance(value,dict):return {k:canonical(v,k) for k,v in sorted(value.items())}
    if isinstance(value,list):
        items=[canonical(x) for x in value]
        return sorted(items,key=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False)) if field in UNORDERED_FIELDS else items
    if isinstance(value,bool):return {'$boolean':value}
    if isinstance(value,str) and field in DATETIME_FIELDS:
        try:
            instant=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
            if instant.tzinfo is not None:return {'$instant':instant.astimezone(datetime.timezone.utc).isoformat(timespec='microseconds')}
        except ValueError:pass
    return value

def equivalent(a,b,field=None):return canonical(a,field)==canonical(b,field)

def state_projection(state):
    out={'devices':{d['id']:d['state'] for d in state['devices']},'schedules':[],'playbacks':[],'tasks':[]}
    for s in state['schedules']:
        out['schedules'].append({k:s[k] for k in ['owner_id','kind','when','status']} | {'payload':{'target_device_id':s['payload']['target_device_id'],'actions':s['payload']['actions']}})
    for p in state['playbacks']:out['playbacks'].append({k:p[k] for k in ['owner_id','device_id','content_id','status','position_s']})
    for t in state['tasks']:out['tasks'].append({k:t[k] for k in ['owner_id','operation','target_id','status']})
    return out
