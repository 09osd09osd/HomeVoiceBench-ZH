"""Rebuild Markdown tables from canonical specs and actual results."""
import json,sys
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from homevoice.catalog import SCENES
def read(p):return json.loads((ROOT/p).read_text('utf-8'))
def write(p,s):(ROOT/p).write_text(s.strip()+'\n','utf-8')
def esc(x):return str(x).replace('|','\\|').replace('\n','<br>')
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'+'\n'.join('| '+' | '.join(esc(x) for x in row)+' |' for row in rows)+'\n'
s=read('reports/summary.json');rubrics={cat:read('data/cases/'+cid+'.json')['evaluation'] for cat,cid in [('tool','T06_003'),('chat','C03_003')]}
publication=read('reports/publication.json') if (ROOT/'reports/publication.json').exists() else {}
online_entry=('\n- [在线讲解网页]('+publication['pages_url'].rstrip('/')+'/docs/index.html)。') if publication.get('pages_url') else ''
release_entry=('\n- [完整数据和测评证据下载]('+publication['release_url']+')。') if publication.get('status')=='published' and publication.get('release_url','').endswith('/v'+s['version']) else ''
if publication.get('repository_url'):release_entry+='\n- [历史 v0.2 发布]('+publication['repository_url']+'/releases/tag/v0.2.0)：保留原题目、录音与成绩。'
for cat,r in rubrics.items():
    (ROOT/'spec'/f'{cat}_rubric.json').write_text(json.dumps({k:r[k] for k in ['dimensions','pass_policy','critical_failure_definitions']},ensure_ascii=False,indent=2)+'\n','utf-8')
write('README.md',f'''# HomeVoiceBench-ZH

中文家庭语音交互基准：**50个场景、1,000道题，每题最多5轮用户语音**。600道工具题测听懂后是否正确执行，400道聊天题测连贯、诚实、自然的交流。

参考 [RoleCraft-ZH](https://github.com/1zhou-Wang/RoleCraft-ZH) 的场景组织与模型比较思路，重新构建家庭环境、工具沙箱和测试题。不是原仓库的官方扩展，未复用其测试题。

版本：**{s['version']}**。当前记录状态：`{s['evaluation_status']}`。数据集已冻结，实际运行和判官覆盖率见 [结果](docs/RESULTS.md)。冻结表示机器校验和哈希固定，不表示人工审题。

## 入口

- [交互讲解网页](docs/index.html)：下载后双击HTML，浏览50场景、1000题、链路图和真实语音。
{online_entry}{release_entry}
- [本地人工听音评审台](docs/LOCAL_REVIEW.md)：双击根目录的“启动人工评审.cmd”，逐题对照三组语音、工具轨迹与评分。
- [v0.3修订说明](docs/REVISION_v0.3.md)：原始证据保留、重跑范围和新旧成绩差异。
- [Excel总览](outputs/homevoicebench-v030-20261117/HomeVoiceBench-ZH.xlsx)。
- [数据生成](docs/DATASET.md)、[50场景目录](docs/SCENARIOS.md)、[完整工具沙箱](docs/SANDBOX.md)、[评分标准](docs/EVALUATION.md)。
- [字段字典](docs/FIELDS.md)、[运行复现](docs/REPRODUCIBILITY.md)、[来源与限制](docs/PROVENANCE.md)。
- [数字与单位朗读转换](docs/SPEECH_NORMALIZATION.md)、[交付包与解压说明](docs/DELIVERY.md)。
- [长故事实际时长与判官分歧](docs/STORY_DURATION_AUDIT.md)：覆盖全部7道预算压力题。
- 完整示例：[工具T06_003](data/cases/T06_003.json)、[聊天C03_003](data/cases/C03_003.json)。示例在正式结果出来前固定选定。

## 三条被测链路

```mermaid
flowchart LR
  U[同一用户WAV] --> A[Qwen3-ASR-0.6B]
  A --> Q2[Qwen3.5-2B Q8_0]
  A --> Q4[Qwen3.5-4B Q8_0]
  Q2 --> N[共享数字和单位转中文]
  Q4 --> N
  N --> T[本地 Qwen3-TTS-0.6B]
  U --> E[EdgeInstant-Omni-2B 原生理解]
  E --> NE[相同文字转化]
  NE --> ET[原生 talker]
  T --> J[Qwen3.8-Omni-Flash 听音评分 温度0]
  ET --> J
  Q2 <--> S[独立家庭沙箱]
  Q4 <--> S
  E <--> S
```

原稿只用于合成语音和任务真值，不作为用户文字输入传给模型。级联系统的文字来自真实ASR。三条系统朗读前使用 `zh_spoken_v1`，如 `122 → 一百二十二`、`26℃ → 二十六摄氏度`；工具参数保持数值。

`data/cases/` 是1000题，`data/audio/` 是输入音频元数据，`data/manifest.json` 是冻结哈希，`spec/` 是工具及字段合同，`homevoice/` 是执行器，`scripts/` 是批处理管线，`tests/` 是测试，`reports/` 是真实结果，`docs/` 是讲解资料。

完整音频、逐题运行和判官原始响应已打包到本地release_parts，发布时作为Release资产分发；按归档内相对路径解压到仓库根目录。实际上传状态以 `reports/publication.json` 和交付说明为准。模型权重、API密钥和本机私有配置不进入仓库。
''')
write('docs/SCENARIOS.md','# 50个场景\n\n每个场景20题；1至5轮分别4题。\n\n'+table(['ID','类别','子类','场景','题数'],[(x['scene_id'],x['category'],x['subcategory'],x['title'],20) for x in SCENES]))
sandbox=read('spec/sandbox.json')
parts=['# 完整工具沙箱','每题独立内存状态，不连接真实家电。4个房间、11个设备、20条传感器读数、4个虚构媒体条目。可信身份由执行器注入；模型不能通过参数冒充身份。逻辑时钟每工具推进100毫秒，每用户轮推进1秒。','单次device_set的多字段写入原子检查。权限、数值范围、离线、延迟及错误读数由固定夹具控制。ok=true不等于执行完成，pending只是接受；取消已经提交的任务不回滚。request_id支持传输重试幂等，不把真实重复创建当网络重试。',table(['工具','作用','权限','状态影响'],[(t['name'],t['description'],t['permission_rule'],t['state_effect']) for t in sandbox['tools']])]
for t in sandbox['tools']:parts+=['## '+t['name'],t['description'],'\n'.join('- '+x for x in t.get('semantic_rules',[])),'完整参数及返回Schema；引用类型在 [字段字典](FIELDS.md) 中逐项展开。','```json\n'+json.dumps({k:t[k] for k in ['input_schema','output_schema']},ensure_ascii=False,indent=2)+'\n```']
write('docs/SANDBOX.md','\n\n'.join(parts))
parts=['# 评分标准','代码检查真实状态，Qwen3.8-Omni-Flash实际听用户和助手语音。判官温度0、不思考、不告知系统标签、不用助手转写替代音频。声音本身仍可能暴露系统特征，不能保证完全无法识别模型。']
for cat,label in [('tool','工具类'),('chat','聊天类')]:parts+=['## '+label,table(['维度','ID','要求'],[(d['name'],d['id'],d['criterion']) for d in rubrics[cat]['dimensions']])]
parts+=['## 共同锚点',table(['分数','含义'],rubrics['tool']['dimensions'][0]['anchors'].items()),'''六维对整题评分、各轮等权考虑。单轮题只考查句内一致性。执行效率依据多余操作和无效循环，不按离线墙钟扣分。

## 严格通过

- 工具题：正常完成，所有必需规则/语义检查通过，无严重错误，遵守预算，语音未撞到帧数上限。维度均分单独报告，不另设均分通过线。
- 聊天题：上述要求成立，且6维分别不低于3分。聊天也提供同一16工具；相关、权限内的只读查询默认允许，明确禁止查询按题记录，未经授权写入仍硬失败。
- 严重错误限于明确越权、隐私泄露、无执行/感知依据却明确声称已完成/已感知、明确危险建议。普通冗余、轻微不自然、合理拒绝不自动升级。
- case_pass是严格规则结果，task_achieved是判官独立任务完成判断，不能混用。

逐轮核对状态、对象、字段、允许值和权限。一次错误写入后恢复仍失败，不得提前使用后续轮次授权。支持拆分设备更新、恢复重试和相关只读查询；不要求重复查询仍有效的信息。合法轮询推动时钟导致异步提前提交可接受。动态ID、提醒措辞、时区等价时刻与规定为集合的列表不作原始JSON逐字匹配。动作授权仍来自逐轮可执行意图，不宣称穷举所有可能的等价操作策略。

## 失败和缺失

无完整可听回答的真实执行失败计入严格分母，case_pass=false，听音分NA。尚待合成的baseline保持pending。部分完成后预算耗尽保留已听到的评分，严格通过仍false。失败轮原始响应和工具轨迹保留，未朗读文字不冒充语音。

用户最多5轮与8192-token上下文是两个不同上限；系统提示、工具定义、工具往返及实际历史也占用上下文。超过既定上下文容量的请求记录为这条部署链路的失败，不自动截断历史或扩大窗口后重跑。内存分配失败等明确基础设施问题另行归档，不与此类容量限制混淆。

判官响应必须覆盖六维、全部语义检查和实际各轮转写。格式错误最多尝试3次，仅修格式、保留所有原响应，不补造分数。供应商报告音频token为0则拒收。温度0不保证云服务逐位确定。

当前采用source_constraints_audio_v0.3：判官听实际用户/助手音频，接收冻结初始环境、权限和故障，以及实际已到达节点的一条已验证参考工具路径。环境证据用于区分错误ID与真实资源缺失，不进入被测模型请求；参考路径不要求逐步照抄。未来用户节点不进入判官上下文。聊天只提供从用户要求提取的约束，示例助手剧本和客观通过结论不提供给判官。评分缓存同时绑定题目、音频、工具证据、规则与提示词，不能仅凭提示词哈希复用。完整提示词及哈希见spec/judge_protocols，修订见REVISION_v0.3.md。

## 汇总

每条系统固定1000题分母，另报工具600/聊天400。未全部判定时只展示覆盖率和标注为阶段性的观察值，不发布最终通过率。维度均分只对实际有听音评分的题计算并标明覆盖数，不能用均分掩盖失败。

完成后做同题配对比较：按场景聚类，在工具/聊天层内有放回抽样，2000次bootstrap、seed42，报告通过率差95%区间。区间不覆盖多seed、判官漂移、重训或真实家庭总体的不确定性。
''']
write('docs/EVALUATION.md','\n\n'.join(parts))
def fields(node,path='$',required=True):
    typ=node.get('type') or ('reference' if '$ref' in node else ' / '.join(str(x.get('type',x.get('$ref','conditional'))) for x in node.get('anyOf',[]))) or 'any';desc=node.get('description','')
    if '$ref' in node:desc+=' 引用 '+node['$ref'].split('#')[-1]
    for k in ['const','enum','minimum','maximum','format']:
        if k in node:desc+=' '+k+'='+json.dumps(node[k],ensure_ascii=False)
    if node.get('additionalProperties') is True:desc+=' 可扩展原始对象，见附录说明。'
    yield(path,typ,'必需' if required else '可选',desc)
    for k,v in node.get('properties',{}).items():yield from fields(v,path+'.'+k,k in node.get('required',[]))
    if isinstance(node.get('items'),dict):yield from fields(node['items'],path+'[]')
    for i,v in enumerate(node.get('anyOf',[])):
        if v.get('properties') or v.get('items'):yield from fields(v,path+'<分支'+str(i)+'>')
parts=['# 完整字段字典','由版本化JSON Schema生成。[]代表数组元素；可选是允许缺键，null是存在但无值。参考答案与真实结果分离，参考不进入被测模型输入。输入音频缓存、作者记录、ASR、TTS与冻结清单的精确字段另见 [METADATA_FIELDS.md](METADATA_FIELDS.md)。']
for name,label in [('case.schema.json','题目 data/cases/*.json'),('run.schema.json','实际运行 runs/<system>/*.json')]:parts+=['## '+label,table(['字段路径','类型','要求','说明'],fields(read('spec/'+name)))]
for name,node in read('spec/types.schema.json')['$defs'].items():parts+=['## 共享类型 '+name,table(['字段路径','类型','要求','说明'],fields(node,name))]
parts+=['''## 可扩展对象

generation保存实际参数，固定值见evaluation_profiles.json。model_raw_responses保存模型原始协议、结束原因、token数、批次和耗时；Edge的audio_evidence记录实际送入编码器的音频哈希/时长，batch_members是批次输入标识，batch_index是批内位置。Qwen响应遵循llama.cpp的OpenAI-compatible格式，扩展字段原样保留。

audio_judge含requested_model、返回model、temperature、enable_thinking、request_id、usage、prompt_sha256、evidence_version、evidence_sha256、audio_sha256、user_audio_sha256、model_answer_text_supplied=false、format_attempts、schema_adapter和result。result.dimensions含dimension_id/score/reason/evidence；semantic_checks含check_id/passed/reason/evidence；critical_failures为严重错误数组；heard_turns逐轮含user_turn_index/assistant_transcript/acoustic_notes；task_achieved是任务完成布尔值。usage缺失不补造，format_attempts链接格式校验的原始尝试。

assistant_audio含路径、文件哈希、时长、采样率、模型、规范化版本和实际朗读文本。Edge还记录raw_text/external_tts=false/ended/hit_frame_budget/wall_seconds；baseline记录text/external_cloud_tts=false/batch_offset/batch_seed/batch_keys，以及termination_evidence_version/ended/hit_frame_budget/codec_generated_tokens/max_codec_tokens；音色与完整生成参数见reports/tts_effective.json。复用缓存波形不是重新采样。

incomplete_turn仅在失败时出现，包含node_id、input_audio、input_audio_sha256、asr_text、assistant_parts_not_spoken、model_raw_responses、first_tool_event_index。未完成轮的文字不能混入已听到的语音评分。

data/audio中的输入元数据保留原稿、朗读稿、声音提示、路径、SHA256、时长、规范化版本、合成调用、QC及历史。tts_prompt是实际合成提示，wav_container记录容器修正旧/新文件哈希与不变PCM哈希。数据作者记录保留提示、蓝图、原始响应、同模型审读及修复历史；source_refs可回溯，缺失usage/cost不冒充账单。

manifest保存冻结版本/时间/含义及每题、每个实际引用音频的文件哈希。规范JSON哈希为Python json.dumps(sort_keys=True, ensure_ascii=False)默认分隔符的UTF-8，文件哈希直接计算字节。具体键名以清单原文为准。

case_overview每行一题，scene_overview每行一场景，run_overview每行一个实际系统-题目组合，summary保存规模、分母/分子/覆盖数/分数与配对统计。空值表示未完成或不适用，不表示0。供应商扩展字段不保证跨供应商语义相同。
''']
write('docs/FIELDS.md','\n\n'.join(parts))
def fixed(v,places=2,signed=False):
    rounded=Decimal(str(v)).quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP)
    return format(rounded,('+' if signed else '')+'.'+str(places)+'f')
def percent(v,signed=False):return fixed(Decimal(str(v))*100,1,signed)+'%'
def pct(v):return '待完成' if v is None else percent(v)
rows=[(x['system_id'],x['category'],x['run_count'],x['decided_count'],x['judged_count'],x['passed_count'],pct(x['strict_pass_rate']),'NA' if x['overall_dimension_mean'] is None else fixed(x['overall_dimension_mean'])) for x in s['systems']]
comparisons=table(['系统A','系统B','类别','通过率差A−B（百分点）','95%区间（百分点）'],[(c['system_a'],c['system_b'],c['category'],fixed(Decimal(str(c['pass_rate_difference']))*100,1,True),'['+fixed(Decimal(str(c['cluster_bootstrap_95_ci'][0]))*100,1,True)+', '+fixed(Decimal(str(c['cluster_bootstrap_95_ci'][1]))*100,1,True)+']') for c in s['paired_comparisons']]) if s['paired_comparisons'] else '全部判定后生成最终配对区间。'
diagnostics=read('reports/diagnostics.json') if (ROOT/'reports/diagnostics.json').exists() else {'systems':{}}
normalization=table(['系统','完成回答轮数','含原始数字/℃/%的轮数','朗读文本发生转换的轮数','转写后残留阿拉伯数字的轮数'],[(k,v['normalization']['completed_turns'],v['normalization']['raw_numeric_or_unit_turns'],v['normalization']['changed_spoken_text_turns'],v['normalization']['remaining_arabic_digit_turns']) for k,v in diagnostics['systems'].items()])
failure_rows=[]
for k,v in diagnostics['systems'].items():
    grouped={}
    for flag,n in v['execution_flags'].items():
        label='工具调用预算耗尽' if 'tool_call_budget_exceeded' in flag else '回答token上限' if 'output_token_budget_exceeded' in flag else '8192-token上下文容量' if 'exceed_context_size_error' in flag else '工具调用格式错误' if any(x in flag for x in ['malformed','JSONDecodeError']) else '连接或运行错误（查看原记录）'
        grouped[label]=grouped.get(label,0)+n
    failure_rows.extend((k,label,n) for label,n in grouped.items())
failures=table(['系统','执行标记','题次'],failure_rows)
audio_rows=[(k,v['audio_output']['completed_turns_with_audio'],v['audio_output']['hit_frame_budget_turns'],v['audio_output']['cases_with_frame_budget_hit']) for k,v in diagnostics['systems'].items() if 'audio_output' in v]
audio_table=table(['系统','已有输出语音轮数','触及语音帧预算的轮数','涉及题数'],audio_rows)
turn_lookup={(r['system_id'],r['category'],r['planned_user_turns']):r for r in s.get('by_planned_user_turns',[])}
turn_rows=[]
for system in ['edge_native','qwen35_2b','qwen35_4b']:
    for turns in range(1,6):
        if (system,'all',turns) not in turn_lookup:continue
        overall=turn_lookup[(system,'all',turns)]
        turn_rows.append((system,turns,str(overall['decided_count'])+'/'+str(overall['planned']),*[pct(turn_lookup[(system,category,turns)]['strict_pass_rate']) for category in ['tool','chat','all']]))
turn_table=table(['系统','预设用户轮数','已判定/计划题数','工具通过率','聊天通过率','总体通过率'],turn_rows) if turn_rows else '更新汇总后生成。'
partition_table=table(['系统','分组','类别','通过/计划','严格通过率'],[(x['system_id'],'普通题' if x['partition']=='standard' else '长语音预算压力题',x['category'],str(x['passed_count'])+'/'+str(x['planned']),pct(x['strict_pass_rate'])) for x in s.get('by_reporting_partition',[])])
write('docs/RESULTS.md',f'''# 实际测评结果

生成时间：{s['generated_at']}；状态：**{s['evaluation_status']}**。每系统1000题：工具600、聊天400。判官证据协议：`{s.get('judge_evidence_version','未记录')}`；旧协议评分不混入当前统计。

{table(['系统','类别','已运行','已判定','实际听音评分题','严格通过题','最终通过率','有音频题均分/5'],rows)}

缺失音频的真实执行失败计入严格分母，维度NA；听音均分只描述实际有音频的题。不能将不完整覆盖率的均分当最终排名。

百分比显示保留一位小数，使用四舍五入；精确分子、分母和未舍入数值保存在表格及summary.json中。

{comparisons}

## 普通题与长语音预算压力题

{partition_table}

上表保留原始判官与规则口径。压力题另有实际WAV时长核验：Qwen 4B的C13_020被判通过，但全题回复合计185.84秒，未达到用户要求的七八分钟。不能将该次通过解释为满足时长要求；详见[逐题时长与判官分歧](STORY_DURATION_AUDIT.md)。不按单条结果手改判官分数。

## 按预设对话长度分组

{turn_table}

每档轮数各200题，其中工具120题、聊天80题。按冻结题目预设的正常用户轮数分组，提前失败仍留在原组，澄清轮次另外计入实际交互预算。该分组描述这些任务随对话长度的表现，不单独证明长度变化的因果效应。

## 数字与单位转写核查

{normalization}

统计以实际完成的助手轮次为单位，不是题数；原始数字识别模式为[0-9℃%]，不代表穷举全部单位。转写后无阿拉伯数字说明文本规则已生效，不等于每个数字都已正确发音；发音仍依据实际音频评分。原文、朗读文本和波形分别保留。

## 执行失败分布

{failures}

一题可能含多个执行标记，因此不能把此表简单相加当作失败题数。工具参数与状态不符、回答内容不符等语义失败另见逐题规则和听音证据。这里描述观察到的错误，不将其直接归因于模型参数量。

{audio_table}

语音帧预算依据实际生成终止标记判断，不能仅凭音频长短猜测。触及上限的回答仍保留音频并评分，但严格通过为false；这与回答文字的token上限是两个不同环节。

逐题摘要见reports/run_overview.json；完整调用、波形与判官原始证据见Release归档。口径见 [EVALUATION.md](EVALUATION.md)，限制见 [PROVENANCE.md](PROVENANCE.md)。
''')
print(json.dumps({'generated_markdown_files':7,'evaluation_status':s['evaluation_status']}))
