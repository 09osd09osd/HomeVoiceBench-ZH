"""Concurrent DeepSeek authoring with resumable, immutable per-batch evidence."""
import argparse,concurrent.futures,copy,hashlib,json,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.blueprints import blueprint
from homevoice.catalog import SCENES
from homevoice.cloud import ROOT,chat,response_json,redact
from homevoice.sandbox import validate,REGISTRY
from jsonschema import Draft202012Validator
SCHEMA=json.loads((ROOT/'spec/case.schema.json').read_text('utf-8'))
PROMPT='''你是居家语音交互基准的数据作者。所有人物与家庭均为虚构。请根据给定的任务骨架生成中文口语用户台词及参考回答要点。只返回JSON对象，cases数组，每项字段严格为case_id,title,nodes。nodes每项字段node_id,user_text,reference_text。
工具题：必须逐轮保留骨架的全部对象、参数值、时间、否定、授权范围、错误处理要求。可以把生硬字段译成自然中文，但不能改事实，不能添加任何新的操作要求。把百分比、模式、档位等清楚表达。用正常家人的说法，不出现JSON、字段名、工具名、系统提示或评测说明。参考回答以提供的expected_response为事实，pending不能称已完成，故障要诚实说明。用户不应该知道未被其听到的隐藏ID。
聊天题：把骨架发展成具体、连贯、自然的独立对话。每题有不同生活细节，覆盖补充限制、修正、情感与记忆。用户后续台词不能依赖某句尚未生成的助手回答，不使用“选第二个”“你刚才说的那个方案”等不存在的固定答案。可以依赖用户自己已经说出的事实。没有真实工具操作请求。参考答案为可接受回答示范，并明确本轮必要内容；不能宣称唯一正确话术。科学知识取常识范围，避免医疗法律电气维修细节和时效性新闻。不要制造需查网才能评分的问题。
通用：用户每轮大约10至70个汉字，可按意图必要长度调整；不含旁白、括号动作说明或朗读指令。参考回答约15至100字，适合说出来。保持节点数和ID不变，最多5轮。每题标题具体，有区分度。请用数字保留关键数值，不能偷换对象和范围。'''
REVIEW='''你是严格的中文语音测试数据审题员。比较冻结的工具题原始任务骨架与改写台词，检查每一轮有没有遗漏或改变对象、数值、时间、动作、否定、授权范围、失败处理条件。不能靠参考回答弥补用户台词缺失。聊天题检查对话是否具体连贯，后续用户是否依赖尚未产生的助手答案、是否含真实工具操作要求、是否出现无法验证的时效事实。只返回JSON：{"cases":[{"case_id":"...","valid":true或false,"issues":["..."]}]}。合格要求语义忠实，而非字面一致。'''
LOCK=threading.Lock();COUNTER={'complete':0,'failed':0}
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8');tmp.replace(path)
def summary(c):
    return {'case_id':c['identity']['case_id'],'category':c['classification']['category'],'scene':c['classification']['scene_title'],'tags':c['classification']['tags'],'nodes':[{'node_id':n['id'],'task_brief':n['user_text'],'tone':n['tone'],'reference_trace':r['calls'],'reference_requirements':r['assistant_text']} for n,r in zip(c['interaction']['nodes'],c['reference']['turns'])]}
def run_batch(job):
    scene,indices=job;label=f'{scene["scene_id"]}_{indices[0]:03d}-{indices[-1]:03d}';rawfile=ROOT/'data/authoring'/f'{label}.json'
    cases=[blueprint(scene,i) for i in indices];briefs=[summary(c) for c in cases]
    prompt=hashlib.sha256(PROMPT.encode()).hexdigest()
    source_hash=hashlib.sha256(json.dumps(briefs,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    record=json.loads(rawfile.read_text('utf-8')) if rawfile.exists() else None
    if record is not None and (record.get('blueprint_sha256')!=source_hash or record.get('prompt_sha256')!=prompt):
        save(ROOT/'data/authoring/history'/f'{label}-{record["prompt_sha256"][:8]}.json',record);record=None
    if record is None:
        record=None;feedback=''
        for attempt in range(3):
            response=chat('deepseek-v4.1-flash',[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(briefs,ensure_ascii=False)+feedback}],temperature=0.85,max_tokens=6500)
            try:generated=response_json(response)
            except (ValueError,KeyError) as e:
                save(ROOT/'data/authoring/rejected'/f'{label}-author-{attempt}.json',response)
                feedback='\n上次输出不是合法完整JSON，请完整重写，不要注释、代码省略或尾逗号。';continue
            if len(generated.get('cases',[]))!=len(cases):feedback='\n上次输出题数不正确，请完整输出。';continue
            review_result=chat('deepseek-v4.1-flash',[{'role':'system','content':REVIEW},{'role':'user','content':json.dumps({'blueprints':briefs,'candidate':generated},ensure_ascii=False)}],temperature=0,max_tokens=1800)
            try:review=response_json(review_result)
            except (ValueError,KeyError):
                save(ROOT/'data/authoring/rejected'/f'{label}-review-{attempt}.json',review_result);continue
            found={x['case_id']:x for x in review.get('cases',[])}
            if all(found.get(c['identity']['case_id'],{}).get('valid') is True for c in cases):
                record={'blueprint_sha256':source_hash,'prompt_sha256':prompt,'requested_model':'deepseek-v4.1-flash','returned_model':response.get('model'),'request_id':response.get('id',response.get('request_id')),'usage':response.get('usage'),'review_request_id':review_result.get('id',review_result.get('request_id')),'review_usage':review_result.get('usage'),'review':review,'attempt':attempt+1,'generated':generated};save(rawfile,record);break
            feedback='\n上次审题发现以下问题，请本次修复且保持原始任务不变：'+json.dumps(review,ensure_ascii=False)
        if record is None:raise ValueError('authoring_review_failed:'+label)
    generated={x['case_id']:x for x in record['generated']['cases']}
    for c in cases:
        cid=c['identity']['case_id'];g=generated[cid]
        assert [x['node_id'] for x in g['nodes']]==[x['id'] for x in c['interaction']['nodes']],cid+' node identity mismatch'
        c['identity']['title']=g['title'];c['provenance'].update(model=record['returned_model'],request_id=record['request_id'],prompt_id=record['prompt_sha256'])
        # Request-level usage lives in authoring record/ledger; do not multiply batch usage into each case.
        c['provenance']['source_refs']=[f'data/authoring/{label}.json']
        for node,ref,authored in zip(c['interaction']['nodes'],c['reference']['turns'],g['nodes']):
            assert isinstance(authored['user_text'],str) and len(authored['user_text'])>=4
            node['user_text']=authored['user_text'];ref['assistant_text']=authored['reference_text']
        c['quality'].update(schema_validation='passed',reference_rule_validation='passed',independent_review='pending')
        c['quality']['known_limitations'].append('已由DeepSeek同模型另一次请求审题，不等同独立模型或人工审核。')
        # All possible delivered user utterances, including fallback, get an audio record.
        texts=[(x['id'],x['user_text'],x['tone']) for x in c['interaction']['nodes']]+[('FALLBACK',c['interaction']['clarification']['fallback_text'],'平静')]
        for node,text,tone in texts:
            c['variants'][0]['audio_assets'].append({'asset_id':f'{cid}_{node}','node_id':node,'status':'planned','path':None,'sha256':None,'duration_s':None,'sample_rate_hz':None,'channels':None,'codec':None,'tts_model':'qwen-audio-3.1-tts-next','voice_id':None,'seed':20261116+int(cid[-3:]),'tone':tone,'noise_condition':'clean_synthetic_speech','transcript_gt':text,'qc_status':'not_run','qc_asr_text':None,'processing':[]})
        validate(c,SCHEMA);save(ROOT/'data/cases'/f'{cid}.json',c)
    with LOCK:
        COUNTER['complete']+=len(cases);print(json.dumps({'batch':label,**COUNTER},ensure_ascii=False),flush=True)
    return len(cases)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=8);ap.add_argument('--scenes',default='all');ap.add_argument('--batch-size',type=int,default=5);args=ap.parse_args()
    save(ROOT/'spec/scenarios.json',SCENES);save(ROOT/'spec/authoring_prompts.json',{'author':PROMPT,'review':REVIEW,'temperature':0.85,'review_temperature':0})
    scenes=SCENES if args.scenes=='all' else [s for s in SCENES if s['scene_id'] in args.scenes.split(',')]
    jobs=[(s,list(range(i,min(21,i+args.batch_size)))) for s in scenes for i in range(1,21,args.batch_size)]
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for fut in concurrent.futures.as_completed([pool.submit(run_batch,j) for j in jobs]):
            try:fut.result()
            except Exception as e:
                with LOCK:COUNTER['failed']+=1
                errors.append(redact(e));print(json.dumps({'error':redact(e)},ensure_ascii=False),flush=True)
    save(ROOT/'reports/text_generation.json',{'requested_cases':len(scenes)*20,'complete_this_invocation':COUNTER['complete'],'failed_batches':errors,'max_concurrency':args.workers,'status':'passed' if not errors else 'incomplete'})
    if errors:raise SystemExit(1)
