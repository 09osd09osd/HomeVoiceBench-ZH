"""Strict judge validation; normalize only unambiguous field-name aliases."""
import copy
def validate_judgment(raw,dimension_ids,check_ids,turn_ids):
    if not isinstance(raw,dict):raise ValueError('root must be one JSON object, not a list or per-turn objects')
    d=copy.deepcopy(raw)
    for key in ['dimensions','semantic_checks','critical_failures','heard_turns']:
        if not isinstance(d.get(key),list):raise ValueError(key+' must be an array')
    for entry in d['dimensions']:
        if not isinstance(entry,dict):raise ValueError('dimension entries must be objects')
        if 'dimension_id' not in entry and 'id' in entry:entry['dimension_id']=entry.pop('id')
    for entry in d['semantic_checks']:
        if not isinstance(entry,dict):raise ValueError('semantic check entries must be objects')
        if 'check_id' not in entry and 'id' in entry:entry['check_id']=entry.pop('id')
    scores={x.get('dimension_id'):x for x in d['dimensions']}
    if set(scores)!=set(dimension_ids) or len(scores)!=len(d['dimensions']):raise ValueError('dimensions must contain exactly one entry for each required ID')
    if any(type(x.get('score')) is not int or not 0<=x['score']<=5 for x in scores.values()):raise ValueError('score must be an integer from 0 through 5')
    checks={x.get('check_id'):x for x in d['semantic_checks']}
    if set(checks)!=set(check_ids) or len(checks)!=len(d['semantic_checks']):raise ValueError('semantic_checks must contain exactly every required check ID')
    if any(type(x.get('passed')) is not bool for x in checks.values()):raise ValueError('passed must be boolean')
    if any(not isinstance(x,dict) for x in d['heard_turns']):raise ValueError('heard_turns entries must be objects')
    if len(d['heard_turns'])!=len(turn_ids) or {x.get('user_turn_index') for x in d['heard_turns']}!=set(turn_ids):raise ValueError('heard_turns must cover each actual audible turn exactly once')
    if any(not isinstance(x.get('assistant_transcript'),str) for x in d['heard_turns']):raise ValueError('actual audible transcription is required')
    if type(d.get('task_achieved')) is not bool or any(not isinstance(x,str) for x in d['critical_failures']):raise ValueError('invalid outcome types')
    for x in list(scores.values())+list(checks.values()):
        if not isinstance(x.get('reason'),str) or not isinstance(x.get('evidence'),list) or any(not isinstance(e,str) for e in x['evidence']):raise ValueError('reason string and evidence string array are required')
    return d
