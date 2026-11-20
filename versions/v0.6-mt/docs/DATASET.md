# 数据生成

本版为 **HomeVoiceBench-MT v0.6.0**：家居与儿童两个场景，各 1,000 段、每段固定 10 轮，共 20,000 轮用户语音。评测抽样每场景前 100 段，共 200 段 / 2,000 轮。

## 生成流程

1. 用 DeepSeek 生成 10 轮对话脚本，包含每轮用户话术、事实槽位（facts）、约束（constraints）、探针（probe）、工具期望（tool_expect）与轮次设计（turn_design：distract / change / resume / tool 等）。
2. 脚本按场景/话题配额均衡抽取；家居 7 类话题、儿童 9 类话题，配额见 [SCENARIOS.md](SCENARIOS.md)。
3. 用 `qwen3-tts-flash` 逐轮合成 24kHz 输入语音，数字与单位按 [SPEECH_NORMALIZATION.md](SPEECH_NORMALIZATION.md) 转写后朗读。
4. 级联系统：输入语音先经 ASR（qwen3-asr）转文本，再由语言模型生成回答，最后 TTS 合成 24kHz 回答语音；原生模型直接以音频输入、音频输出。
5. 判官 qwen3.8-omni-flash 听实际回答音频，按 11 个通用维度 + 场景专项评分。

## 规模

| 项 | 值 |
|---|---|
| 家居对话 | 1,000 段（评测 100） |
| 儿童对话 | 1,000 段（评测 100） |
| 每段轮数 | 10 |
| 输入语音 | 20,000 段，24kHz |
| 评测轮次 | 2,000 |
| 系统 | edge_native、qwen35_4b、qwen35_2b、minicpm5_2b、qwen25_omni_3b |

## 注意

- 生成脚本与 TTS 文本会保留在 `data/`；原始大体积音频不随 Git 仓库提交。
- 机器生成 + 机器判官不等于人工审核；边界见 [PROVENANCE.md](PROVENANCE.md)。
