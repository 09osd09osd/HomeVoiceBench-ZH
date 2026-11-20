# 字段字典

## 对话脚本（data/dialogues_A.jsonl / B.jsonl）

| 字段 | 类型 | 说明 |
|---|---|---|
| dialogue_id | str | 唯一编号，如 A-home-0001 / B-child-0001 |
| scenario | str | home / child |
| topic | str | 话题 |
| tool_mode | str | mixed / pure_chat 等 |
| age_band | str/null | 儿童年龄段 |
| turn_design | str | distract / change / resume / tool / pure_chat |
| turns | list | 10 轮 |
| turns[].turn | int | 1–10 |
| turns[].user_text | str | 用户话术 |
| turns[].facts | list | 本轮新增事实 |
| turns[].constraints | list | 约束 |
| turns[].probe | str/null | 探针 |
| turns[].tool_expect | list | 期望工具调用 |

## 运行记录（runs/<system>/<dialogue>.json）

| 字段 | 说明 |
|---|---|
| case_id | 对话编号 |
| status | completed / model_limit / error |
| turns[].assistant | 回答文本 |
| turns[].output_audio | {path, duration, sample_rate} |
| turns[].tool_calls | 实际工具调用（参数/返回/状态） |

## 判官记录（reports / review/data.json）

| 字段 | 说明 |
|---|---|
| scores | 11 个维度各 0–5 |
| violations | 违规列表 |
| notes | 判官理由 |
| answer_text | 回答原文 |
| answer_audio | 音频路径 |
