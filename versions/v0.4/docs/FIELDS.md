# v0.4 字段与证据说明

题目结构、真实执行记录、工具合同分别保存在 `spec/case.schema.json`、`spec/run.schema.json`、`spec/sandbox.json`。下表从交付 schema 自动生成。原始模型响应和供应方 usage 是开放对象，保留供应方实际返回字段，不臆造统一字段。

完整工具例题：[T10_101](../pilot/data/cases/T10_101.json)。完整聊天例题：[C06_102](../pilot/data/cases/C06_102.json)。对应三组原始执行 JSON 位于 `pilot/runs/<system_id>/<case_id>.json`，当前为本地开发验证记录。

`null` 表示尚无结果或不适用，不等于零分。相对音频路径以所属 split 的根目录为准，例如 `benchmark/assets/audio/...`。同题共用同一份用户波形，三组不会分别重合成输入。

## 题目

| 字段路径 | 类型 | 含义 |
|---|---|---|
| `(根对象)` | object | 完整基础用例；运行结果另存，避免把真实结果和参考答案混在一起。 |
| `schema_version` | string | 见下级字段；以 schema 定义为准。 固定值：0.4.0 |
| `identity` | object | 题目标识。 |
| `identity.case_id` | string | 全局唯一题目 ID。 |
| `identity.case_version` | string | 题目内容版本；修改需升版。 |
| `identity.title` | string | 题目名。 |
| `identity.language` | string | 语言。 可选值：["zh-CN"] |
| `identity.status` | string | 题目生命周期。 可选值：["draft", "reviewed", "frozen"] |
| `classification` | object | 分类与划分，仅评测器使用。 |
| `classification.category` | string | 一级分类。 可选值：["tool", "chat"] |
| `classification.subcategory` | string | 固定子类标识。 可选值：["home_query", "device_control", "environment_query", "schedule_management", "media_management", "task_management", "daily_companionship", "emotional_support", "family_communication", "home_advice", "joint_planning", "learning", "story_roleplay", "games", "interest_discussion", "assistant_boundaries"] |
| `classification.scene_id` | string | 所属场景卡 ID。 |
| `classification.scene_title` | string | 场景名称。 |
| `classification.difficulty` | string | 难度。 可选值：["easy", "medium", "hard"] |
| `classification.tags` | array | 可多选。 |
| `classification.tags[]` | string | 能力标签。 |
| `classification.split` | string | 数据划分。 可选值：["development", "regression", "test"] |
| `classification.group_id` | string | 同源题组；改写和模态变体必须同组同划分。 |
| `provenance` | https://homebench.example/spec/0.2/types.schema.json#/$defs/Generation | 生成记录。 |
| `model_context` | object | 唯一可整体投影给模型的上下文区。 |
| `model_context.system_prompt` | string | 对所有被测模型语义一致的家庭助手指令。 |
| `model_context.actor` | https://homebench.example/spec/0.2/types.schema.json#/$defs/Actor | 可信用户上下文。 |
| `model_context.public_facts` | array | 允许可见的场景背景。 |
| `model_context.public_facts[]` | string | 明确提供给模型的事实。 |
| `model_context.tool_names` | array | 两类都提供同一工具集合。 |
| `model_context.tool_names[]` | string | 启用工具名。 可选值：["device_query", "device_set", "sensor_read", "schedule_list", "schedule_create", "schedule_update", "schedule_cancel", "media_search", "media_play", "media_control", "task_get", "task_cancel"] |
| `model_context.history_policy` | string | 只回填待测模型自己的真实历史及真实工具响应。 可选值：["actual_model_history"] |
| `model_context.audio_transcript_visible` | object | 音频输入不附标准转录。 固定值：False |
| `environment` | https://homebench.example/spec/0.2/types.schema.json#/$defs/Fixture | 私有环境夹具。 |
| `interaction` | object | 对话编排。 |
| `interaction.start_node_id` | string | 起始节点。 |
| `interaction.nodes` | array | 正常节点与备用分支节点，最多32个；限制的是每条实际交互路径最多5轮，不是整个节点库只能有5项。 |
| `interaction.nodes[]` | https://homebench.example/spec/0.2/types.schema.json#/$defs/Node | 对话节点。 |
| `interaction.clarification` | object | 澄清协议。 |
| `interaction.clarification.mode` | string | 先匹配预定义分支，无匹配时使用有次数上限的固定回退。 可选值：["fixed_nodes"] |
| `interaction.clarification.fallback_text` | string | 未预设有效澄清分支时的用户回复，不补充隐藏事实。 |
| `interaction.clarification.max_uses` | integer | 允许回退次数。 |
| `interaction.clarification.counts_as_user_turn` | boolean | 必须计入五轮预算。 |
| `interaction.clarification.resume` | string | 收到正常回答后继续当前节点的 next；回退期间不提前推进。 可选值：["resume_current_node_then_next"] |
| `interaction.clarification.router_profile` | string | 冻结的分支识别器版本，只看可见对话，不看答案。 |
| `interaction.budget` | https://homebench.example/spec/0.2/types.schema.json#/$defs/Budget | 运行预算。 |
| `interaction.termination` | string | 最后节点回答完、预算耗尽或致命运行错误时结束。 |
| `variants` | array | 变体不增加基础题数。 |
| `variants[]` | object | 同一道题的不同输入方式。 |
| `variants[].variant_id` | string | 输入变体 ID。 |
| `variants[].modality` | string | 输入形式。 可选值：["audio"] |
| `variants[].status` | string | 可用状态。 可选值：["ready", "planned", "failed"] |
| `variants[].source_text_variant_id` | null | 无可运行文字变体。user_text仅为作者原稿与评分真值。 |
| `variants[].audio_assets` | array | 音频变体按节点登记，含澄清回退。 |
| `variants[].audio_assets[]` | https://homebench.example/spec/0.2/types.schema.json#/$defs/AudioAsset | 音频登记。 |
| `evaluation` | object | 隐藏评分标准。 |
| `evaluation.rubric_version` | string | 评分规则版本。 |
| `evaluation.checks` | array | 必要条件和诊断条件。 |
| `evaluation.checks[]` | https://homebench.example/spec/0.2/types.schema.json#/$defs/Check | 检查项。 |
| `evaluation.dimensions` | array | 逐项评分。 |
| `evaluation.dimensions[]` | https://homebench.example/spec/0.2/types.schema.json#/$defs/Dimension | 维度。 |
| `evaluation.pass_policy` | object | 整题通过规则。 |
| `evaluation.pass_policy.required_checks_all_true` | boolean | 所有 required 检查必须满足。 |
| `evaluation.pass_policy.require_no_critical_failure` | boolean | 严重错误直接不通过。 |
| `evaluation.pass_policy.require_budget_respected` | boolean | 预算必须满足。 |
| `evaluation.pass_policy.require_normal_completion` | boolean | 必须正常走完规定交互。 |
| `evaluation.pass_policy.min_applicable_dimension_score` | anyOf | 聊天初始门槛为 3；工具主要按必要条件判定，为 null。 |
| `evaluation.task_achieved_definition` | anyOf | 工具任务实际达成的定义；聊天为 null。 |
| `evaluation.critical_failure_definitions` | array | 提前定义；尝试与实际执行分开。 |
| `evaluation.critical_failure_definitions[]` | string | 严重错误及范围。 |
| `evaluation.judge_profile` | string | 语义评分器配置版本，实际模型版本写入运行记录。 |
| `evaluation.behavior_policy` | object | 按实际到达轮次约束查询和写操作；禁止未来授权，含语义要求。 |
| `evaluation.behavior_policy.version` | string | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes` | array | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[]` | object | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[].node_id` | string | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[].allowed_read_tools` | array | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[].allowed_read_tools[]` | string | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[].allowed_writes` | array | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[].allowed_writes[]` | object | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[].must_satisfy` | array | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[].must_satisfy[]` | string | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[].must_not` | array | 见下级字段；以 schema 定义为准。 |
| `evaluation.behavior_policy.nodes[].must_not[]` | string | 见下级字段；以 schema 定义为准。 |
| `evaluation.reporting_partition` | string | 普通任务与超出现有短答预算的长语音要求分开统计，同时保留全量成绩。 可选值：["standard", "budget_stress"] |
| `evaluation.constraint_reference_version` | string | 可核验约束版本；开放式回答不匹配固定示例剧本。 |
| `reference` | object | 隐藏参考过程。 |
| `reference.record_kind` | string | 明确这是示范而非模型测试。 可选值：["authored_reference_not_model_run"] |
| `reference.unique_answer` | object | 参考答案不唯一。 固定值：False |
| `reference.turns` | array | 完整正常路径。 |
| `reference.turns[]` | https://homebench.example/spec/0.2/types.schema.json#/$defs/ReferenceTurn | 参考回合。 |
| `reference.acceptable_alternatives` | array | 不能把单一措辞/轨迹当成唯一答案。 |
| `reference.acceptable_alternatives[]` | string | 允许的合理替代。 |
| `reference.expected_case_pass` | boolean | 参考过程按设计应通过；不是实测成绩。 |
| `quality` | object | 数据质量状态。 |
| `quality.schema_validation` | string | 结构校验状态。 可选值：["pending", "passed", "failed"] |
| `quality.reference_rule_validation` | string | 参考轨迹的规则断言校验。 可选值：["pending", "passed", "failed"] |
| `quality.independent_review` | string | 独立模型或人员审题状态。 可选值：["pending", "passed", "failed"] |
| `quality.human_review` | string | 人工审核状态。 可选值：["pending", "passed", "failed"] |
| `quality.known_limitations` | array | 与此题有关的限制。 |
| `quality.known_limitations[]` | string | 限制。 |
| `design` | object | Versioned split, family, difficulty progression and independent fact-check specification. |

## 实测记录

| 字段路径 | 类型 | 含义 |
|---|---|---|
| `(根对象)` | object | 真实运行记录；参考答案在 case 文件中独立保存 |
| `record_kind` | string | 仅真实运行 固定值：actual_model_run |
| `schema_version` | string | 新版实测记录结构版本 固定值：0.4.0 |
| `case_id` | string | 用例ID |
| `case_sha256` | string | 运行当时完整用例的规范JSON SHA256：sort_keys=True, ensure_ascii=False 默认分隔符 UTF-8 |
| `system_id` | string | 系统ID 可选值：["qwen35_2b", "qwen35_4b", "edge_native"] |
| `model_id` | string | 被测核心模型名称 |
| `input_modality` | string | 统一语音输入 固定值：audio |
| `asr_model` | anyOf | baseline识别模型；Edge为null |
| `tts_model` | string | baseline语音合成模型或 native_talker |
| `normalizer_version` | string | 共享转换版本 |
| `generation` | object | 实际生成参数；见 evaluation_profiles.json |
| `execution` | object | 执行证据 |
| `execution.status` | string | 失败包括真实预算/格式问题与基础设施异常，须结合 flags 判断 可选值：["completed", "failed"] |
| `execution.model_calls` | integer | 实际推理请求数 |
| `execution.tool_calls` | integer | 实际工具调用数 |
| `execution.wall_seconds` | number | 整题交互阶段耗时 |
| `execution.flags` | array | 失败或截断标记，不以假分数替代 |
| `execution.flags[]` | string | 标记或异常类型与说明 |
| `execution.timing_scope` | string | 明确计时范围 |
| `execution.failure` | object/null | stage/type/reason明确失败阶段和原因；预算、已执行调用、当前轮调用、音频与文字可用性、infra_candidate；正常完成为null。 |
| `turns` | array | 已完成交互轮次；异常发生的未完成轮可能不在此数组中 |
| `turns[]` | object | 实际发生的一轮用户交互，含工具循环 |
| `turns[].user_turn_index` | integer | 从1开始，含澄清 |
| `turns[].node_id` | string | 已投递预写节点，或 FALLBACK |
| `turns[].input_variant_id` | string | A0：唯一语音输入变体 |
| `turns[].input_audio` | string | 仓库相对路径；发布包解压后可访问 |
| `turns[].input_audio_sha256` | string | 实际投递波形的 SHA256 |
| `turns[].delivered_text` | null | 没有把题目原文作为文字投递；baseline 的识别结果另记 asr_text |
| `turns[].asr_text` | anyOf | baseline 实际 ASR 识别文本；原生模型为 null |
| `turns[].assistant_text` | string | 模型原始可朗读回答，不含结构化工具调用 |
| `turns[].spoken_text` | string | 共享数字/单位规范化后的朗读文本 |
| `turns[].normalizer_version` | string | 朗读转换版本 |
| `turns[].assistant_audio` | anyOf | 实际输出音频及溯源：path/sha256/duration_s/sample_rate_hz/model/normalizer_version/spoken_text；Edge 另含 raw_text、ended、hit_frame_budget、wall_seconds，baseline 另含 text、batch_offset、batch_seed、batch_keys、external_cloud_tts。原生音频缓存耗时不是当前调用的实时延迟。 |
| `turns[].tool_events` | array | 本轮真实调用顺序 |
| `turns[].tool_events[]` | object | 沙箱事件：request_id、call(tool_name/arguments)、response、state_before/state_after 及逻辑时间；状态类型见 types.schema.json。 |
| `turns[].model_raw_responses` | array | 每次推理的完整原始响应；OpenAI兼容模型保留 choices/usage/timings，原生保留 raw_output/token计数/audio_evidence/finish_reason/worker耗时 |
| `turns[].model_raw_responses[]` | object | 供应方或本地适配器原始响应，不作为判官听音的替代 |
| `turns[].wall_seconds` | number | 该轮交互阶段耗时；baseline 不含离线ASR和TTS；不可横向当作端到端延迟 |
| `turns[].finish_reason` | string | 最后一次生成结束原因 |
| `turns[].routing_label` | string | 固定路由器决策 可选值：["normal", "predefined_clarification", "bounded_fallback"] |
| `turns[].selected_branch_id` | anyOf | 命中预定义澄清分支ID |
| `rule_checks` | array | 客观状态检查 |
| `rule_checks[]` | object | 单项判定 |
| `rule_checks[].check_id` | string | 对应 evaluation.checks.id |
| `rule_checks[].passed` | boolean | 客观规则通过与否 |
| `rule_checks[].observed` | object | 实际观察、差异状态或违规列表 |
| `rule_checks[].evaluator` | string | 规则引擎版本 |
| `tool_trace` | array | 整题完整沙箱日志，包含未完成轮内已发生的调用 |
| `tool_trace[]` | object | 沙箱事件：request_id、call(tool_name/arguments)、response、state_before/state_after 及逻辑时间；状态类型见 types.schema.json。 |
| `incomplete_turn` | anyOf | 预算、格式或服务错误发生时保存的未完成轮：node_id/input_audio/input_audio_sha256/asr_text/assistant_parts_not_spoken/model_raw_responses/first_tool_event_index。未朗读文字不可作为实际音频评分。 |
| `final_state` | object | 真实终态，见 types.schema.json 家庭状态定义 |
| `audio_judge` | anyOf | 实际听音评分记录：model/requested_model/temperature/enable_thinking/request_id/usage/prompt_sha256/audio_sha256/model_answer_text_supplied/result。result 含 dimensions、semantic_checks、critical_failures、heard_turns、task_achieved；分数是0–5整数。 |
| `case_pass` | anyOf | 严格整题通过；未完成评判为null，执行失败可为false且维度分数仍未知 |
| `task_achieved` | anyOf | 判官判断用户主要目标是否达到；与严格通过率分开 |
| `judge_status` | string | scored，或没有可评分回答时的明确原因 |
| `revision` | object | 本次执行/复用来源、各协议哈希、版本和规则变更证据。 |
| `objective_audio_checks` | array | 基于实际WAV的独立ASR和判官听写核对闭合数字；不是音频真值或单位/语义的完全判定。 |
| `objective_audio_checks[]` | object | 见下级字段；以 schema 定义为准。 |
| `audio_fact_review_required` | boolean | 两份听写不一致、缺少听写或通过结论与缺失数字冲突时标记复核。 |
| `case_pass_primary` | boolean/null | 统一语义一致性复核之前的原始听音严格通过结论，保留不覆盖。 |
| `semantic_review` | object | 统一复核初评实际听写和工具证据的语义逻辑；不是第二次独立听音。含version/model/temperature/scope/evidence_sha256/prompt_sha256/request_id/usage/result；result为checks、critical_failures、review_notes。 |
| `audio_adjudication` | object | Blind fresh audio adjudication of rating/numeric conflicts; first schema-valid response, original judgments retained, not human gold. |

## 新增设计字段

| `design` 子字段 | 说明 |
|---|---|
| `index` | 本场景中的题号；开发集用101及以后，正式集用001–020。 |
| `split/partition` | development 或 test；开发不混入正式通过率。 |
| `grouped` | 是否属于40%的成组题。 |
| `family` | 组或独立题的稳定标识；开发、正式不共用family。 |
| `level` | 成组题第1–4级；独立题为null。 |
| `difficulty` | 预设 easy/medium/hard，不由模型成绩反推。 |
| `turns` | 计划用户轮数，不把工具调用计作用户轮次。 |
| `variant` | 夹具和声音选择的确定性变体索引。 |
| `group_size` | 成组题4；独立题1。 |
| `progression` | 同一任务逐步加入的上下文要求说明。 |
| `fixture_index` | 生成冻结家庭夹具的确定性索引。 |
| `tool_profile` | core10；异步场景使用core10+async2。 |
| `core_constraints[]` | node_id、源用户must_satisfy、非强制解释acceptance_guidance、must_not、blocked_read_tools、restriction_evidence。 |
| `audio_facts[]` | node_id、kind、expected、required、source等；闭合数字核对规范。设备/传感器数值可从冻结reference额外导出。 |

## 中断与评分字段

`execution.failure` 的 `stage/type/reason` 给出失败位置、异常类别与具体原因；`completed_user_turns/executed_tool_calls/current_turn_executed_tool_calls` 是已经真实发生的数量；`budget` 是当次约束；`infra_candidate` 只是网络/显存异常候选标记，仍须核验。正常完成时为null。

`incomplete_turn.tool_events` 是中断前已执行的工具；`pending_tool_calls_not_executed` 是被预算阻止、没有执行的调用；`assistant_parts_not_spoken` 是产生但未朗读的文字，不能拿来替代音频打分。旧版缺失字段在页面显示“未记录”。

`objective_audio_checks[]` 包含 `check_id/specification/status/local_asr_text/judge_heard_text/local_asr_match/judge_transcript_match/evaluator/scope`。两种转写一致仅是证据；单位归属、否定、上下文仍需语义评价。`audio_fact_review_required` 标记待复核，不自动把ASR识别错误算成模型错误。

`case_pass` 是严格任务通过；六维分数不单独作为通过门槛。`task_achieved` 保留判官独立判断。`audio_judge` 保留模型、温度、请求ID、用量、提示哈希、证据哈希、听写与逐项理由。没有回答音频时不编造六维分数。

## 工具沙箱

每次返回统一 envelope：request_id、ok、status、data、error、operation_id、clock_time。工具调用的完整参数约束、返回结构及副作用说明见 [sandbox.json](../spec/sandbox.json)。

| 工具 | 层级 | 用途 | 必需参数 |
|---|---|---|---|
| `device_query` | 常用 | 查询设备。可按房间ID或中文房间名、设备类型、设备ID或完整中文设备名筛选；一次返回设备ID、状态、能力、当前用户权限及正在播放的会话。省略筛选返回全部可见设备。未知房间明确报错。 | 无；按查询范围提供可选筛选 |
| `device_set` | 常用 | 修改指定设备状态。 | device_id, changes |
| `sensor_read` | 常用 | 读取房间内指定环境指标。 | room_id, metrics |
| `schedule_list` | 常用 | 查询当前用户可见的未来安排。 | 无；按查询范围提供可选筛选 |
| `schedule_create` | 常用 | 新建提醒、闹钟或定时设备动作。 | kind, when, payload |
| `schedule_update` | 常用 | 修改已有安排，保留安排 ID 和归属。 | schedule_id, patch |
| `schedule_cancel` | 常用 | 取消未来安排。 | schedule_id |
| `media_search` | 常用 | 搜索固定媒体库。 | query |
| `media_play` | 常用 | 在指定设备播放媒体。 | content_id, device_id |
| `media_control` | 常用 | 控制现有播放会话。 | playback_id, action |
| `task_get` | 异步扩展 | 读取异步执行任务状态。 | task_id |
| `task_cancel` | 异步扩展 | 取消仍可取消的异步任务。 | task_id |

状态语义：等价时间按同一时刻比较；每次写入按当前轮授权的对象、字段和值核验；取消已取消安排幂等成功；播放新媒体会停止旧播放。动态ID不要求与参考完全一致。参考是已验证的一条合法路径，不能把其调用顺序当作唯一答案。

## 最终机器裁定与原始评分

- case_pass_primary：初判加客观规则得到的原始通过结论。
- semantic_review.result：盲化语义复核的检查项、严重错误和备注；proposed_case_pass只是候选结论，decision_status标记一致或曾有分歧。
- audio_adjudication.trigger：是否因语义分歧、数字待核验而重新听音。
- audio_adjudication.result：新一次真实听音返回的dimensions、semantic_checks、critical_failures、heard_turns、task_achieved、numeric_checks。最终任务通过使用本次语义及数字结论，并保留客观硬规则；总览质量均分仍使用初判，不择优混用。
- audio_adjudication中的version、model/requested_model、temperature、enable_thinking、prompt_sha256、evidence_sha256、request_id、usage、format_attempts、scope记录裁定协议、服务实际模型、配置、证据绑定和调用来源。格式重试只为获得首个结构有效结果，不按评分重试。
- numeric_checks逐项包含check_id、passed、heard、reason。客观数值检查中的fresh_audio_verification保留重听音后的核验；两个转写一致也不自动等于声学真值。
- reports/run_overview中的final_rating_source区分一致复核与重新听音裁定；audio_adjudicated表示是否完成新听音，不表示人评。
