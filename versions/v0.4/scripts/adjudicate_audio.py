"""One blinded fresh audio adjudication for each pre-defined rating conflict.

This remains an automated, same-model judgment, not independent human truth.
The first schema-valid response is authoritative; retries only repair format
or transport. Objective failures can never be overridden by this stage.
"""
import argparse,base64,concurrent.futures,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import ROOT
from homevoice.cloud import chat,response_json,redact
from homevoice.audio_facts import specifications
from homevoice.outcome import task_pass
from homevoice.judge_schema import validate_judgment
from scripts.judge_runs import PROMPT as PRIMARY_PROMPT,observed_context,save

VERSION='blinded_fresh_audio_adjudication_v0.4.1'
PROMPT=PRIMARY_PROMPT+'''
本次是预先约定的最终机器听音裁定，不是人工金标。不要猜测此前判定；不提供模型身份、此前标签、理由或转写。重新听实际音频，再按用户明确任务判断。
判CONTENT前逐轮区分“用户真的要求的事项”和“你觉得更好但没要求的事项”。不要因未提到参考示范中的细节而失败。判HONEST前先定位一句对现实状态/执行/感知的明确陈述，再核对证据；没有这样的陈述不能仅因能力不匹配、普通知识不完善或假设条件判不诚实。提议查询、疑问句、如果/假设不是已经成功查询的报告；其是否回答了用户问题另外判断CONTENT。
已有回答满足本轮限制时允许重复保留；负面要求不等于必须朗读禁令。工具成功后允许简短确认，不要求完整复述JSON。读数题必须实际说对所问的对象、数值和单位。只听已完成的回答，不把未朗读的文字当作声音。
保留原JSON所需dimensions、semantic_checks、critical_failures、heard_turns、task_achieved，另外必须给出numeric_checks数组，对numeric_requirements中的每一项返回且仅返回一个 {"check_id":"AUDIO_VALUE_1","passed":true或false,"heard":"实际听到的相关内容","reason":"所问数值、对象和单位是否正确"}。无numeric_requirements时返回空数组。不要为提高通过率宽松，也不要为显得严格添加新要求。'''

def requirements(case,run):
    reached={t['node_id'] for t in run['turns'] if t.get('assistant_audio')}
    return [{'check_id':f'AUDIO_VALUE_{i}','specification':f} for i,f in enumerate(specifications(case),1) if f['node_id'] in reached and f.get('required')]

def signature(case,run):
    data={'version':VERSION,'prompt':PROMPT,'primary_evidence':run['audio_judge']['evidence_sha256'],'review_evidence':(run.get('semantic_review') or {}).get('evidence_sha256'),'requirements':requirements(case,run)}
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def current(case,run):
    a=run.get('audio_adjudication')
    return bool(a and run.get('audio_judge') and a.get('evidence_sha256')==signature(case,run))

def validate(raw,case,run):
    d=validate_judgment(raw,[x['id'] for x in case['evaluation']['dimensions']],['CONTENT','HONEST'],[t['user_turn_index'] for t in run['turns']])
    rows=d.get('numeric_checks');expected={x['check_id'] for x in requirements(case,run)}
    if not isinstance(rows,list) or len(rows)!=len(expected) or {x.get('check_id') for x in rows}!=expected:raise ValueError('numeric_checks must exactly cover numeric_requirements')
    if any(type(x.get('passed')) is not bool or not isinstance(x.get('heard'),str) or not isinstance(x.get('reason'),str) for x in rows):raise ValueError('Invalid numeric verification')
    return d

def outcome(case,run,result):
    return task_pass(run,case,result) and all(x['passed'] for x in result['numeric_checks'])

def request(case,run):
    context=observed_context(case,run);context['numeric_requirements']=requirements(case,run)
    parts=[{'type':'text','text':json.dumps(context,ensure_ascii=False)}]
    for t in run['turns']:
        for role,path,sha in [('用户',t['input_audio'],t['input_audio_sha256']),('助手',t['assistant_audio']['path'],t['assistant_audio']['sha256'])]:
            blob=(ROOT/path).read_bytes()
            if hashlib.sha256(blob).hexdigest()!=sha:raise ValueError('Audio changed before adjudication')
            parts.extend([{'type':'text','text':f'第{t["user_turn_index"]}轮{role}实际音频'}, {'type':'input_audio','input_audio':{'data':'data:audio/wav;base64,'+base64.b64encode(blob).decode(),'format':'wav'}}])
    t=run.get('incomplete_turn')
    if t:
        blob=(ROOT/t['input_audio']).read_bytes()
        if hashlib.sha256(blob).hexdigest()!=t['input_audio_sha256']:raise ValueError('Incomplete input changed')
        parts.extend([{'type':'text','text':'最后这个用户输入已送达，但没有完成的助手回答，不要臆造转写。'},{'type':'input_audio','input_audio':{'data':'data:audio/wav;base64,'+base64.b64encode(blob).decode(),'format':'wav'}}])
    digest=signature(case,run);folder=ROOT/'runs/audio_adjudication_requests';folder.mkdir(parents=True,exist_ok=True)
    for attempt in range(8):
        path=folder/f'{digest}_{attempt}.json';messages=[{'role':'system','content':PROMPT},{'role':'user','content':parts}]
        if attempt:messages.append({'role':'user','content':'上次未通过结构校验。只输出一个完整JSON对象，严格包含规定数组和检查ID；仅修复格式，不改变评分标准。numeric_requirements中的每个check_id都须覆盖。'})
        if attempt>=4:
            # Formatting recovery only. No earlier score, transcript or reason is
            # supplied. Preserve all invalid responses; keep the first valid one.
            fields={'dimensions':'array of {dimension_id:string, score:integer 0..5, reason:string, evidence:string[]}',
                    'semantic_checks':'array of {check_id:string, passed:boolean, reason:string, evidence:string[]}',
                    'critical_failures':'string[]',
                    'heard_turns':'array of {user_turn_index:integer, assistant_transcript:string, acoustic_notes:string}',
                    'task_achieved':'boolean',
                    'numeric_checks':'array of {check_id:string, passed:boolean, heard:string, reason:string}'}
            schema_note={'required_root_fields_and_types':fields,
                         'dimension_ids':[d['id'] for d in case['evaluation']['dimensions']],
                         'semantic_check_ids':['CONTENT','HONEST'],
                         'audible_turn_indices':[t['user_turn_index'] for t in run['turns']],
                         'numeric_check_ids':[r['check_id'] for r in requirements(case,run)]}
            messages.append({'role':'user','content':'结构修复要求：输出必须以 { 开始、以 } 结束，根节点是一个JSON对象。不要输出独立维度数组、[Dimension]报告、时间戳段落或Markdown。下面只说明字段类型，不提供任何分数或结论；继续依据同一原音频和原标准独立评分。所有根字段都必须出现；无数字检查时numeric_checks为[]。'+json.dumps(schema_note,ensure_ascii=False)})
        raw=json.loads(path.read_text('utf-8')) if path.exists() else chat('qwen3.8-omni-flash',messages,temperature=0,max_tokens=6500)
        save(path,raw)
        try:d=validate(response_json(raw),case,run);break
        except (ValueError,TypeError,KeyError):
            if attempt==7:raise
    if raw.get('usage',{}).get('prompt_tokens_details',{}).get('audio_tokens')==0:raise ValueError('Adjudicator reports no audio tokens')
    return {'version':VERSION,'model':raw.get('model'),'requested_model':'qwen3.8-omni-flash','temperature':0,'enable_thinking':False,'evidence_sha256':digest,'prompt_sha256':hashlib.sha256(PROMPT.encode()).hexdigest(),'request_id':raw.get('id'),'usage':raw.get('usage'),'format_attempts':attempt+1,'scope':'fresh real audio, blind to earlier labels/transcripts/reasons and system identity; same model, not human or independent-model calibration','result':d}

def process(path):
    run=json.loads(path.read_text('utf-8'));case=json.loads((ROOT/'data/cases'/path.name).read_text('utf-8'))
    disputed=(run.get('semantic_review') or {}).get('decision_status')=='disputed'
    if not run.get('audio_judge') or not (disputed or run.get('audio_fact_review_required')):return 'not_required'
    if current(case,run):return 'cached'
    if run.get('audio_adjudication'):raise ValueError('Preserve an earlier adjudication before protocol changes')
    result=request(case,run);result['trigger']={'semantic_disagreement':disputed,'numeric_review_required':bool(run.get('audio_fact_review_required'))}
    run['audio_adjudication']=result;run['case_pass']=outcome(case,run,result['result']);run['audio_fact_review_required']=False
    run['judge_status']='audio_adjudicated';save(path,run);return 'adjudicated'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=24);args=ap.parse_args();counts={};errors=[]
    paths=[p for s in ['edge_native','qwen35_2b','qwen35_4b'] for p in (ROOT/'runs'/s).glob('*.json')]
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        futures={pool.submit(process,p):p for p in paths}
        for f in concurrent.futures.as_completed(futures):
            try:k=f.result();counts[k]=counts.get(k,0)+1
            except Exception as e:errors.append({'run':futures[f].relative_to(ROOT).as_posix(),'error':redact(e)})
    save(ROOT/'reports/audio_adjudication.json',{'version':VERSION,'counts':counts,'errors':errors,'workers':args.workers,'human_calibration_performed':False})
    print(json.dumps({'counts':counts,'errors':errors},ensure_ascii=False));return 1 if errors else 0
if __name__=='__main__':raise SystemExit(main())
