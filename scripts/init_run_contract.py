"""Write the executed protocol rather than retaining unimplemented draft fields."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.runner import OFFICIAL
from homevoice.speech_text import VERSION
def field(t,d,**kw):return {'type':t,'description':d,**kw}
def obj(d,p,required=None):return field('object',d,properties=p,required=list(p) if required is None else required,additionalProperties=False)
def arr(d,item):return field('array',d,items=item)
def nullable(s):return {'anyOf':[s,{'type':'null'}],'description':s.get('description','')}
text=lambda d:field('string',d)
num=lambda d:field('number',d)
boolean=lambda d:field('boolean',d)
opaque=lambda d:field('object',d,additionalProperties=True)
audio=opaque('实际输出音频及溯源：path/sha256/duration_s/sample_rate_hz/model/normalizer_version/spoken_text；Edge 另含 raw_text、ended、hit_frame_budget、wall_seconds，baseline 另含 text、batch_offset、batch_seed、batch_keys、external_cloud_tts。原生音频缓存耗时不是当前调用的实时延迟。')
event=obj('真实工具调用与状态快照',{'request_id':text('沙箱请求ID'),'call':opaque('tool_name 与 arguments；参数严格匹配 sandbox.json 中该工具 input_schema'),'response':opaque('真实工具响应；匹配该工具 output_schema'),'state_before':opaque('执行前完整家庭状态'),'state_after':opaque('执行后完整家庭状态')})
# The trace includes sandbox clock/event metadata; preserve it under the sandbox contract.
event=opaque('沙箱事件：request_id、call(tool_name/arguments)、response、state_before/state_after 及逻辑时间；状态类型见 types.schema.json。')
turn=obj('实际发生的一轮用户交互，含工具循环',{
 'user_turn_index':field('integer','从1开始，含澄清',minimum=1,maximum=5),'node_id':text('已投递预写节点，或 FALLBACK'),'input_variant_id':text('A0：唯一语音输入变体'),
 'input_audio':text('仓库相对路径；发布包解压后可访问'),'input_audio_sha256':text('实际投递波形的 SHA256'),'delivered_text':field('null','没有把题目原文作为文字投递；baseline 的识别结果另记 asr_text'),
 'asr_text':nullable(text('baseline 实际 ASR 识别文本；原生模型为 null')),'assistant_text':text('模型原始可朗读回答，不含结构化工具调用'),'spoken_text':text('共享数字/单位规范化后的朗读文本'),'normalizer_version':text('朗读转换版本'),
 'assistant_audio':nullable(audio),'tool_events':arr('本轮真实调用顺序',event),'model_raw_responses':arr('每次推理的完整原始响应；OpenAI兼容模型保留 choices/usage/timings，原生保留 raw_output/token计数/audio_evidence/finish_reason/worker耗时',opaque('供应方或本地适配器原始响应，不作为判官听音的替代')),
 'wall_seconds':num('该轮交互阶段耗时；baseline 不含离线ASR和TTS；不可横向当作端到端延迟'),'finish_reason':text('最后一次生成结束原因'),'routing_label':field('string','固定路由器决策',enum=['normal','predefined_clarification','bounded_fallback']),'selected_branch_id':nullable(text('命中预定义澄清分支ID'))})
schema=obj('真实运行记录；参考答案在 case 文件中独立保存',{
 'record_kind':field('string','仅真实运行',const='actual_model_run'),'schema_version':field('string','结构版本',const='0.2.0'),'case_id':text('用例ID'),'case_sha256':text('运行当时完整用例的规范JSON SHA256：sort_keys=True, ensure_ascii=False 默认分隔符 UTF-8'),'system_id':field('string','系统ID',enum=['qwen35_2b','qwen35_4b','edge_native']),'model_id':text('被测核心模型名称'),
 'input_modality':field('string','统一语音输入',const='audio'),'asr_model':nullable(text('baseline识别模型；Edge为null')),'tts_model':text('baseline语音合成模型或 native_talker'),'normalizer_version':text('共享转换版本'),'generation':opaque('实际生成参数；见 evaluation_profiles.json'),
 'execution':obj('执行证据',{'status':field('string','失败包括真实预算/格式问题与基础设施异常，须结合 flags 判断',enum=['completed','failed']),'model_calls':field('integer','实际推理请求数',minimum=0),'tool_calls':field('integer','实际工具调用数',minimum=0),'wall_seconds':num('整题交互阶段耗时'),'flags':arr('失败或截断标记，不以假分数替代',text('标记或异常类型与说明')),'timing_scope':text('明确计时范围')}),
 'turns':arr('已完成交互轮次；异常发生的未完成轮可能不在此数组中',turn),'rule_checks':arr('客观状态检查',obj('单项判定',{'check_id':text('对应 evaluation.checks.id'),'passed':boolean('客观规则通过与否'),'observed':{'description':'实际观察、差异状态或违规列表'},'evaluator':text('规则引擎版本')})),
 'tool_trace':arr('整题完整沙箱日志，包含未完成轮内已发生的调用',event),'incomplete_turn':nullable(opaque('预算、格式或服务错误发生时保存的未完成轮：node_id/input_audio/input_audio_sha256/asr_text/assistant_parts_not_spoken/model_raw_responses/first_tool_event_index。未朗读文字不可作为实际音频评分。')),
 'final_state':opaque('真实终态，见 types.schema.json 家庭状态定义'),'audio_judge':nullable(opaque('实际听音评分记录：model/requested_model/temperature/enable_thinking/request_id/usage/prompt_sha256/audio_sha256/model_answer_text_supplied/result。result 含 dimensions、semantic_checks、critical_failures、heard_turns、task_achieved；分数是0–5整数。')),
 'case_pass':nullable(boolean('严格整题通过；未完成评判为null，执行失败可为false且维度分数仍未知')),'task_achieved':nullable(boolean('判官判断用户主要目标是否达到；与严格通过率分开')),'judge_status':text('scored，或没有可评分回答时的明确原因')},required=None)
schema['required'].remove('judge_status');schema['$schema']='https://json-schema.org/draft/2020-12/schema';schema['$id']='https://homebench.example/spec/0.2/run.schema.json'
(ROOT/'spec/run.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n','utf-8')
profiles={'schema_version':'0.2.0','input_modality':'audio','normalizer_version':VERSION,'user_text_generator':{'model':'deepseek-v4.1-flash','role':'wording and a second same-model review; executable ground truth authored first'},'user_tts':{'model':'qwen-audio-3.1-tts-next','sample_rate_hz':24000,'channels':1,'concurrency':16},'audio_judge':{'model':'qwen3.8-omni-flash','temperature':0,'enable_thinking':False,'answer_text_supplied':False,'required_evidence':'actual input and output WAVs plus sandbox trace'},'qwen_baselines':{'models':['Qwen3.5-2B','Qwen3.5-4B'],'runtime':'llama.cpp b11552','quantization':'Q8_0','generation':OFFICIAL,'asr':'Qwen3-ASR-0.6B','tts':'Qwen3-TTS-12Hz-0.6B-CustomVoice','tts_voice':'Vivian','context_per_slot':8192,'context_shift':False},'edge_native':{'model':'EdgeInstant-Omni-2B-1106-Preview','generation':{'do_sample':False,'max_new_tokens':256,'seed':42},'context_limit':8192,'input_sample_rate_hz':16000,'output_sample_rate_hz':24000,'external_asr':False,'external_tts':False,'dtype':'published mixed BF16/FP32, auto','attention':'sdpa'},'budget':{'max_user_turns':5,'max_tool_calls':12,'max_consecutive_tool_calls':4,'max_model_calls':30,'interaction_wall_timeout_s':300},'dialogue_router':{'version':'visible_regex_v1','model':None,'rules':'normal next_node_id; explicit question + predefined branch selects first matching stored branch; tool terminal question may consume one fixed FALLBACK within five user turns','limitations':'fixed follow-up dialogue; cannot cover arbitrary user behavior; questions without recognized markers may follow normal route'},'timing_policy':'offline throughput only; precomputed ASR and batch TTS are reported separately; interaction time is not comparable end-to-end latency','reporting':'all 1000 cases per system in strict pass denominator; unjudged dimensions are NA; failures never become fabricated zero audio scores'}
(ROOT/'spec/evaluation_profiles.json').write_text(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n','utf-8')
print('Wrote actual run schema and evaluation profiles')
