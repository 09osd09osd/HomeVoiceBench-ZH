# 交付包与使用说明

公开仓库：[09osd09osd/HomeVoiceBench-ZH](https://github.com/09osd09osd/HomeVoiceBench-ZH)。v0.3本地交付已完成，公开发布尚未完成；最终状态以reports/publication.json和GitHub Release为准。

数据规模：50场景、1,000题、1650段去重输入语音；三个系统共3,000条最终运行记录，其中2637题有实际回答音频并接受听音评分。其余无回答音频的执行失败计入严格通过率分母，维度分数留空。

首次浏览请打开[说明网页](index.html)、[Excel总览](../outputs/homevoicebench-v030-20261117/HomeVoiceBench-ZH.xlsx)或[结果报告](RESULTS.md)。现有项目目录已经包含所有文件，无需再次解压。

## 搬到另一台电脑

1. 将代码/文本包 `homevoicebench-zh-v0.3-source.zip` 解压到一个新目录；GitHub发布后也可直接克隆仓库。
2. 将输入包和所有evaluation包解压到同一个目录，保留内部相对路径。每个ZIP独立完整，不是需要拼接的分卷压缩文件。
3. 打开 `docs/index.html` 浏览，打开 `outputs/homevoicebench-v030-20261117/HomeVoiceBench-ZH.xlsx` 查看表格。完整运行记录在 `runs/<system>/<case>.json`，其中音频路径相对项目根目录。
4. 需要重新运行模型时按[复现说明](REPRODUCIBILITY.md)安装依赖并配置模型与API。模型权重、密钥和本机环境不包含在交付包中。

代码包包含程序、冻结文本题目、工具合同、字段字典、报告、Excel、HTML及网页试听样例。输入包包含正式输入WAV以及仍被历史/QC元数据引用的缓存；正式输入只计data/manifest.json中的1,650段。evaluation包包含正式回答WAV、逐题轨迹、真实ASR、判官原始响应及保留的修复/试验历史；正式统计只读取三个系统的当前记录，归档历史不混入分数。

## 归档列表

代码包：[homevoicebench-zh-v0.3-source.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-source.zip)。其SHA256在本地 `reports/source_archive.json` 和 `release_parts/SHA256SUMS.txt`，发布时也提供独立SHA256SUMS.txt；不把代码包自身的哈希嵌入其内部。

| 文件 | 大小 MiB | SHA256 |
|---|---:|---|
| [homevoicebench-zh-v0.3-inputs-001.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-inputs-001.zip) | 296.3 | `8f7d163d91352bf5db890103a46f0cb6e4f79ba3661047d793e0ae5c6e1ce1dd` |
| [homevoicebench-zh-v0.3-evaluation-001.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-001.zip) | 308.3 | `168441e7b6b7103cfd41d878915020834e085ac73ddba524393934a9089fbb60` |
| [homevoicebench-zh-v0.3-evaluation-002.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-002.zip) | 308.3 | `4cd8e17e0f737d404293657ffe288eb6e34dae76bea47ad4bf0d21a54fb05761` |
| [homevoicebench-zh-v0.3-evaluation-003.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-003.zip) | 307.6 | `4db392716ca6919b384f47f1fe8588d0723e6c01e4dd473a628c522e49db2ba4` |
| [homevoicebench-zh-v0.3-evaluation-004.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-004.zip) | 307.7 | `ddf4b05aee8e529b0901bbf2536a37abfc21514733e1158ff7e6b4537194b187` |
| [homevoicebench-zh-v0.3-evaluation-005.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-005.zip) | 308.0 | `290dd5255f36393aa2966b10ff4d345be747f544fa7671417a963d3ea76f9158` |
| [homevoicebench-zh-v0.3-evaluation-006.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-006.zip) | 307.5 | `6669bc20a4b6dfd6477c9114b5d4ff0dae3fe3ef267e9d38c63e7608a0f5b2b2` |
| [homevoicebench-zh-v0.3-evaluation-007.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-007.zip) | 307.9 | `37cfd40069e9336c74cc5fe6f888ebded07b1692986a47e707258f03609680b1` |
| [homevoicebench-zh-v0.3-evaluation-008.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-008.zip) | 309.0 | `eb007a3f9d10d0de69f2b71fe2c78a03c51e1e36d25adc044ba7e06ba578c0af` |
| [homevoicebench-zh-v0.3-evaluation-009.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-009.zip) | 308.8 | `5e5c3ebaf59ef655009f2709a4c1acdd7b0bf0c8c83865fbd1e89650b90bbd2c` |
| [homevoicebench-zh-v0.3-evaluation-010.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-010.zip) | 307.1 | `616bca50852aa72b0e0ac9ce3165237e1a624287d4d79decda550ad8fa27b79a` |
| [homevoicebench-zh-v0.3-evaluation-011.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-011.zip) | 308.6 | `a852c5b1052949c41dc34e370d6369660cb0b67e3cd23f48f4ed2f543ef08cb6` |
| [homevoicebench-zh-v0.3-evaluation-012.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-012.zip) | 307.1 | `d30a722b3de256b8d26cbed46e22dfd2c3d408117d30723330335e8a08116ac7` |
| [homevoicebench-zh-v0.3-evaluation-013.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-013.zip) | 308.0 | `f868c31b0d287406e3b36e0f90d2589f18d49af8096582dd70e53762518b1be2` |
| [homevoicebench-zh-v0.3-evaluation-014.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-014.zip) | 307.8 | `fab96c99f9b9bbf0fead88c8a82e7c5248152ee612d38f9621c5f91fd4e5ce33` |
| [homevoicebench-zh-v0.3-evaluation-015.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-015.zip) | 308.4 | `751b2393745da10b103251045b49f340049823f00e98925b75331e73a45c3511` |
| [homevoicebench-zh-v0.3-evaluation-016.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-016.zip) | 307.4 | `8be54f9f4f15d433de5139d5124e07a9d270052b3ef1f9f65416bc4c27372008` |
| [homevoicebench-zh-v0.3-evaluation-017.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-017.zip) | 327.2 | `36a449b25108837777f46b14befe20958923b62326984b6a08065c349e6b2bba` |
| [homevoicebench-zh-v0.3-evaluation-018.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-018.zip) | 308.4 | `0e9f876d9216584679ae196f92ce1086f777f07e058e9cfb48b866ec0c3d550c` |
| [homevoicebench-zh-v0.3-evaluation-019.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-019.zip) | 70.1 | `872862202930deb539f19027fb69127b54810932c252c3f158eb154da685f98f` |
| [homevoicebench-zh-v0.3-evaluation-020.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-020.zip) | 44.1 | `b005fa26a02167b707f789f9fa94cb8570af3a15345ea7b17a9a8264a5aeb5ed` |
| [homevoicebench-zh-v0.3-evaluation-021.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.3.0/homevoicebench-zh-v0.3-evaluation-021.zip) | 16.7 | `f3b53930e8d62e1caec1805acf2d9501045e86b5fd710896d0f8a8a143442bc0` |

ZIP已检查CRC并记录SHA256。机器审题和听音评分不等于人工审核；结论边界见[来源与限制](PROVENANCE.md)。
