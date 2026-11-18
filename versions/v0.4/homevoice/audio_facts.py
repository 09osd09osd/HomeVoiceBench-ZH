"""Closed factual checks over independently transcribed actual audio.

Transcription is neural evidence, not ground truth. Disagreement stays visible
as needs_review; it never silently fails a model or fills in missing speech.
"""
import re
from .speech_text import normalize,number,digits
VERSION='closed_audio_values_v0.4'
def specifications(case):
    out=list(case['design'].get('audio_facts',[]));scene=case['classification']['scene_id']
    for turn in case['reference']['turns']:
        node=turn['node_id']
        for event in turn['calls']:
            call=event['call'];response=event['expected_response']
            if not response.get('ok'):continue
            data=response.get('data') or {}
            if call['tool_name']=='sensor_read' and scene in ['T16','T17','T18']:
                sensors=data if isinstance(data,list) else data.get('readings',data.get('sensors',[]))
                for sensor in sensors:
                    if type(sensor.get('value')) in [int,float]:out.append({'node_id':node,'kind':'sensor_value','expected':sensor['value'],'unit':sensor.get('unit'),'metric':sensor.get('metric'),'required':True,'source':'frozen_sensor_fixture'})
            if call['tool_name']=='device_query':
                fields={'T03':{'U1':'brightness_pct','U2':'opening_pct','U3':'target_temperature_c','U5':'brightness_pct'},'T06':{'U3':'brightness_pct'},'T07':{'U3':'color_temperature_k'},'T08':{'U3':'target_temperature_c'},'T09':{'U3':'opening_pct','U5':'opening_pct'},'T10':{'U5':'fan_speed'},'T12':{'U3':'volume_pct'},'T05':{'U1':'volume_pct','U4':'volume_pct'}}
                field=fields.get(scene,{}).get(node)
                if field:
                    for d in data.get('devices',[]):
                        val=d.get('state',{}).get(field)
                        if type(val) in [int,float]:out.append({'node_id':node,'kind':'device_state_value','expected':val,'field':field,'device_id':d['id'],'required':True,'source':'frozen_reference_state'})
    return out

def contains_value(text,value):
    canonical=normalize(text).replace('两','二').replace('〇','零')
    # Bound both sides so e.g. 一百二十二 cannot match 十二 or 二十二.
    numeric='零一二三四五六七八九十百千万亿点负正'
    candidates=[number(str(value)),digits(str(value))]
    return any(re.search('(?<!['+numeric+'])'+re.escape(v)+'(?!['+numeric+'])',canonical) for v in candidates)

def evaluate(case,run,transcripts):
    heard={h['user_turn_index']:h['assistant_transcript'] for h in (run.get('audio_judge') or {}).get('result',{}).get('heard_turns',[])};turns={t['node_id']:t for t in run['turns']};out=[]
    for i,fact in enumerate(specifications(case),1):
        t=turns.get(fact['node_id']);status='unreached_or_no_audio';a=b=None;asr=None;j=None
        if t and t.get('assistant_audio'):
            sha=t['assistant_audio']['sha256'];asr=transcripts.get(sha);j=heard.get(t['user_turn_index'])
            if asr is not None and j is not None:
                a=contains_value(asr,fact['expected']);b=contains_value(j,fact['expected'])
                status='value_present_in_both' if a and b else 'needs_review' if a!=b else 'value_missing_in_both'
            else:status='pending_transcription'
        out.append({'check_id':f'AUDIO_VALUE_{i}','specification':fact,'status':status,'local_asr_text':asr,'judge_heard_text':j,'local_asr_match':a,'judge_transcript_match':b,'evaluator':VERSION,'scope':'Numeric presence only; association, units, negation and context remain semantic checks.'})
    return out
