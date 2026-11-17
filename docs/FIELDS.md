# 完整字段字典

由版本化JSON Schema生成。[]代表数组元素；可选是允许缺键，null是存在但无值。参考答案与真实结果分离，参考不进入被测模型输入。输入音频缓存、作者记录、ASR、TTS与冻结清单的精确字段另见 [METADATA_FIELDS.md](METADATA_FIELDS.md)。

## 题目 data/cases/*.json

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| $ | object | 必需 | 完整基础用例；运行结果另存，避免把真实结果和参考答案混在一起。 |
| $.schema_version | string | 必需 | 数据结构版本。 enum=["0.2.0", "0.3.0"] |
| $.identity | object | 必需 | 题目标识。 |
| $.identity.case_id | string | 必需 | 全局唯一题目 ID。 |
| $.identity.case_version | string | 必需 | 题目内容版本；修改需升版。 |
| $.identity.title | string | 必需 | 题目名。 |
| $.identity.language | string | 必需 | 语言。 enum=["zh-CN"] |
| $.identity.status | string | 必需 | 题目生命周期。 enum=["draft", "reviewed", "frozen"] |
| $.classification | object | 必需 | 分类与划分，仅评测器使用。 |
| $.classification.category | string | 必需 | 一级分类。 enum=["tool", "chat"] |
| $.classification.subcategory | string | 必需 | 固定子类标识。 enum=["home_query", "device_control", "environment_query", "schedule_management", "media_management", "task_management", "daily_companionship", "emotional_support", "family_communication", "home_advice", "joint_planning", "learning", "story_roleplay", "games", "interest_discussion", "assistant_boundaries"] |
| $.classification.scene_id | string | 必需 | 所属场景卡 ID。 |
| $.classification.scene_title | string | 必需 | 场景名称。 |
| $.classification.difficulty | string | 必需 | 难度。 enum=["easy", "medium", "hard"] |
| $.classification.tags | array | 必需 | 可多选。 |
| $.classification.tags[] | string | 必需 | 能力标签。 |
| $.classification.split | string | 必需 | 数据划分。 enum=["development", "regression", "test"] |
| $.classification.group_id | string | 必需 | 同源题组；改写和模态变体必须同组同划分。 |
| $.provenance | reference | 必需 | 生成记录。 引用 /$defs/Generation |
| $.model_context | object | 必需 | 唯一可整体投影给模型的上下文区。 |
| $.model_context.system_prompt | string | 必需 | 对所有被测模型语义一致的家庭助手指令。 |
| $.model_context.actor | reference | 必需 | 可信用户上下文。 引用 /$defs/Actor |
| $.model_context.public_facts | array | 必需 | 允许可见的场景背景。 |
| $.model_context.public_facts[] | string | 必需 | 明确提供给模型的事实。 |
| $.model_context.tool_names | array | 必需 | 两类都提供同一工具集合。 |
| $.model_context.tool_names[] | string | 必需 | 启用工具名。 enum=["home_get", "device_list", "clock_get", "policy_get", "device_get", "device_set", "sensor_read", "schedule_list", "schedule_create", "schedule_update", "schedule_cancel", "media_search", "media_play", "media_control", "task_get", "task_cancel"] |
| $.model_context.history_policy | string | 必需 | 只回填待测模型自己的真实历史及真实工具响应。 enum=["actual_model_history"] |
| $.model_context.audio_transcript_visible | any | 必需 | 音频输入不附标准转录。 const=false |
| $.environment | reference | 必需 | 私有环境夹具。 引用 /$defs/Fixture |
| $.interaction | object | 必需 | 对话编排。 |
| $.interaction.start_node_id | string | 必需 | 起始节点。 |
| $.interaction.nodes | array | 必需 | 正常节点与备用分支节点，最多32个；限制的是每条实际交互路径最多5轮，不是整个节点库只能有5项。 |
| $.interaction.nodes[] | reference | 必需 | 对话节点。 引用 /$defs/Node |
| $.interaction.clarification | object | 必需 | 澄清协议。 |
| $.interaction.clarification.mode | string | 必需 | 先匹配预定义分支，无匹配时使用有次数上限的固定回退。 enum=["predefined_branches_with_bounded_fallback"] |
| $.interaction.clarification.fallback_text | string | 必需 | 未预设有效澄清分支时的用户回复，不补充隐藏事实。 |
| $.interaction.clarification.max_uses | integer | 必需 | 允许回退次数。 minimum=0 maximum=5 |
| $.interaction.clarification.counts_as_user_turn | boolean | 必需 | 必须计入五轮预算。 |
| $.interaction.clarification.resume | string | 必需 | 收到正常回答后继续当前节点的 next；回退期间不提前推进。 enum=["resume_current_node_then_next"] |
| $.interaction.clarification.router_profile | string | 必需 | 冻结的分支识别器版本，只看可见对话，不看答案。 |
| $.interaction.budget | reference | 必需 | 运行预算。 引用 /$defs/Budget |
| $.interaction.termination | string | 必需 | 最后节点回答完、预算耗尽或致命运行错误时结束。 |
| $.variants | array | 必需 | 变体不增加基础题数。 |
| $.variants[] | object | 必需 | 同一道题的不同输入方式。 |
| $.variants[].variant_id | string | 必需 | 输入变体 ID。 |
| $.variants[].modality | string | 必需 | 输入形式。 enum=["audio"] |
| $.variants[].status | string | 必需 | 可用状态。 enum=["ready", "planned", "failed"] |
| $.variants[].source_text_variant_id | null | 必需 | 无可运行文字变体。user_text仅为作者原稿与评分真值。 |
| $.variants[].audio_assets | array | 必需 | 音频变体按节点登记，含澄清回退。 |
| $.variants[].audio_assets[] | reference | 必需 | 音频登记。 引用 /$defs/AudioAsset |
| $.evaluation | object | 必需 | 隐藏评分标准。 |
| $.evaluation.rubric_version | string | 必需 | 评分规则版本。 |
| $.evaluation.checks | array | 必需 | 必要条件和诊断条件。 |
| $.evaluation.checks[] | reference | 必需 | 检查项。 引用 /$defs/Check |
| $.evaluation.dimensions | array | 必需 | 逐项评分。 |
| $.evaluation.dimensions[] | reference | 必需 | 维度。 引用 /$defs/Dimension |
| $.evaluation.pass_policy | object | 必需 | 整题通过规则。 |
| $.evaluation.pass_policy.required_checks_all_true | boolean | 必需 | 所有 required 检查必须满足。 |
| $.evaluation.pass_policy.require_no_critical_failure | boolean | 必需 | 严重错误直接不通过。 |
| $.evaluation.pass_policy.require_budget_respected | boolean | 必需 | 预算必须满足。 |
| $.evaluation.pass_policy.require_normal_completion | boolean | 必需 | 必须正常走完规定交互。 |
| $.evaluation.pass_policy.min_applicable_dimension_score | integer / null | 必需 | 聊天初始门槛为 3；工具主要按必要条件判定，为 null。 |
| $.evaluation.task_achieved_definition | string / null | 必需 | 工具任务实际达成的定义；聊天为 null。 |
| $.evaluation.critical_failure_definitions | array | 必需 | 提前定义；尝试与实际执行分开。 |
| $.evaluation.critical_failure_definitions[] | string | 必需 | 严重错误及范围。 |
| $.evaluation.judge_profile | string | 必需 | 语义评分器配置版本，实际模型版本写入运行记录。 |
| $.evaluation.behavior_policy | object | 可选 | 按实际到达轮次约束查询和写操作；禁止未来授权，含语义要求。 |
| $.evaluation.behavior_policy.version | string | 必需 |  |
| $.evaluation.behavior_policy.nodes | array | 必需 |  |
| $.evaluation.behavior_policy.nodes[] | object | 必需 |  |
| $.evaluation.behavior_policy.nodes[].node_id | string | 必需 |  |
| $.evaluation.behavior_policy.nodes[].allowed_read_tools | array | 必需 |  |
| $.evaluation.behavior_policy.nodes[].allowed_read_tools[] | string | 必需 |  |
| $.evaluation.behavior_policy.nodes[].allowed_writes | array | 必需 |  |
| $.evaluation.behavior_policy.nodes[].allowed_writes[] | object | 必需 |  |
| $.evaluation.behavior_policy.nodes[].must_satisfy | array | 必需 |  |
| $.evaluation.behavior_policy.nodes[].must_satisfy[] | string | 必需 |  |
| $.evaluation.behavior_policy.nodes[].must_not | array | 必需 |  |
| $.evaluation.behavior_policy.nodes[].must_not[] | string | 必需 |  |
| $.evaluation.reporting_partition | string | 可选 | 普通任务与超出现有短答预算的长语音要求分开统计，同时保留全量成绩。 enum=["standard", "budget_stress"] |
| $.evaluation.constraint_reference_version | string | 可选 | 可核验约束版本；开放式回答不匹配固定示例剧本。 |
| $.reference | object | 必需 | 隐藏参考过程。 |
| $.reference.record_kind | string | 必需 | 明确这是示范而非模型测试。 enum=["authored_reference_not_model_run"] |
| $.reference.unique_answer | any | 必需 | 参考答案不唯一。 const=false |
| $.reference.turns | array | 必需 | 完整正常路径。 |
| $.reference.turns[] | reference | 必需 | 参考回合。 引用 /$defs/ReferenceTurn |
| $.reference.acceptable_alternatives | array | 必需 | 不能把单一措辞/轨迹当成唯一答案。 |
| $.reference.acceptable_alternatives[] | string | 必需 | 允许的合理替代。 |
| $.reference.expected_case_pass | boolean | 必需 | 参考过程按设计应通过；不是实测成绩。 |
| $.quality | object | 必需 | 数据质量状态。 |
| $.quality.schema_validation | string | 必需 | 结构校验状态。 enum=["pending", "passed", "failed"] |
| $.quality.reference_rule_validation | string | 必需 | 参考轨迹的规则断言校验。 enum=["pending", "passed", "failed"] |
| $.quality.independent_review | string | 必需 | 独立模型或人员审题状态。 enum=["pending", "passed", "failed"] |
| $.quality.human_review | string | 必需 | 人工审核状态。 enum=["pending", "passed", "failed"] |
| $.quality.known_limitations | array | 必需 | 与此题有关的限制。 |
| $.quality.known_limitations[] | string | 必需 | 限制。 |


## 实际运行 runs/<system>/*.json

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| $ | object | 必需 | 真实运行记录；参考答案在 case 文件中独立保存 |
| $.record_kind | string | 必需 | 仅真实运行 const="actual_model_run" |
| $.schema_version | string | 必需 | 结构版本 enum=["0.2.0", "0.3.0"] |
| $.case_id | string | 必需 | 用例ID |
| $.case_sha256 | string | 必需 | 运行当时完整用例的规范JSON SHA256：sort_keys=True, ensure_ascii=False 默认分隔符 UTF-8 |
| $.system_id | string | 必需 | 系统ID enum=["qwen35_2b", "qwen35_4b", "edge_native"] |
| $.model_id | string | 必需 | 被测核心模型名称 |
| $.input_modality | string | 必需 | 统一语音输入 const="audio" |
| $.asr_model | string / null | 必需 | baseline识别模型；Edge为null |
| $.tts_model | string | 必需 | baseline语音合成模型或 native_talker |
| $.normalizer_version | string | 必需 | 共享转换版本 |
| $.generation | object | 必需 | 实际生成参数；见 evaluation_profiles.json 可扩展原始对象，见附录说明。 |
| $.execution | object | 必需 | 执行证据 |
| $.execution.status | string | 必需 | 失败包括真实预算/格式问题与基础设施异常，须结合 flags 判断 enum=["completed", "failed"] |
| $.execution.model_calls | integer | 必需 | 实际推理请求数 minimum=0 |
| $.execution.tool_calls | integer | 必需 | 实际工具调用数 minimum=0 |
| $.execution.wall_seconds | number | 必需 | 整题交互阶段耗时 |
| $.execution.flags | array | 必需 | 失败或截断标记，不以假分数替代 |
| $.execution.flags[] | string | 必需 | 标记或异常类型与说明 |
| $.execution.timing_scope | string | 必需 | 明确计时范围 |
| $.turns | array | 必需 | 已完成交互轮次；异常发生的未完成轮可能不在此数组中 |
| $.turns[] | object | 必需 | 实际发生的一轮用户交互，含工具循环 |
| $.turns[].user_turn_index | integer | 必需 | 从1开始，含澄清 minimum=1 maximum=5 |
| $.turns[].node_id | string | 必需 | 已投递预写节点，或 FALLBACK |
| $.turns[].input_variant_id | string | 必需 | A0：唯一语音输入变体 |
| $.turns[].input_audio | string | 必需 | 仓库相对路径；发布包解压后可访问 |
| $.turns[].input_audio_sha256 | string | 必需 | 实际投递波形的 SHA256 |
| $.turns[].delivered_text | null | 必需 | 没有把题目原文作为文字投递；baseline 的识别结果另记 asr_text |
| $.turns[].asr_text | string / null | 必需 | baseline 实际 ASR 识别文本；原生模型为 null |
| $.turns[].assistant_text | string | 必需 | 模型原始可朗读回答，不含结构化工具调用 |
| $.turns[].spoken_text | string | 必需 | 共享数字/单位规范化后的朗读文本 |
| $.turns[].normalizer_version | string | 必需 | 朗读转换版本 |
| $.turns[].assistant_audio | object / null | 必需 | 实际输出音频及溯源：path/sha256/duration_s/sample_rate_hz/model/normalizer_version/spoken_text；Edge 另含 raw_text、ended、hit_frame_budget、wall_seconds，baseline 另含 text、batch_offset、batch_seed、batch_keys、external_cloud_tts。原生音频缓存耗时不是当前调用的实时延迟。 |
| $.turns[].tool_events | array | 必需 | 本轮真实调用顺序 |
| $.turns[].tool_events[] | object | 必需 | 沙箱事件：request_id、call(tool_name/arguments)、response、state_before/state_after 及逻辑时间；状态类型见 types.schema.json。 可扩展原始对象，见附录说明。 |
| $.turns[].model_raw_responses | array | 必需 | 每次推理的完整原始响应；OpenAI兼容模型保留 choices/usage/timings，原生保留 raw_output/token计数/audio_evidence/finish_reason/worker耗时 |
| $.turns[].model_raw_responses[] | object | 必需 | 供应方或本地适配器原始响应，不作为判官听音的替代 可扩展原始对象，见附录说明。 |
| $.turns[].wall_seconds | number | 必需 | 该轮交互阶段耗时；baseline 不含离线ASR和TTS；不可横向当作端到端延迟 |
| $.turns[].finish_reason | string | 必需 | 最后一次生成结束原因 |
| $.turns[].routing_label | string | 必需 | 固定路由器决策 enum=["normal", "predefined_clarification", "bounded_fallback"] |
| $.turns[].selected_branch_id | string / null | 必需 | 命中预定义澄清分支ID |
| $.rule_checks | array | 必需 | 客观状态检查 |
| $.rule_checks[] | object | 必需 | 单项判定 |
| $.rule_checks[].check_id | string | 必需 | 对应 evaluation.checks.id |
| $.rule_checks[].passed | boolean | 必需 | 客观规则通过与否 |
| $.rule_checks[].observed | any | 必需 | 实际观察、差异状态或违规列表 |
| $.rule_checks[].evaluator | string | 必需 | 规则引擎版本 |
| $.tool_trace | array | 必需 | 整题完整沙箱日志，包含未完成轮内已发生的调用 |
| $.tool_trace[] | object | 必需 | 沙箱事件：request_id、call(tool_name/arguments)、response、state_before/state_after 及逻辑时间；状态类型见 types.schema.json。 可扩展原始对象，见附录说明。 |
| $.incomplete_turn | object / null | 必需 | 预算、格式或服务错误发生时保存的未完成轮：node_id/input_audio/input_audio_sha256/asr_text/assistant_parts_not_spoken/model_raw_responses/first_tool_event_index。未朗读文字不可作为实际音频评分。 |
| $.final_state | object | 必需 | 真实终态，见 types.schema.json 家庭状态定义 可扩展原始对象，见附录说明。 |
| $.audio_judge | object / null | 必需 | 实际听音评分记录：model/requested_model/temperature/enable_thinking/request_id/usage/prompt_sha256/audio_sha256/model_answer_text_supplied/result。result 含 dimensions、semantic_checks、critical_failures、heard_turns、task_achieved；分数是0–5整数。 |
| $.case_pass | boolean / null | 必需 | 严格整题通过；未完成评判为null，执行失败可为false且维度分数仍未知 |
| $.task_achieved | boolean / null | 必需 | 判官判断用户主要目标是否达到；与严格通过率分开 |
| $.judge_status | string | 可选 | scored，或没有可评分回答时的明确原因 |
| $.revision | object | 可选 | 本次执行/复用来源、各协议哈希、版本和规则变更证据。 |


## 共享类型 Error

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Error | object | 必需 | 工具错误。 |
| Error.code | string | 必需 | 固定错误码。 |
| Error.message | string | 必需 | 模型可见的错误解释，不含隐藏答案。 |
| Error.retryable | boolean | 必需 | 当前错误是否允许按预算重试。 |


## 共享类型 Actor

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Actor | object | 必需 | 当前发言者。 |
| Actor.id | string | 必需 | 评测器提供的可信用户标识，模型不能自行修改。 |
| Actor.name | string | 必需 | 场景使用的虚构称呼。 |
| Actor.role | string | 必需 | 可信权限角色。 |


## 共享类型 Room

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Room | object | 必需 | 房间。 |
| Room.id | string | 必需 | 稳定房间标识。 |
| Room.name | string | 必需 | 模型可见房间名。 |


## 共享类型 DeviceState

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| DeviceState | object | 必需 | 完整设备状态；不支持的字段为 null，列表为 []。 |
| DeviceState.power | boolean / null | 必需 | 开关；不支持此项时为 null。 |
| DeviceState.brightness_pct | number / null | 必需 | 亮度百分比。 |
| DeviceState.color_temperature_k | number / null | 必需 | 色温，单位 K。 |
| DeviceState.target_temperature_c | number / null | 必需 | 目标温度，单位摄氏度。 |
| DeviceState.mode | string / null | 必需 | 设备模式；实际允许值由 capabilities 决定。 |
| DeviceState.fan_speed | integer / null | 必需 | 风速档位，实际范围由设备能力决定。 |
| DeviceState.opening_pct | number / null | 必需 | 窗帘打开百分比。 |
| DeviceState.volume_pct | number / null | 必需 | 音量百分比。 |
| DeviceState.cleaning_status | string / null | 必需 | 扫地机状态。 |
| DeviceState.target_room_ids | array | 必需 | 当前清扫目标；非扫地机为 []。 |
| DeviceState.target_room_ids[] | string | 必需 | 房间 ID。 |


## 共享类型 DeviceChanges

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| DeviceChanges | object | 必需 | 仅允许这些修改字段；还必须符合目标设备的 capabilities。 |
| DeviceChanges.power | boolean | 可选 | 开关；不支持此项时为 null。 |
| DeviceChanges.brightness_pct | number | 可选 | 亮度百分比。 minimum=0 maximum=100 |
| DeviceChanges.color_temperature_k | number | 可选 | 色温，单位 K。 minimum=1000 maximum=10000 |
| DeviceChanges.target_temperature_c | number | 可选 | 目标温度，单位摄氏度。 minimum=-10 maximum=60 |
| DeviceChanges.mode | string | 可选 | 设备模式；实际允许值由 capabilities 决定。 |
| DeviceChanges.fan_speed | integer | 可选 | 风速档位，实际范围由设备能力决定。 minimum=0 maximum=10 |
| DeviceChanges.opening_pct | number | 可选 | 窗帘打开百分比。 minimum=0 maximum=100 |
| DeviceChanges.volume_pct | number | 可选 | 音量百分比。 minimum=0 maximum=100 |
| DeviceChanges.target_room_ids | array | 可选 | 当前清扫目标；非扫地机为 []。 |
| DeviceChanges.target_room_ids[] | string | 必需 | 房间 ID。 |
| DeviceChanges.cleaning_action | string | 可选 | 扫地机操作，不直接写 cleaning_status。 enum=["start", "pause", "resume", "return_home"] |


## 共享类型 Capability

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Capability | object | 必需 | 设备能力和参数限制。 |
| Capability.field | string | 必需 | 可修改字段。 |
| Capability.allowed_values | array / null | 必需 | 枚举范围；非枚举为 null。 |
| Capability.allowed_values<分支0> | array | 必需 | 枚举范围；非枚举为 null。 |
| Capability.allowed_values<分支0>[] | any | 必需 | 一个允许值。 |
| Capability.minimum | number / null | 必需 | 最小值。 |
| Capability.maximum | number / null | 必需 | 最大值。 |
| Capability.unit | string / null | 必需 | 单位；无单位为 null。 |


## 共享类型 Device

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Device | object | 必需 | 设备记录。 |
| Device.id | string | 必需 | 设备 ID。 |
| Device.name | string | 必需 | 设备名称。 |
| Device.type | string | 必需 | 设备类型。 enum=["light", "air_conditioner", "curtain", "fan", "purifier", "tv", "speaker", "vacuum"] |
| Device.room_id | string | 必需 | 所属房间。 |
| Device.online | boolean | 必需 | 是否在线。 |
| Device.state | reference | 必需 | 当前状态。 引用 /$defs/DeviceState |
| Device.capabilities | array | 必需 | 能力清单。 |
| Device.capabilities[] | reference | 必需 | 允许修改的能力。 引用 /$defs/Capability |


## 共享类型 DeviceInfo

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| DeviceInfo | object | 必需 | 目录返回的设备信息，不包含实时状态。 |
| DeviceInfo.id | string | 必需 | 设备 ID。 |
| DeviceInfo.name | string | 必需 | 设备名称。 |
| DeviceInfo.type | string | 必需 | 设备类型。 enum=["light", "air_conditioner", "curtain", "fan", "purifier", "tv", "speaker", "vacuum"] |
| DeviceInfo.room_id | string | 必需 | 所属房间。 |
| DeviceInfo.capabilities | array | 必需 | 能力清单。 |
| DeviceInfo.capabilities[] | reference | 必需 | 允许修改的能力。 引用 /$defs/Capability |


## 共享类型 Sensor

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Sensor | object | 必需 | 环境观测。 |
| Sensor.id | string | 必需 | 传感器 ID。 |
| Sensor.room_id | string | 必需 | 所在房间。 |
| Sensor.metric | string | 必需 | 测量类型。 enum=["temperature_c", "humidity_pct", "illuminance_lux", "co2_ppm", "presence"] |
| Sensor.value | any | 必需 | 数值；presence 使用布尔值。 |
| Sensor.unit | string | 必需 | 单位；presence 为 boolean。 |
| Sensor.observed_at | string | 必需 | 实际观测时间。 format="date-time" |
| Sensor.online | boolean | 必需 | 是否可读。 |


## 共享类型 When

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| When | object | 必需 | 安排触发时间。 |
| When.mode | string | 必需 | 触发方式。 enum=["once", "daily", "weekly"] |
| When.at | string / null | 必需 | once 使用的绝对时间，包含时区偏移。 |
| When.local_time | string / null | 必需 | daily/weekly 使用的 HH:MM:SS。 |
| When.weekdays | array | 必需 | weekly 使用；其余为 []。 |
| When.weekdays[] | integer | 必需 | 星期一=1，星期日=7。 minimum=1 maximum=7 |
| When.timezone | string | 必需 | IANA 时区，例如 Asia/Taipei。 |


## 共享类型 DeviceAction

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| DeviceAction | object | 必需 | 定时设备动作；不允许嵌套工具或执行任意代码。 |
| DeviceAction.device_id | string | 必需 | 目标设备 ID。 |
| DeviceAction.changes | reference | 必需 | 计划执行的修改。 引用 /$defs/DeviceChanges |


## 共享类型 Payload

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Payload | object | 必需 | 安排内容。 |
| Payload.message | string / null | 必需 | 提醒或闹钟内容；设备动作时为 null。 |
| Payload.target_device_id | string / null | 必需 | 闹钟播放设备；提醒使用场景通知通道。 |
| Payload.actions | array | 必需 | device_action 使用；其他类型为 []。 |
| Payload.actions[] | reference | 必需 | 设备动作。 引用 /$defs/DeviceAction |


## 共享类型 Schedule

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Schedule | object | 必需 | 未来安排。 |
| Schedule.id | string | 必需 | 沙箱生成的安排 ID。 |
| Schedule.owner_id | string | 必需 | 归属用户，由可信上下文注入。 |
| Schedule.kind | string | 必需 | 安排类型。 enum=["reminder", "alarm", "device_action"] |
| Schedule.when | reference | 必需 | 触发时间。 引用 /$defs/When |
| Schedule.payload | reference | 必需 | 内容。 引用 /$defs/Payload |
| Schedule.status | string | 必需 | 安排状态：一次性安排触发后为completed；不代表其设备动作一定成功，实际结果另看任务记录。 enum=["active", "cancelled", "completed"] |
| Schedule.created_at | string | 必需 | 创建时间。 format="date-time" |
| Schedule.updated_at | string | 必需 | 最近修改时间。 format="date-time" |
| Schedule.last_triggered_at | string / null | 必需 | 最近实际触发时间；未触发为 null。 |


## 共享类型 Media

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Media | object | 必需 | 媒体库条目。 |
| Media.id | string | 必需 | 媒体 ID。 |
| Media.title | string | 必需 | 媒体标题。 |
| Media.type | string | 必需 | 媒体类型。 enum=["music", "story", "podcast"] |
| Media.duration_s | number | 必需 | 长度，秒。 minimum=0 |
| Media.source | string | 必需 | 此版为固定本地媒体库。 enum=["fixture"] |
| Media.asset_id | string / null | 必需 | 实际文件的素材 ID；仅目录模拟时为 null。 |


## 共享类型 Playback

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Playback | object | 必需 | 播放会话。 |
| Playback.id | string | 必需 | 播放会话 ID。 |
| Playback.owner_id | string | 必需 | 所属用户。 |
| Playback.device_id | string | 必需 | 播放设备。 |
| Playback.content_id | string | 必需 | 媒体 ID。 |
| Playback.status | string | 必需 | 状态。 enum=["playing", "paused", "stopped", "ended"] |
| Playback.position_s | number | 必需 | 播放进度，秒。 minimum=0 |
| Playback.updated_at | string | 必需 | 更新时间。 format="date-time" |


## 共享类型 Task

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Task | object | 必需 | 异步任务；取消已提交任务不会回滚。 |
| Task.id | string | 必需 | 异步执行任务 ID。 |
| Task.owner_id | string | 必需 | 所属用户。 |
| Task.operation | string | 必需 | 原始工具名。 |
| Task.target_id | string | 必需 | 操作对象。 |
| Task.status | string | 必需 | 执行状态。 enum=["pending", "running", "committed", "cancelled", "failed"] |
| Task.progress_pct | number | 必需 | 进度百分比。 minimum=0 maximum=100 |
| Task.cancellable | boolean | 必需 | 当前阶段是否可取消。 |
| Task.created_at | string | 必需 | 创建时间。 format="date-time" |
| Task.updated_at | string | 必需 | 更新时间。 format="date-time" |
| Task.result | conditional / null | 必需 | 任务结果；结构遵循对应工具的成功数据。 |
| Task.error | https://homebench.example/spec/0.2/types.schema.json#/$defs/Error / null | 必需 | 失败原因。 |


## 共享类型 Preference

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Preference | object | 必需 | 允许向当前用户提供的偏好。 |
| Preference.key | string | 必需 | 公开偏好名称。 |
| Preference.value | string | 必需 | 偏好内容。 |


## 共享类型 HomeInfo

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| HomeInfo | object | 必需 | home_get 的返回数据。 |
| HomeInfo.home_id | string | 必需 | 家庭 ID。 |
| HomeInfo.name | string | 必需 | 虚构家庭名称。 |
| HomeInfo.rooms | array | 必需 | 可见房间。 |
| HomeInfo.rooms[] | reference | 必需 | 房间。 引用 /$defs/Room |
| HomeInfo.public_preferences | array | 必需 | 当前用户可见的偏好。 |
| HomeInfo.public_preferences[] | reference | 必需 | 公开偏好。 引用 /$defs/Preference |


## 共享类型 Permission

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Permission | object | 必需 | 权限规则；拒绝优先，未匹配默认拒绝。 |
| Permission.id | string | 必需 | 规则 ID。 |
| Permission.actor_role | string | 必需 | 适用角色。 |
| Permission.resource_type | string | 必需 | 资源类型。 enum=["home", "device", "sensor", "schedule", "media", "playback", "task"] |
| Permission.resource_ids | array | 必需 | 匹配对象。 |
| Permission.resource_ids[] | string | 必需 | 资源 ID 或 *。 |
| Permission.actions | array | 必需 | 允许/禁止的动作。 |
| Permission.actions[] | string | 必需 | 工具名或 *。 |
| Permission.decision | string | 必需 | 权限结论。 enum=["allow", "deny"] |
| Permission.owner_only | boolean | 必需 | true 时还要求资源属于当前用户。 |


## 共享类型 Fault

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Fault | object | 必需 | 确定性故障夹具；网络重放不增加匹配请求序号。 |
| Fault.id | string | 必需 | 故障 ID。 |
| Fault.tool_name | string | 必需 | 匹配的工具。 |
| Fault.resource_id | string / null | 必需 | 匹配对象；null 为该工具所有对象。 |
| Fault.on_attempts | array | 必需 | 在哪些请求触发。 |
| Fault.on_attempts[] | integer | 必需 | 从 1 开始的匹配请求序号。 minimum=1 |
| Fault.kind | string | 必需 | 故障类型。 enum=["offline", "transient_failure", "delay", "timeout"] |
| Fault.delay_ms | integer | 必需 | delay 使用的逻辑延迟；其他类型为 0。 minimum=0 |


## 共享类型 Event

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Event | object | 必需 | 独立于模型的环境变化。 |
| Event.id | string | 必需 | 外部事件 ID。 |
| Event.at | string | 必需 | 触发时间。 format="date-time" |
| Event.type | string | 必需 | 事件种类。 enum=["device_change", "sensor_change"] |
| Event.target_id | string | 必需 | 设备或传感器 ID。 |
| Event.changes | https://homebench.example/spec/0.2/types.schema.json#/$defs/DeviceChanges / null | 必需 | device_change 时的修改。 |
| Event.sensor_value | conditional / null | 必需 | sensor_change 时的读数。 |


## 共享类型 Clock

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Clock | object | 必需 | 可复现的逻辑时钟；不等于产品实际耗时。 |
| Clock.start_at | string | 必需 | 场景开始时间。 format="date-time" |
| Clock.current_at | string | 必需 | 当前逻辑时间；初态等于 start_at。 format="date-time" |
| Clock.timezone | string | 必需 | IANA 时区。 |
| Clock.advance_after_user_turn_ms | integer | 必需 | 一个用户回合结束后推进的逻辑毫秒。 minimum=0 |
| Clock.advance_after_tool_call_ms | integer | 必需 | 每次工具调用结束后的逻辑毫秒。 minimum=0 |


## 共享类型 State

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| State | object | 必需 | 完整初始状态，仅评测器可见；不能整包发送给模型。 |
| State.clock | reference | 必需 | 时钟。 引用 /$defs/Clock |
| State.home | reference | 必需 | 家庭公开资料。 引用 /$defs/HomeInfo |
| State.devices | array | 必需 | 全部设备夹具。 |
| State.devices[] | reference | 必需 | 设备。 引用 /$defs/Device |
| State.sensors | array | 必需 | 传感器夹具。 |
| State.sensors[] | reference | 必需 | 传感器。 引用 /$defs/Sensor |
| State.schedules | array | 必需 | 初始安排。 |
| State.schedules[] | reference | 必需 | 安排。 引用 /$defs/Schedule |
| State.media_catalog | array | 必需 | 固定媒体库。 |
| State.media_catalog[] | reference | 必需 | 媒体。 引用 /$defs/Media |
| State.playbacks | array | 必需 | 播放状态。 |
| State.playbacks[] | reference | 必需 | 播放会话。 引用 /$defs/Playback |
| State.tasks | array | 必需 | 任务状态。 |
| State.tasks[] | reference | 必需 | 异步任务。 引用 /$defs/Task |


## 共享类型 Fixture

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Fixture | object | 必需 | 私有家庭环境。 |
| Fixture.initial_state | reference | 必需 | 初始状态。 引用 /$defs/State |
| Fixture.permissions | array | 必需 | 可信权限表。 |
| Fixture.permissions[] | reference | 必需 | 权限规则。 引用 /$defs/Permission |
| Fixture.faults | array | 必需 | 本题故障设置；无故障为 []。 |
| Fixture.faults[] | reference | 必需 | 故障。 引用 /$defs/Fault |
| Fixture.external_events | array | 必需 | 外部事件；无事件为 []。 |
| Fixture.external_events[] | reference | 必需 | 环境事件。 引用 /$defs/Event |
| Fixture.id_prefix | string | 必需 | 沙箱新对象 ID 的稳定前缀。 |


## 共享类型 ToolCall

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| ToolCall | object | 必需 | 规范化工具调用；原始模型输出另存运行记录。 |
| ToolCall.tool_name | string | 必需 | 工具名。 |
| ToolCall.arguments | any | 必需 | 严格按该工具 input_schema 校验的参数。 |


## 共享类型 Usage

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Usage | object | 必需 | 实际用量；未执行不能写 0。 |
| Usage.input_tokens | integer / null | 必需 | 实际输入 token；未知为 null。 |
| Usage.output_tokens | integer / null | 必需 | 实际输出 token。 |
| Usage.cached_input_tokens | integer / null | 必需 | 实际缓存输入 token。 |
| Usage.audio_input_seconds | number / null | 必需 | 实际音频输入时长。 |
| Usage.audio_output_seconds | number / null | 必需 | 实际音频输出时长。 |


## 共享类型 Cost

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Cost | object | 必需 | 费用；估算与实扣分开。 |
| Cost.currency | string / null | 必需 | 币种。 |
| Cost.amount | number / null | 必需 | 实际账单或估算金额。 |
| Cost.basis | string | 必需 | 费用依据。 enum=["not_measured", "usage_estimate", "provider_invoice"] |
| Cost.price_source | string / null | 必需 | 估算单价来源。 |
| Cost.price_date | string / null | 必需 | 单价日期。 |


## 共享类型 AudioAsset

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| AudioAsset | object | 必需 | 音频素材登记。 |
| AudioAsset.asset_id | string | 必需 | 素材 ID。 |
| AudioAsset.node_id | string | 必需 | 对应对话节点或 fallback。 |
| AudioAsset.status | string | 必需 | 素材状态。 enum=["planned", "generated", "verified", "rejected"] |
| AudioAsset.path | string / null | 必需 | 相对数据包的文件路径。 |
| AudioAsset.sha256 | string / null | 必需 | 文件 SHA256。 |
| AudioAsset.duration_s | number / null | 必需 | 实际时长。 |
| AudioAsset.sample_rate_hz | integer / null | 必需 | 实际采样率。 |
| AudioAsset.channels | integer / null | 必需 | 声道数。 |
| AudioAsset.codec | string / null | 必需 | 实际编码。 |
| AudioAsset.tts_model | string / null | 必需 | 合成模型及版本。 |
| AudioAsset.voice_id | string / null | 必需 | 音色标识，仅复现使用。 |
| AudioAsset.seed | integer / null | 必需 | 合成种子。 |
| AudioAsset.tone | string | 必需 | 设计语气；不作为待测模型文字提示。 |
| AudioAsset.noise_condition | string | 必需 | 声学条件描述。 |
| AudioAsset.transcript_gt | string | 必需 | 原台词，音频通道仅供评测器使用。 |
| AudioAsset.qc_status | string | 必需 | 音频质检状态。 enum=["not_run", "machine_pass", "human_pass", "failed"] |
| AudioAsset.qc_asr_text | string / null | 必需 | 独立 ASR 质检结果。 |
| AudioAsset.processing | array | 必需 | 处理记录；无处理为 []。 |
| AudioAsset.processing[] | string | 必需 | 每项实际处理及参数。 |


## 共享类型 Generation

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Generation | object | 必需 | 生成溯源；不含凭据。 |
| Generation.source | string | 必需 | 来源类型。 enum=["authored_example", "api_generated", "human_authored"] |
| Generation.provider | string / null | 必需 | 生成服务商。 |
| Generation.model | string / null | 必需 | 生成模型及版本。 |
| Generation.prompt_id | string / null | 必需 | 生成提示词版本/哈希。 |
| Generation.request_id | string / null | 必需 | 生成请求 ID。 |
| Generation.seed | integer | 必需 | 数据构造种子。 minimum=0 |
| Generation.created_date | string | 必需 | 本条规范数据的创建日期。 |
| Generation.source_refs | array | 必需 | 依据；原创例子可为空。 |
| Generation.source_refs[] | string | 必需 | 资料来源 URL 或内部授权资料标识。 |
| Generation.usage | reference | 必需 | 生成用量。 引用 /$defs/Usage |
| Generation.cost | reference | 必需 | 生成成本。 引用 /$defs/Cost |


## 共享类型 Budget

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Budget | object | 必需 | 预算；正式运行不静默截断历史。 |
| Budget.max_user_turns | integer | 必需 | 用户轮数上限，澄清也计入。 minimum=1 maximum=5 |
| Budget.max_model_calls | integer | 必需 | 模型生成请求上限。 minimum=1 |
| Budget.max_tool_calls | integer | 必需 | 整题工具调用上限。 minimum=0 |
| Budget.max_consecutive_tool_calls | integer | 必需 | 单个用户回合内工具调用上限。 minimum=0 |
| Budget.max_output_tokens_per_call | integer | 必需 | 每次模型生成的输出上限。 minimum=1 |
| Budget.context_window_tokens | integer | 必需 | 可用上下文总长度。 minimum=1 |
| Budget.wall_timeout_s | number | 必需 | 整题实际执行超时，不是虚拟等待时间。 minimum=1 |


## 共享类型 Node

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Node | object | 必需 | 单个用户节点；每次只投递该节点原话或对应音频。 |
| Node.id | string | 必需 | 节点 ID。 |
| Node.user_text | string | 必需 | 本节点的用户原话。 |
| Node.tone | string | 必需 | 设计语气，用于合成和评测，不注入文字模型提示。 |
| Node.next_node_id | string / null | 必需 | 正常回答后进入的下一节点；结束为 null。 |
| Node.clarification_branches | array | 必需 | 没有相应预定义分支时才使用统一回退。 |
| Node.clarification_branches[] | object | 必需 | 预定义澄清分支。 |
| Node.clarification_branches[].id | string | 必需 | 本节点内唯一分支 ID。 |
| Node.clarification_branches[].match | string | 必需 | 对应助手所询问的信息；只用于冻结路由器。 |
| Node.clarification_branches[].next_node_id | string | 必需 | 发送哪个已写好的用户节点。 |
| Node.expected_user_turn_index | integer | 必需 | 正常路径中第几轮。 minimum=1 maximum=5 |


## 共享类型 Filter

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Filter | object | 必需 | 断言的集合筛选条件。 |
| Filter.field | string | 必需 | 集合元素内部的 JSON Pointer。 |
| Filter.op | string | 必需 | 匹配方式；time_eq 按带时区的同一时刻比较，不逐字比较日期。 enum=["eq", "time_eq", "in", "contains"] |
| Filter.value | any | 必需 | 比较值。 |


## 共享类型 Check

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Check | object | 必需 | 每题预先声明的评分条件；不能依据模型表现事后修改。 |
| Check.id | string | 必需 | 检查项 ID。 |
| Check.description | string | 必需 | 人类可读的判定条件。 |
| Check.required | boolean | 必需 | 是否为用例通过的必要条件。 |
| Check.severity | string | 必需 | 失败级别。 enum=["ordinary", "critical"] |
| Check.scope | string | 必需 | 检查时机。 enum=["after_node", "trajectory", "final"] |
| Check.node_id | string / null | 必需 | after_node 对应节点。 |
| Check.method | string | 必需 | 规则或语义检查。 enum=["rule", "semantic_judge"] |
| Check.operator | string | 必需 | 检查算子。 enum=["count_equals", "value_equals", "unchanged", "tool_count_equals", "semantic", "state_matches", "no_unrequested_mutation", "read_evidence", "no_unauthorized_write", "read_policy_respected"] |
| Check.path | string / null | 必需 | 状态 JSON Pointer；语义检查可为 null。 |
| Check.filters | array | 必需 | 集合筛选条件，按 AND 连接。 |
| Check.filters[] | reference | 必需 | 筛选。 引用 /$defs/Filter |
| Check.expected | any | 必需 | 期望值；semantic 使用 true。 |
| Check.evidence_sources | array | 必需 | 例如 state、tool_trace、assistant_text。 |
| Check.evidence_sources[] | string | 必需 | 证据来源。 |


## 共享类型 Dimension

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Dimension | object | 必需 | 分项评分标准。 |
| Dimension.id | string | 必需 | 维度 ID。 |
| Dimension.name | string | 必需 | 中文维度名。 |
| Dimension.applicable | boolean | 必需 | 是否适用；不适用时运行分数为 null。 |
| Dimension.criterion | string | 必需 | 本题在该维度具体看什么。 |
| Dimension.anchors | object | 必需 | 逐项 0–5 分锚点。 |
| Dimension.anchors.0 | string | 必需 | 该分数对应的表现。 |
| Dimension.anchors.1 | string | 必需 | 该分数对应的表现。 |
| Dimension.anchors.2 | string | 必需 | 该分数对应的表现。 |
| Dimension.anchors.3 | string | 必需 | 该分数对应的表现。 |
| Dimension.anchors.4 | string | 必需 | 该分数对应的表现。 |
| Dimension.anchors.5 | string | 必需 | 该分数对应的表现。 |


## 共享类型 ReferenceCall

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| ReferenceCall | object | 必需 | 参考工具调用，不是模型实测。 |
| ReferenceCall.call | reference | 必需 | 理想轨迹中的调用。 引用 /$defs/ToolCall |
| ReferenceCall.expected_response | any | 必需 | 符合该工具 output_schema 的示范响应。 |


## 共享类型 ReferenceTurn

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| ReferenceTurn | object | 必需 | 参考回合。 |
| ReferenceTurn.node_id | string | 必需 | 对应用户节点。 |
| ReferenceTurn.calls | array | 必需 | 本轮理想工具调用，可为空。 |
| ReferenceTurn.calls[] | reference | 必需 | 示范调用。 引用 /$defs/ReferenceCall |
| ReferenceTurn.assistant_text | string | 必需 | 一种可接受的示范回复，不要求逐字一致。 |


## 共享类型 GenerationConfig

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| GenerationConfig | object | 必需 | 实际生效参数；不支持的参数也需记录为 null。 |
| GenerationConfig.temperature | number / null | 必需 | 实际温度。 |
| GenerationConfig.do_sample | boolean / null | 必需 | 是否采样。 |
| GenerationConfig.top_p | number / null | 必需 | 实际 top_p。 |
| GenerationConfig.top_k | integer / null | 必需 | 实际 top_k。 |
| GenerationConfig.min_p | number / null | 必需 | 实际 min_p。 |
| GenerationConfig.presence_penalty | number / null | 必需 | 实际 presence penalty。 |
| GenerationConfig.seed | integer / null | 必需 | 实际生成种子。 |
| GenerationConfig.max_output_tokens | integer / null | 必需 | 实际每次输出上限。 |
| GenerationConfig.context_window_tokens | integer / null | 必需 | 实际上下文长度。 |
| GenerationConfig.enable_thinking | boolean / null | 必需 | 实际是否启用thinking；Qwen复现组关闭。 |


## 共享类型 Profile

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| Profile | object | 必需 | 一次模型实验的真实配置。 |
| Profile.profile_id | string / null | 必需 | 冻结实验配置 ID。 |
| Profile.model_name | string / null | 必需 | 实际模型名。 |
| Profile.provider | string / null | 必需 | 本地或服务商。 |
| Profile.revision | string / null | 必需 | 权重/服务版本。 |
| Profile.weights_sha256 | string / null | 必需 | 本地权重哈希；服务未提供时为 null。 |
| Profile.runtime_version | string / null | 必需 | 推理框架版本。 |
| Profile.quantization | string / null | 必需 | 量化类型。 |
| Profile.adapter_version | string / null | 必需 | 接口适配器版本。 |
| Profile.system_prompt_sha256 | string / null | 必需 | 实际 system prompt 哈希。 |
| Profile.tool_spec_sha256 | string / null | 必需 | 工具声明哈希。 |
| Profile.generation | reference | 必需 | 实际参数。 引用 /$defs/GenerationConfig |
| Profile.output_mode | string / null | 必需 | 文字或语音输出。 |
| Profile.asr_model | string / null | 必需 | ASR 型号和版本；原生音频为 null。 |
| Profile.tts_model | string / null | 必需 | TTS 型号和版本；原生输出为 null。 |
| Profile.native_audio | boolean / null | 必需 | 是否原生音频输入。 |
| Profile.hardware | string / null | 必需 | 硬件和必要运行条件。 |
| Profile.chat_template_sha256 | string / null | 必需 | 实际模型聊天模板哈希。 |
| Profile.effective_config | conditional / null | 必需 | 实际生效请求及服务配置的原始快照，移除凭据；供应商私有字段不由本数据格式定义。 |


## 共享类型 RunToolEvent

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| RunToolEvent | object | 必需 | 真实工具事件。 |
| RunToolEvent.event_id | string | 必需 | 调用事件 ID。 |
| RunToolEvent.model_call_index | integer | 必需 | 第几次模型生成提出的调用。 minimum=1 |
| RunToolEvent.call | reference | 必需 | 实际规范化调用。 引用 /$defs/ToolCall |
| RunToolEvent.request_id | string | 必需 | 传输请求 ID。 |
| RunToolEvent.response | any | 必需 | 实际工具响应，按该工具输出 schema 校验。 |
| RunToolEvent.state_before | reference | 必需 | 私有调用前快照。 引用 /$defs/State |
| RunToolEvent.state_after | reference | 必需 | 私有调用后快照。 引用 /$defs/State |
| RunToolEvent.start_monotonic_ms | number | 必需 | 主机单调时钟起点。 minimum=0 |
| RunToolEvent.end_monotonic_ms | number | 必需 | 主机单调时钟终点。 minimum=0 |
| RunToolEvent.transport_retry_count | integer | 必需 | 传输层重试次数。 minimum=0 |
| RunToolEvent.raw_call | any | 必需 | 未修正的模型原始工具调用。 |


## 共享类型 RunTurn

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| RunTurn | object | 必需 | 真实对话回合。 |
| RunTurn.user_turn_index | integer | 必需 | 实际第几轮，含回退。 minimum=1 maximum=5 |
| RunTurn.node_id | string | 必需 | 对应节点或 FALLBACK。 |
| RunTurn.input_variant_id | string | 必需 | 实际输入变体。 |
| RunTurn.delivered_text | string / null | 必需 | 实际送入模型的文字；原生音频为 null。 |
| RunTurn.delivered_audio_asset_id | string / null | 必需 | 实际音频素材 ID。 |
| RunTurn.asr_text | string / null | 必需 | 级联链路实际 ASR 转写；不是标准答案。 |
| RunTurn.assistant_text | string / null | 必需 | 真实助手文本输出。 |
| RunTurn.assistant_audio_path | string / null | 必需 | 真实助手音频路径。 |
| RunTurn.tool_events | array | 必需 | 本轮工具轨迹。 |
| RunTurn.tool_events[] | reference | 必需 | 工具事件。 引用 /$defs/RunToolEvent |
| RunTurn.model_raw_responses | array | 必需 | 保留未修复原始返回。 |
| RunTurn.model_raw_responses[] | any | 必需 | 供应商原始响应，去除凭据。 |
| RunTurn.routing_label | string / null | 必需 | 分支识别结果。 |
| RunTurn.selected_branch_id | string / null | 必需 | 命中的预定义分支 ID；正常继续或回退为 null。 |
| RunTurn.routing_evidence | string / null | 必需 | 分支选择依据，仅基于可见对话。 |
| RunTurn.usage | reference | 必需 | 实际用量。 引用 /$defs/Usage |
| RunTurn.wall_latency_ms | number / null | 必需 | 本轮实测墙钟耗时。 |
| RunTurn.finish_reason | string / null | 必需 | 正常结束、长度截断、接口失败等原始原因。 |


## 共享类型 CheckResult

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| CheckResult | object | 必需 | 逐条件判分。 |
| CheckResult.check_id | string | 必需 | 对应评分条件。 |
| CheckResult.passed | boolean / null | 必需 | 条件是否通过；未判定为 null。 |
| CheckResult.observed | any | 必需 | 实际观测值。 |
| CheckResult.evidence | array | 必需 | 证据。 |
| CheckResult.evidence[] | string | 必需 | 原话、事件 ID、状态路径等证据。 |
| CheckResult.evaluator | string | 必需 | 执行的规则版本或判官配置 ID。 |


## 共享类型 ScoreResult

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| ScoreResult | object | 必需 | 分项成绩。 |
| ScoreResult.dimension_id | string | 必需 | 维度 ID。 |
| ScoreResult.applicable | boolean | 必需 | 是否适用。 |
| ScoreResult.score | integer / null | 必需 | 0–5 整数；不适用或未评分为 null。 |
| ScoreResult.reason | string / null | 必需 | 扣分/得分依据。 |
| ScoreResult.evidence | array | 必需 | 依据列表。 |
| ScoreResult.evidence[] | string | 必需 | 证据。 |


## 共享类型 FailureFlag

| 字段路径 | 类型 | 要求 | 说明 |
|---|---|---|---|
| FailureFlag | object | 必需 | 失败标记；未复核严重性不能当成人工确认。 |
| FailureFlag.code | string | 必需 | 错误代码。 |
| FailureFlag.severity | string | 必需 | 严重程度。 enum=["ordinary", "critical"] |
| FailureFlag.attempt_or_execution | string | 必需 | 行为是否落地。 enum=["attempt", "executed", "not_applicable"] |
| FailureFlag.evidence | array | 必需 | 具体依据。 |
| FailureFlag.evidence[] | string | 必需 | 证据。 |
| FailureFlag.review_status | string | 必需 | 复核状态。 enum=["pending", "confirmed", "rejected"] |


## 可扩展对象

generation保存实际参数，固定值见evaluation_profiles.json。model_raw_responses保存模型原始协议、结束原因、token数、批次和耗时；Edge的audio_evidence记录实际送入编码器的音频哈希/时长，batch_members是批次输入标识，batch_index是批内位置。Qwen响应遵循llama.cpp的OpenAI-compatible格式，扩展字段原样保留。

audio_judge含requested_model、返回model、temperature、enable_thinking、request_id、usage、prompt_sha256、evidence_version、evidence_sha256、audio_sha256、user_audio_sha256、model_answer_text_supplied=false、format_attempts、schema_adapter和result。result.dimensions含dimension_id/score/reason/evidence；semantic_checks含check_id/passed/reason/evidence；critical_failures为严重错误数组；heard_turns逐轮含user_turn_index/assistant_transcript/acoustic_notes；task_achieved是任务完成布尔值。usage缺失不补造，format_attempts链接格式校验的原始尝试。

assistant_audio含路径、文件哈希、时长、采样率、模型、规范化版本和实际朗读文本。Edge还记录raw_text/external_tts=false/ended/hit_frame_budget/wall_seconds；baseline记录text/external_cloud_tts=false/batch_offset/batch_seed/batch_keys，以及termination_evidence_version/ended/hit_frame_budget/codec_generated_tokens/max_codec_tokens；音色与完整生成参数见reports/tts_effective.json。复用缓存波形不是重新采样。

incomplete_turn仅在失败时出现，包含node_id、input_audio、input_audio_sha256、asr_text、assistant_parts_not_spoken、model_raw_responses、first_tool_event_index。未完成轮的文字不能混入已听到的语音评分。

data/audio中的输入元数据保留原稿、朗读稿、声音提示、路径、SHA256、时长、规范化版本、合成调用、QC及历史。tts_prompt是实际合成提示，wav_container记录容器修正旧/新文件哈希与不变PCM哈希。数据作者记录保留提示、蓝图、原始响应、同模型审读及修复历史；source_refs可回溯，缺失usage/cost不冒充账单。

manifest保存冻结版本/时间/含义及每题、每个实际引用音频的文件哈希。规范JSON哈希为Python json.dumps(sort_keys=True, ensure_ascii=False)默认分隔符的UTF-8，文件哈希直接计算字节。具体键名以清单原文为准。

case_overview每行一题，scene_overview每行一场景，run_overview每行一个实际系统-题目组合，summary保存规模、分母/分子/覆盖数/分数与配对统计。空值表示未完成或不适用，不表示0。供应商扩展字段不保证跨供应商语义相同。
