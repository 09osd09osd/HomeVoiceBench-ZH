# HomeVoiceBench-MT v0.6.0

中文家庭多轮语音交互基准：**家居闲聊/便签提醒 + 儿童聊天，每段 10 轮，5 条语音链路，判官听音评分**。

## 入口

- [交互讲解网页](docs/index.html)：双击 HTML，浏览评测设计、逐轮结果与两段完整试听样例。
- [在线讲解网页](https://09osd09osd.github.io/HomeVoiceBench-ZH/versions/v0.6-mt/docs/index.html)。
- [本地人工听音评审台](docs/LOCAL_REVIEW.md)：双击 `启动人工评审.cmd`，逐题对照五个系统语音、工具轨迹与评分。
- [Excel 总览](outputs/HomeVoiceBench-MT.xlsx)。
- [结果报告](docs/RESULTS.md)、[评分标准](docs/EVALUATION.md)、[场景与配额](docs/SCENARIOS.md)。
- [数据生成](docs/DATASET.md)、[字段字典](docs/FIELDS.md)、[运行复现](docs/REPRODUCIBILITY.md)。
- [来源与限制](docs/PROVENANCE.md)、[交付包说明](docs/DELIVERY.md)、[数字与单位朗读转换](docs/SPEECH_NORMALIZATION.md)。

## 结论摘要

- 儿童场景：三个级联系统（2b / 4b / minicpm）从第 5–6 轮开始走低，记忆/长程/一致性下降 0.2–0.3；两个原生模型（edge、omni）保持平稳。
- 家居场景：五组都基本平稳。
- 加权总分 4.5–4.9，0.5 阈值不触发；结论以分维度曲线为准。为什么多轮差异小，见 [PROVENANCE.md](docs/PROVENANCE.md)。
