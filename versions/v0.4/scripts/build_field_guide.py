"""Generate the exhaustive declared-field index from the shipped schemas."""
import json
from pathlib import Path
CODE=Path(__file__).resolve().parents[1]
def read(p):return json.loads((CODE/p).read_text('utf-8'))
def cell(v):return str(v).replace('|','\\|').replace('\n',' ')
def walk(s,path=''):
    yield path or '(根对象)',s
    for name,child in s.get('properties',{}).items():yield from walk(child,path+'.'+name if path else name)
    if isinstance(s.get('items'),dict):yield from walk(s['items'],path+'[]')
    for i,sub in enumerate(s.get('anyOf',[])):
        if sub.get('type')!='null':yield from walk(sub,path)
def kind(s):
    if '$ref' in s:return s['$ref']
    return '/'.join(s['type']) if isinstance(s.get('type'),list) else s.get('type','anyOf' if 'anyOf' in s else 'object')
lines=['# v0.4 字段与证据说明','','题目结构、真实执行记录、工具合同分别保存在 `spec/case.schema.json`、`spec/run.schema.json`、`spec/sandbox.json`。下表从交付 schema 自动生成。原始模型响应和供应方 usage 是开放对象，保留供应方实际返回字段，不臆造统一字段。','','完整工具例题：[T10_101](../pilot/data/cases/T10_101.json)。完整聊天例题：[C06_102](../pilot/data/cases/C06_102.json)。对应三组原始执行 JSON 位于 `pilot/runs/<system_id>/<case_id>.json`，当前为本地开发验证记录。','','`null` 表示尚无结果或不适用，不等于零分。相对音频路径以所属 split 的根目录为准，例如 `benchmark/assets/audio/...`。同题共用同一份用户波形，三组不会分别重合成输入。','']
for title,file in [('题目','case.schema.json'),('实测记录','run.schema.json')]:
    lines.extend(['## '+title,'','| 字段路径 | 类型 | 含义 |','|---|---|---|'])
    seen=set()
    for path,s in walk(read('spec/'+file)):
        if path in seen:continue
        seen.add(path);desc=s.get('description','见下级字段；以 schema 定义为准。')
        if 'enum' in s:desc+=' 可选值：'+json.dumps(s['enum'],ensure_ascii=False)
        if 'const' in s:desc+=' 固定值：'+str(s['const'])
        lines.append(f'| `{path}` | {cell(kind(s))} | {cell(desc)} |')
    lines.append('')
design={'index':'本场景中的题号；开发集用101及以后，正式集用001–020。','split/partition':'development 或 test；开发不混入正式通过率。','grouped':'是否属于40%的成组题。','family':'组或独立题的稳定标识；开发、正式不共用family。','level':'成组题第1–4级；独立题为null。','difficulty':'预设 easy/medium/hard，不由模型成绩反推。','turns':'计划用户轮数，不把工具调用计作用户轮次。','variant':'夹具和声音选择的确定性变体索引。','group_size':'成组题4；独立题1。','progression':'同一任务逐步加入的上下文要求说明。','fixture_index':'生成冻结家庭夹具的确定性索引。','tool_profile':'core10；异步场景使用core10+async2。','core_constraints[]':'node_id、源用户must_satisfy、非强制解释acceptance_guidance、must_not、blocked_read_tools、restriction_evidence。','audio_facts[]':'node_id、kind、expected、required、source等；闭合数字核对规范。设备/传感器数值可从冻结reference额外导出。'}
lines+=['## 新增设计字段','','| `design` 子字段 | 说明 |','|---|---|']+[f'| `{k}` | {v} |' for k,v in design.items()]
lines+=['','## 中断与评分字段','','`execution.failure` 的 `stage/type/reason` 给出失败位置、异常类别与具体原因；`completed_user_turns/executed_tool_calls/current_turn_executed_tool_calls` 是已经真实发生的数量；`budget` 是当次约束；`infra_candidate` 只是网络/显存异常候选标记，仍须核验。正常完成时为null。','','`incomplete_turn.tool_events` 是中断前已执行的工具；`pending_tool_calls_not_executed` 是被预算阻止、没有执行的调用；`assistant_parts_not_spoken` 是产生但未朗读的文字，不能拿来替代音频打分。旧版缺失字段在页面显示“未记录”。','','`objective_audio_checks[]` 包含 `check_id/specification/status/local_asr_text/judge_heard_text/local_asr_match/judge_transcript_match/evaluator/scope`。两种转写一致仅是证据；单位归属、否定、上下文仍需语义评价。`audio_fact_review_required` 标记待复核，不自动把ASR识别错误算成模型错误。','','`case_pass` 是严格任务通过；六维分数不单独作为通过门槛。`task_achieved` 保留判官独立判断。`audio_judge` 保留模型、温度、请求ID、用量、提示哈希、证据哈希、听写与逐项理由。没有回答音频时不编造六维分数。','','## 工具沙箱','','每次返回统一 envelope：request_id、ok、status、data、error、operation_id、clock_time。工具调用的完整参数约束、返回结构及副作用说明见 [sandbox.json](../spec/sandbox.json)。','','| 工具 | 层级 | 用途 | 必需参数 |','|---|---|---|---|']
for t in read('spec/sandbox.json')['tools']:
    lines.append(f'| `{t["name"]}` | {"异步扩展" if t["name"].startswith("task_") else "常用"} | {cell(t["description"])} | {cell(", ".join(t["input_schema"].get("required",[])) or "无；按查询范围提供可选筛选")} |')
lines+=['','状态语义：等价时间按同一时刻比较；每次写入按当前轮授权的对象、字段和值核验；取消已取消安排幂等成功；播放新媒体会停止旧播放。动态ID不要求与参考完全一致。参考是已验证的一条合法路径，不能把其调用顺序当作唯一答案。','']
lines+=['## 最终机器裁定与原始评分','','- case_pass_primary：初判加客观规则得到的原始通过结论。','- semantic_review.result：盲化语义复核的检查项、严重错误和备注；proposed_case_pass只是候选结论，decision_status标记一致或曾有分歧。','- audio_adjudication.trigger：是否因语义分歧、数字待核验而重新听音。','- audio_adjudication.result：新一次真实听音返回的dimensions、semantic_checks、critical_failures、heard_turns、task_achieved、numeric_checks。最终任务通过使用本次语义及数字结论，并保留客观硬规则；总览质量均分仍使用初判，不择优混用。','- audio_adjudication中的version、model/requested_model、temperature、enable_thinking、prompt_sha256、evidence_sha256、request_id、usage、format_attempts、scope记录裁定协议、服务实际模型、配置、证据绑定和调用来源。格式重试只为获得首个结构有效结果，不按评分重试。','- numeric_checks逐项包含check_id、passed、heard、reason。客观数值检查中的fresh_audio_verification保留重听音后的核验；两个转写一致也不自动等于声学真值。','- reports/run_overview中的final_rating_source区分一致复核与重新听音裁定；audio_adjudicated表示是否完成新听音，不表示人评。','']
(CODE/'docs/FIELDS.md').write_text('\n'.join(lines),'utf-8')
print(json.dumps({'field_guide':'docs/FIELDS.md','lines':len(lines)}))
