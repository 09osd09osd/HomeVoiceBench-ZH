# HomeVoiceBench-ZH v0.2.0

中文家庭纯语音交互基准：30个工具场景、20个聊天场景，每场景20题，共1,000题，每题最多5轮用户语音。包含实验组及两条Qwen级联基线的3,000条实际运行记录、评分和音频证据。

- [在线讲解网页](https://09osd09osd.github.io/HomeVoiceBench-ZH/docs/index.html)
- [Excel总览](https://09osd09osd.github.io/HomeVoiceBench-ZH/outputs/homevoicebench-20261117/HomeVoiceBench-ZH.xlsx)
- [完整结果与评分口径](https://github.com/09osd09osd/HomeVoiceBench-ZH/blob/main/docs/RESULTS.md)

## 下载和使用

1. 克隆仓库，或下载下面的 `homevoicebench-zh-v0.2-source.zip` 并解压。这个包包含代码、冻结文本题目、说明文档、Excel和HTML。
2. 下载 `homevoicebench-zh-v0.2-inputs-001.zip`，获得1,648段去重输入语音。
3. 如需完整回答音频、工具轨迹及判官原始证据，下载全部19个 `evaluation-001` 至 `evaluation-019` ZIP。
4. 将这些ZIP解压到同一个项目目录，保留内部相对路径。每个ZIP独立完整，不需要拼接。
5. 打开 `docs/index.html` 浏览，或按 `docs/REPRODUCIBILITY.md` 重新运行。

发布文件约5.9 GB；可以先下载代码包了解内容，再按需下载音频与证据。[SHA256校验清单](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/SHA256SUMS.txt)与各包一同发布，详细大小和校验值见[交付说明](https://github.com/09osd09osd/HomeVoiceBench-ZH/blob/main/docs/DELIVERY.md)。

三条系统共用数字与单位的中文朗读转换。原始回答、转换后的朗读稿、真实波形和工具数值分别保留。模型权重、API密钥和本机私有环境不在发布包中。

数据为干净的合成普通话，经过机器检查，尚未人工逐题复核。单次运行和单个听音判官的结果不能代表所有真实家庭环境，详细限制见[来源与结论边界](https://github.com/09osd09osd/HomeVoiceBench-ZH/blob/main/docs/PROVENANCE.md)。
