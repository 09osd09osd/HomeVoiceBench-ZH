"""Accepted development report, without claiming independent human calibration."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import CODE_ROOT
ROOT=CODE_ROOT/'pilot'
def read(rel):return json.loads((ROOT/rel).read_text('utf-8'))
s=read('reports/summary.json');runs=read('reports/run_overview.json');gate=read('reports/acceptance.json');cal=read('reports/semantic_regression.json');pipeline=read('reports/pipeline.json')
labels={'edge_native':'实验组 EdgeInstant','qwen35_2b':'Qwen 2B 级联','qwen35_4b':'Qwen 4B 级联'}
out=['# v0.4 · 100题开发验证报告','','60道工具题、40道聊天题，覆盖全部50个场景，40%成组题，三组各运行100题。与正式1000题分别统计。','',f'技术与评分验收：{gate["status"]}。用户已授权采用修复后的机器评分流程开展全量运行。尚未进行独立人工校准。','','| 系统 | 初判通过 | 复核候选通过 | 曾有分歧 | 重新听音裁定 | 最终通过 |','|---|---:|---:|---:|---:|---:|']
for r in s['semantic_consistency_review']['systems']:
    out.append(f'| {labels[r["system_id"]]} | {r["primary_passed"]}/100 | {r["review_proposed_passed"]}/100 | {r["disputed"]} | {r["audio_adjudicated"]} | {r["final_passed"]}/100 |')
out+=['','初判听取真实用户与助手音频；语义复核使用实际听写及工具证据，隐藏模型身份和初判标签/理由。两次冲突或闭集数字存疑时，重新听原音频，以首个结构有效的裁定为准。客观规则失败不能被覆盖。全部阶段使用同一Qwen3.8模型，不能称为独立判官或人工金标。质量六维保留初判，与任务通过分开报告。','','## 输入修复与保留','','9题原稿曾混入工具字段名称：T06_101–104、T11_101–104、T12_101。仅改为自然中文，目标、参数值、轮次和授权不变；三组对称重跑这9题。其余91题在冻结数据及旧运行哈希一致后复用，没有选择较好答案。',f'当前原稿检查受影响题数：{read("reports/spoken_source_lint.json")["affected_cases"]}。','','此前两轮100题完整保留在 pilot_history/initial_protocol 和 pilot_history/pre_full_run_protocol；原始v0.3保持不变。','','## Greedy与吞吐','','三组内容和工具决策均为greedy：Qwen温度0、top_k=1、top_p=1；Edge do_sample=false。语音合成保留原采样配置，数字和单位共用朗读规范化。','','| 系统 | 客户端并发 | 最近交互阶段耗时 | 处理范围 |','|---|---:|---:|---|']
for system,label in labels.items():
    timing=[x for x in pipeline['stages'] if x['stage']=='main_'+system][-1];workers=read('reports/worker_selection_'+system+'.json')['workers']
    out.append(f'| {label} | {workers} | {timing["seconds"]:.1f} 秒 | 仅9题重跑，其余缓存复用 |')
out+=['','以上是离线阶段墙钟时间，不是100题全部重新推理耗时或用户端到端延迟。ASR、TTS、评分另计。云端任务与GPU重叠，本机一次只装载一个主模型。小样本探测和缓存命中不能用于宣称稳定的加速倍数。','','## 评分校验边界','',f'早期4个代理审查反例匹配预定判断 {sum(x["passed"] for x in cal["rows"])}/4。它们用于暴露边界，不是独立人工金标；未匹配记录保留。技术验收表示覆盖、哈希及协议执行检查完成，不代表判官准确率已通过人评校准。','','## 曾有分歧的记录','','试听页同时显示初判、复核、最终机器听音裁定、录音和工具轨迹。可选人工备注不会覆盖机器原始证据。','','| 系统 | 题号 | 初判 | 复核候选 | 最终 | 试听 |','|---|---|---|---|---|---|']
disputes=[r for r in runs if r.get('semantic_disputed')]
def verdict(x):return '通过' if x is True else '失败' if x is False else '待定'
for r in disputes:
    cid=r['case_id'];out.append(f'| {labels[r["system_id"]]} | {cid} | {verdict(r["case_pass_primary"])} | {verdict(r["review_proposed_case_pass"])} | {verdict(r["case_pass"])} | [打开](http://127.0.0.1:18788/review/?dataset=pilot#case={cid}) |')
out+=['','[评分协议](FULL_RUN_POLICY.md) · [字段说明](FIELDS.md) · [100题Excel](../pilot/outputs/homevoicebench-v040/HomeVoiceBench-ZH-v0.4.xlsx) · [保留校验](PRESERVATION.json)','']
(CODE_ROOT/'docs/PILOT_REPORT.md').write_text('\n'.join(out),'utf-8')
(ROOT/'reports/semantic_disputes.json').write_text(json.dumps(disputes,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'report':'docs/PILOT_REPORT.md','disputes':len(disputes),'acceptance':gate['status']}))
