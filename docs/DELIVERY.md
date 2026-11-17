# 交付包与使用说明

已发布：[09osd09osd/HomeVoiceBench-ZH](https://github.com/09osd09osd/HomeVoiceBench-ZH)。完整资产见[GitHub Release](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/tag/v0.2.0)。

数据规模：50场景、1,000题、1,648段去重输入语音；三个系统共3,000条最终运行记录，其中2,642题有实际回答音频并接受听音评分。其余无回答音频的执行失败计入严格通过率分母，维度分数留空。

首次浏览请打开[说明网页](index.html)、[Excel总览](../outputs/homevoicebench-20261117/HomeVoiceBench-ZH.xlsx)或[结果报告](RESULTS.md)。现有项目目录已经包含所有文件，无需再次解压。

## 搬到另一台电脑

1. 将代码/文本包 `homevoicebench-zh-v0.2-source.zip` 解压到一个新目录；GitHub发布后也可直接克隆仓库。
2. 将输入包和所有evaluation包解压到同一个目录，保留内部相对路径。每个ZIP独立完整，不是需要拼接的分卷压缩文件。
3. 打开 `docs/index.html` 浏览，打开 `outputs/homevoicebench-20261117/HomeVoiceBench-ZH.xlsx` 查看表格。完整运行记录在 `runs/<system>/<case>.json`，其中音频路径相对项目根目录。
4. 需要重新运行模型时按[复现说明](REPRODUCIBILITY.md)安装依赖并配置模型与API。模型权重、密钥和本机环境不包含在交付包中。

代码包包含程序、冻结文本题目、工具合同、字段字典、报告、Excel、HTML及网页试听样例。输入包包含正式输入WAV。evaluation包包含正式回答WAV、逐题轨迹、真实ASR、判官原始响应及保留的修复/试验历史；正式统计只读取三个系统的当前记录，归档历史不混入分数。

## 归档列表

代码包：[homevoicebench-zh-v0.2-source.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-source.zip)。其SHA256在本地 `reports/source_archive.json` 和 `release_parts/SHA256SUMS.txt`，发布时也提供独立SHA256SUMS.txt；不把代码包自身的哈希嵌入其内部。

| 文件 | 大小 MiB | SHA256 |
|---|---:|---|
| [homevoicebench-zh-v0.2-inputs-001.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-inputs-001.zip) | 278.1 | `6568d6ae5f08fd8b817f4e4c92ed552d5097f26b4bc80d81835a8e0678e71706` |
| [homevoicebench-zh-v0.2-evaluation-001.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-001.zip) | 308.5 | `d864c6f247c2c175ee405a99ec9dcd56ba9ac1876823ae4e348e3361a2c40115` |
| [homevoicebench-zh-v0.2-evaluation-002.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-002.zip) | 308.5 | `560ab49a2520cf9a2dd0d46f092ab6666d319ce291c10ba3d4ce0eb1def132a2` |
| [homevoicebench-zh-v0.2-evaluation-003.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-003.zip) | 309.0 | `5f4d3ead31a6f3fce95a2de949247822e117feb9c3c263c5a53cd2d1a7fd9b43` |
| [homevoicebench-zh-v0.2-evaluation-004.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-004.zip) | 308.3 | `ddcec7c5aad7e03ead62b7ecf0c613fd78e94dcadacc4d9c90628b44e91087ac` |
| [homevoicebench-zh-v0.2-evaluation-005.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-005.zip) | 308.3 | `a3804a89a8778caf38e21f7c7d8ffcf44b463341028ce860cc431e3d2ba66d02` |
| [homevoicebench-zh-v0.2-evaluation-006.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-006.zip) | 308.0 | `9170b96e363b310ffdaf62bdf74d83bd75bca33cfccfdac27f671aefa5e727ff` |
| [homevoicebench-zh-v0.2-evaluation-007.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-007.zip) | 308.5 | `7784a8eb8f75f5ea947878d36ce4a1df6b99a1de605f8e5456d1789c49044c6e` |
| [homevoicebench-zh-v0.2-evaluation-008.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-008.zip) | 308.2 | `6ee39111185102e7fb70d3dae499bce964cbcecc59b2bfe2f6ac43e0bbb17973` |
| [homevoicebench-zh-v0.2-evaluation-009.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-009.zip) | 308.3 | `aa125d54e7eaf81d746683902d566fc5ff2540035930a92e9190bf7b3020f002` |
| [homevoicebench-zh-v0.2-evaluation-010.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-010.zip) | 308.4 | `c09833c8869c163bda375c009cead04f2f6afb5f9e51426f7eb13bff45326cf4` |
| [homevoicebench-zh-v0.2-evaluation-011.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-011.zip) | 307.0 | `97b24a21051f2a0950733587741edd3eee0b003dac273fddfc5d3cc1abcdb288` |
| [homevoicebench-zh-v0.2-evaluation-012.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-012.zip) | 308.8 | `7078542130a9fe9380963dbe2e573159767b22a36b31be7631846b5ced2c9f7e` |
| [homevoicebench-zh-v0.2-evaluation-013.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-013.zip) | 308.0 | `54022377d037afc8ddbaf8389caeff998772bb7a1410aa8916f6d7aa9c5179ba` |
| [homevoicebench-zh-v0.2-evaluation-014.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-014.zip) | 308.5 | `235912d8d320720d01a90d7b3c6d3642bab139b2771d665705e86087008df7f3` |
| [homevoicebench-zh-v0.2-evaluation-015.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-015.zip) | 308.3 | `51cd583d617fd28f291e4a218cd94065860e8273558d24a4f7002792d41c2001` |
| [homevoicebench-zh-v0.2-evaluation-016.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-016.zip) | 328.3 | `a9935cecf23ca393a07dff525e838c532d3937c857d6689f4af8a405ef94b023` |
| [homevoicebench-zh-v0.2-evaluation-017.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-017.zip) | 259.3 | `ba6f2aa4c75db90bd8afbba1e0bd0a00ed7799c2c19bc1698f11a7fbb57a948a` |
| [homevoicebench-zh-v0.2-evaluation-018.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-018.zip) | 60.0 | `5cd6f43119af66cad27e139b77a32206da4db16b77e27dc32fb1af31203e6e18` |
| [homevoicebench-zh-v0.2-evaluation-019.zip](https://github.com/09osd09osd/HomeVoiceBench-ZH/releases/download/v0.2.0/homevoicebench-zh-v0.2-evaluation-019.zip) | 49.9 | `749dc92f1b21ae4082d3f438b3e7cfe0d124b1e09bc39a227cb65cdf4aee4aad` |

ZIP已检查CRC并记录SHA256。机器审题和听音评分不等于人工审核；结论边界见[来源与限制](PROVENANCE.md)。
