"""Build the formal report only after complete technical acceptance."""
import collections,datetime,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from homevoice.paths import CODE_ROOT
ROOT=CODE_ROOT/'benchmark'
def read(rel):return json.loads((ROOT/rel).read_text('utf-8'))
s=read('reports/summary.json');gate=read('reports/acceptance.json');runs=read('reports/run_overview.json');pipeline=read('reports/pipeline.json')
assert gate['status']=='passed' and s['evaluation_status']=='complete'
assert len(runs)==3000 and all(type(r['case_pass']) is bool for r in runs)
labels={'edge_native':'实验组 EdgeInstant','qwen35_2b':'Qwen 2B 级联','qwen35_4b':'Qwen 4B 级联','all':'全部','tool':'工具','chat':'聊天'}
out=['# v0.4 · 正式1000题测评报告','',f'统计时间：{s["generated_at"]}。1000题、3000份系统运行记录均已归档并给出最终判定，证据完整性检查通过。执行中断的记录仍计为失败；独立100题开发集另外报告。','','600工具题、400聊天题，共50个场景，每场景20题；400道成组题，基础/标准/挑战分别600/300/100题。用户输入只有语音，三组内容和工具决策均为greedy。判官Qwen3.8-Omni-Flash温度0。','','| 系统 | 类别 | 通过 / 计划 | 通过率 | 有声音初评数 | 六维均分 / 5 |','|---|---|---:|---:|---:|---:|']
for r in s['systems']:
    mean='NA' if r['overall_dimension_mean'] is None else f'{r["overall_dimension_mean"]:.2f}'
    out.append(f'| {labels[r["system_id"]]} | {labels[r["category"]]} | {r["passed_count"]}/{r["planned"]} | {r["strict_pass_rate"]:.1%} | {r["judged_count"]} | {mean} |')
out+=['','没有完成的音频或执行失败仍计入分母；没有可听输出的题不虚构声音质量分。任务通过率采用修复后的最终裁定；六维质量均分保留首次听音评分，未用后续裁定覆盖。','','## 按预设用户轮数','','| 系统 | 轮数 | 通过 / 计划 | 通过率 |','|---|---:|---:|---:|']
for r in s['by_planned_user_turns']:
    if r['category']=='all':out.append(f'| {labels[r["system_id"]]} | {r["planned_user_turns"]} | {r["passed_count"]}/{r["planned"]} | {r["strict_pass_rate"]:.1%} |')
out+=['','## 预设难度与成组任务','','| 系统 | 难度 | 通过 / 计划 | 通过率 |','|---|---|---:|---:|']
for r in s['by_difficulty']:
    out.append(f'| {labels[r["system_id"]]} | {r["difficulty"]} | {r["passed"]}/{r["planned"]} | {r["pass_rate"]:.1%} |')
out+=['','| 系统 | 完整四级均通过 | 全部题组 | 第一级即失败 | 后级通过但前级失败的题组 |','|---|---:|---:|---:|---:|']
for system in ('edge_native','qwen35_2b','qwen35_4b'):
    groups=[g for g in s['group_progression'] if g['system_id']==system]
    nonmonotone=sum(any(a['passed'] is False and b['passed'] is True for i,a in enumerate(g['results']) for b in g['results'][i+1:]) for g in groups)
    out.append(f'| {labels[system]} | {sum(all(r["passed"] for r in g["results"]) for g in groups)} | {len(groups)} | {sum(g["first_failed_level"]==1 for g in groups)} | {nonmonotone} |')
out+=['','成组题是观察证据，可能出现后级通过但前级失败；首次失败不能直接定义普适能力上限。不同轮数包含不同任务组合，横向差异也不能全部归因于上下文长度。','','## 50场景任务通过率','','| 场景 | 实验组 | 2B级联 | 4B级联 |','|---|---:|---:|---:|']
for scene in read('reports/scene_overview.json'):
    rates=[]
    for system in ('edge_native','qwen35_2b','qwen35_4b'):
        rr=[r for r in runs if r['system_id']==system and r['scene_id']==scene['scene_id']]
        rates.append(f'{sum(r["case_pass"] for r in rr)}/{len(rr)}')
    out.append('| '+scene['scene_id']+' '+scene['title']+' | '+' | '.join(rates)+' |')
out+=['','不同轮数包含不同任务组合，横向差异不能全部归因于上下文长度；同任务成组结果见Excel的Groups表。','','## 固定评分流程','','程序检查逐轮授权、每次写入及最终状态；时间按同一时刻比较。初判与盲化语义复核有分歧或闭集数字存疑时，按固定协议重新听原音频。采用首个结构有效的裁定，禁止选较高分；客观失败不可被覆盖。所有原判和工具证据均保留。','','| 系统 | 初判通过 | 复核候选通过 | 曾有分歧 | 音频复裁 | 最终通过 |','|---|---:|---:|---:|---:|---:|']
for r in s['semantic_consistency_review']['systems']:
    out.append(f'| {labels[r["system_id"]]} | {r["primary_passed"]} | {r["review_proposed_passed"]} | {r["disputed"]} | {r["audio_adjudicated"]} | {r["final_passed"]} |')
out+=['','各阶段使用同一模型，未经过独立人工校准。技术验收检查可复现性、证据完整性和协议执行，不等于验证判官准确率。','','## 系统配对比较','','| 系统A | 系统B | 类别 | A−B（百分点） | 95%区间（百分点） |','|---|---|---|---:|---:|']
if (ROOT/'reports/scoring_format_recovery.json').exists():
    out[-4:-4]=['格式恢复记录：一份故事题连续四次返回非规范JSON，辅助复核工作器停止。相同音频和评分标准下，第五次得到首个有效结构并判失败；没有挑选较高分。所有无效响应保留，最终批处理补齐其余复核。见 [格式恢复证据](../benchmark/reports/scoring_format_recovery.json)。','']
for r in s['paired_comparisons']:
    lo,hi=r['cluster_bootstrap_95_ci'];out.append(f'| {labels[r["system_a"]]} | {labels[r["system_b"]]} | {labels[r["category"]]} | {100*r["pass_rate_difference"]:+.1f} | [{100*lo:+.1f}, {100*hi:+.1f}] |')
out+=['','按工具/聊天分层，以场景为簇做2000次配对bootstrap，seed=42。区间不覆盖判官偏差或不同随机seed。','','## 执行失败与效率','','| 系统 | 执行未完成 | 主要标记（可重叠） |','|---|---:|---|']
for system in ('edge_native','qwen35_2b','qwen35_4b'):
    rr=[r for r in runs if r['system_id']==system];counts=collections.Counter('context_window_exceeded' if 'exceed_context_size_error' in f or 'exceeds the available context size' in f else f for r in rr for f in r.get('flags',[]));detail='；'.join(f'{k}: {v}' for k,v in counts.most_common(6)) or '无'
    out.append(f'| {labels[system]} | {sum(r["execution_status"]!="completed" for r in rr)} | {detail} |')
out+=['','下面按固定优先顺序将失败分流，每份失败只计入一类；这用于排查，不能替代逐项错误分析。','','| 系统 | 执行中断 | 客观规则未过 | 语音预算截断 | 语义/数字/严重错误 |','|---|---:|---:|---:|---:|']
for system in ('edge_native','qwen35_2b','qwen35_4b'):
    failure_counts=collections.Counter()
    for r in runs:
        if r['system_id']!=system or r['case_pass']:continue
        if r['execution_status']!='completed':kind='execution'
        elif not r['rule_pass']:kind='objective'
        else:
            raw=read(r['run_path'])
            kind='speech_budget' if any((t.get('assistant_audio') or {}).get('hit_frame_budget',False) for t in raw['turns']) else 'semantic'
        failure_counts[kind]+=1
    out.append('| '+labels[system]+' | '+' | '.join(str(failure_counts[k]) for k in ['execution','objective','speech_budget','semantic'])+' |')
out+=['','试听页展示具体中断原因、已执行调用、未执行请求和未朗读文字；未朗读文字不能当作语音回复。','','| 阶段 | 实测墙钟秒数 |','|---|---:|']
for r in pipeline['stages']:out.append(f'| {r["stage"]} | {r["seconds"]:.1f} |')
tts=read('reports/tts_batches.json')
batch_sizes=collections.Counter(b['n'] for b in tts['batches'])
batch_detail='；'.join(f'批量{n}：{count}批' for n,count in sorted(batch_sizes.items(),reverse=True)) or '全部命中缓存'
out+=['',f'本次级联TTS新合成 {tts["completed_tasks"]} 条回复，实际批次为：{batch_detail}。资源失败后降批重试 {len(tts["resource_retries"])} 次，失败尝试与批次成员保存在 speech_resource_attempts 和 speech_batches 中；没有替换已保存的模型文字答案。输出ASR按实际音频时长分批，具体顺序规则见 output_asr_effective.batch_order。']
stream=read('reports/judge_stream_status.json')
elapsed=datetime.datetime.fromisoformat(gate['checked_at']).timestamp()-stream['started_at_unix']
out+=['',f'本次正式推理与评分调度的墙钟时间约 {elapsed/60:.1f} 分钟，从流式评分器启动算到完整性检查结束，包含模型装载与阶段间等待；不含此前制题、用户语音准备及之后的文件导出和上传。起止证据为 judge_stream_status.started_at_unix 与 acceptance.checked_at。','','以上是离线分阶段吞吐。云端评分与GPU重叠，audio_judge阶段主要记录尾部等待和补齐，不能当作全部评分耗时。阶段时间不可简单相加为用户延迟；ASR/声音按哈希缓存，缓存缩短不能宣称为模型本身加速。输入语音预热与补齐另见 benchmark/reports/input_audio_preparation_history.json。','','## 解释边界','','- 干净合成普通话、单seed、单一听音判官，未独立人评校准；不外推为真实家庭远场或噪音表现。','- 开发与测试题号及题组分离，但共用场景模板，不等同于跨领域泛化。','- 部署精度、后端和语音预算存在差异；比较对象是完整系统。','- 不按期望通过率筛选题目或答案；模型失败保留，基础设施异常单独检查。','- v0.3及此前两轮100题均保留；新旧分数不能直接解释为模型进步。','','[逐题试听](http://127.0.0.1:18788/review/?dataset=benchmark) · [Excel](../benchmark/outputs/homevoicebench-v040/HomeVoiceBench-ZH-v0.4.xlsx) · [图文说明](index.html) · [字段说明](FIELDS.md) · [评分协议](FULL_RUN_POLICY.md) · [100题报告](PILOT_REPORT.md)','']
(CODE_ROOT/'docs/FINAL_REPORT.md').write_text('\n'.join(out),'utf-8')
print(json.dumps({'report':'docs/FINAL_REPORT.md','records':len(runs),'acceptance':gate['status']}))
