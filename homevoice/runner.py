"""Audio-only harness. Hidden case truth never enters tested-model requests."""
import copy,hashlib,json,re,time,urllib.error,urllib.request
from pathlib import Path
from .sandbox import ROOT,Sandbox,compact_tools
from .speech_text import normalize,VERSION
from .grading import grade_rules
OFFICIAL={'temperature':1.0,'top_p':1.0,'top_k':20,'min_p':0.0,'presence_penalty':2.0,'seed':42,'max_tokens':512,'chat_template_kwargs':{'enable_thinking':False}}
def post(url,payload,timeout=180):
    req=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as res:return json.load(res)
    except urllib.error.HTTPError as e:raise RuntimeError(f'Local inference HTTP {e.code}: '+e.read().decode('utf-8',errors='replace')[:1000]) from None
def parse_raw(raw):
    calls=[]
    for i,m in enumerate(re.finditer(r'<tool_call>\s*(.*?)\s*</tool_call>',raw,re.S)):
        body=m[1].strip()
        if body.startswith('<function='):
            fn=re.fullmatch(r'<function=([A-Za-z_][A-Za-z0-9_]*)>\s*(.*?)\s*</function>',body,re.S)
            if not fn:raise ValueError('malformed XML function call')
            arguments={};params=list(re.finditer(r'<parameter=([A-Za-z_][A-Za-z0-9_]*)>\s*(.*?)\s*</parameter>',fn[2],re.S))
            remainder=re.sub(r'<parameter=[A-Za-z_][A-Za-z0-9_]*>\s*.*?\s*</parameter>','',fn[2],flags=re.S).strip()
            if remainder:raise ValueError('unparsed XML function argument')
            for p in params:
                if p[1] in arguments:raise ValueError('duplicate parameter')
                try:arguments[p[1]]=json.loads(p[2])
                except json.JSONDecodeError:arguments[p[1]]=p[2].strip()
            d={'name':fn[1],'arguments':arguments}
        else:d=json.loads(body)
        calls.append({'id':f'call_{i}','type':'function','function':{'name':d['name'],'arguments':json.dumps(d['arguments'],ensure_ascii=False)}})
    if '<tool_call>' in raw and not calls:raise ValueError('malformed tool call')
    spoken=re.sub(r'<tool_call>.*?</tool_call>|<think>.*?</think>','',raw,flags=re.S)
    spoken=re.sub(r'<\|[^>]+\|>','',spoken).strip()
    return spoken,calls
def model_projection(case):
    c=case['model_context']
    return [{'role':'system','content':c['system_prompt']+'\n可信当前用户：'+json.dumps(c['actor'],ensure_ascii=False)+'\n家庭公开信息：'+' '.join(c['public_facts'])}]
def execute(case,system,url):
    started=time.monotonic();sim=Sandbox(case['environment'],case['model_context']['actor']);history=model_projection(case);tools=compact_tools();turns=[];flags=[];requests=0;incomplete=None
    edge=system=='edge_native';model_id='EdgeInstant-Omni-2B-1106-Preview' if edge else 'Qwen3.5-'+('2B' if system=='qwen35_2b' else '4B')
    nodes={n['id']:n for n in case['interaction']['nodes']};assets={a['node_id']:a for a in case['variants'][0]['audio_assets']};budget=case['interaction']['budget'];node_id=case['interaction']['start_node_id'];fallback_used=0;resume=None
    try:
        if case['variants'][0]['status']!='ready':raise ValueError('input_audio_not_verified')
        while node_id and len(turns)<budget['max_user_turns']:
            sim.begin_turn(node_id,len(turns)+1)
            audio=assets[node_id];path=ROOT/audio['path'];digest=hashlib.sha256(path.read_bytes()).hexdigest()
            if digest!=audio['sha256']:raise ValueError('input_audio_hash_mismatch')
            asr=None
            if edge:content=[{'type':'audio','audio':str(path)}]
            else:
                a=json.loads((ROOT/'runs/asr'/f'{digest}.json').read_text('utf-8'));asr=a['text'];content=asr
            history.append({'role':'user','content':content});before_trace=len(sim.trace);parts=[];raw_responses=[];tick=time.monotonic();consecutive=0;finish='stop'
            incomplete={'node_id':node_id,'input_audio':audio['path'],'input_audio_sha256':digest,'asr_text':asr,'assistant_parts_not_spoken':parts,'model_raw_responses':raw_responses,'first_tool_event_index':before_trace}
            while True:
                if requests>=budget['max_model_calls']:raise ValueError('model_call_budget_exceeded')
                if time.monotonic()-started>budget['wall_timeout_s']:raise ValueError('interaction_wall_budget_exceeded')
                requests+=1
                if edge:
                    r=post(url+'/infer',{'messages':history,'tools':tools});raw_responses.append(r);spoken,calls=parse_raw(r['raw_output']);finish=r.get('finish_reason','stop')
                    message={'role':'assistant','content':spoken,'tool_calls':calls} if calls else {'role':'assistant','content':spoken}
                else:
                    r=post(url+'/v1/chat/completions',{'model':model_id,'messages':history,'tools':tools,'tool_choice':'auto',**OFFICIAL});raw_responses.append(r);choice=r['choices'][0];message=choice['message'];spoken=message.get('content') or '';calls=message.get('tool_calls') or [];finish=choice.get('finish_reason','stop')
                    if not calls and '<tool_call>' in spoken:
                        spoken,calls=parse_raw(spoken);message={'role':'assistant','content':spoken,'tool_calls':calls}
                history.append(message)
                if spoken.strip():parts.append(spoken.strip())
                if finish=='length':flags.append('output_token_budget_exceeded')
                if not calls:break
                if consecutive+len(calls)>budget['max_consecutive_tool_calls'] or len(sim.trace)+len(calls)>budget['max_tool_calls']:raise ValueError('tool_call_budget_exceeded')
                for i,c in enumerate(calls):
                    fn=c['function'];args=fn['arguments'];args=json.loads(args) if isinstance(args,str) else args
                    response=sim.call(fn['name'],args);history.append({'role':'tool','tool_call_id':c['id'],'content':json.dumps(response,ensure_ascii=False)})
                consecutive+=len(calls)
            raw_text='\n'.join(parts);spoken_text=normalize(raw_text);speech=None
            if edge and spoken_text:speech=post(url+'/speak',{'text':raw_text},timeout=180)
            if not raw_text:flags.append('empty_spoken_response')
            actual_node=resume if node_id=='FALLBACK' else node_id
            sim.end_turn(actual_node)
            turn={'user_turn_index':len(turns)+1,'node_id':node_id,'input_variant_id':'A0','input_audio':audio['path'],'input_audio_sha256':digest,'delivered_text':None,'asr_text':asr,'assistant_text':raw_text,'spoken_text':spoken_text,'normalizer_version':VERSION,'assistant_audio':speech,'tool_events':copy.deepcopy(sim.trace[before_trace:]),'model_raw_responses':raw_responses,'wall_seconds':time.monotonic()-tick,'finish_reason':finish,'routing_label':'normal','selected_branch_id':None}
            turns.append(turn)
            incomplete=None
            if node_id=='FALLBACK':node_id=nodes[resume]['next_node_id'];resume=None;continue
            node=nodes[node_id]
            # Frozen visible-text router. It cannot inspect hidden goals or future answers.
            asks=bool(re.search(r'(请问|哪[个一间盏]|几点|什么时候|能否.{0,8}告诉|可以.{0,8}告诉|需要.{0,8}确认)',raw_text)) and bool(re.search(r'[？?]',raw_text))
            if asks and node['clarification_branches']:
                branch=node['clarification_branches'][0];turn['routing_label']='predefined_clarification';turn['selected_branch_id']=branch['id'];node_id=branch['next_node_id']
            elif asks and case['classification']['category']=='tool' and not node['next_node_id'] and fallback_used<1 and len(turns)<5:
                fallback_used+=1;resume=node_id;node_id='FALLBACK';turn['routing_label']='bounded_fallback'
            else:node_id=node['next_node_id']
        if node_id:flags.append('user_turn_budget_exceeded')
        status='completed' if not flags else 'failed'
    except Exception as e:
        flags.append(type(e).__name__+': '+str(e));status='failed'
    checks=grade_rules(case,sim)
    from .revision import protocol_metadata
    return {'record_kind':'actual_model_run','schema_version':'0.3.0','revision':protocol_metadata(case,'v0.3_actual_execution'),'case_id':case['identity']['case_id'],'case_sha256':hashlib.sha256(json.dumps(case,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'system_id':system,'model_id':model_id,'input_modality':'audio','asr_model':None if edge else 'Qwen3-ASR-0.6B','tts_model':'native_talker' if edge else 'Qwen3-TTS-0.6B','normalizer_version':VERSION,'generation':{'do_sample':False,'max_tokens':256,'seed':42} if edge else OFFICIAL,'execution':{'status':status,'model_calls':requests,'tool_calls':len(sim.trace),'wall_seconds':time.monotonic()-started,'flags':flags,'timing_scope':'interaction_stage; offline ASR and baseline batch TTS reported separately'},'turns':turns,'tool_trace':sim.trace,'incomplete_turn':incomplete,'rule_checks':checks,'final_state':sim.state,'audio_judge':None,'case_pass':None,'task_achieved':None}
