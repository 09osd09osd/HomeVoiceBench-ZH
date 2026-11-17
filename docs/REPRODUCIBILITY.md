# 运行与复现

实际验证环境是Windows、RTX4090 24GB。GPU阶段依次运行，阶段内部并发；云端生成与评分可和本地GPU工作并行。

## 准备

核心依赖见 `requirements.txt`。分别建立Edge、ASR、TTS虚拟环境，避免模型的transformers版本冲突；实际版本见 `reports/edge_worker_18931.json`、`reports/asr_effective.json`、`reports/tts_effective.json`。取得获授权的原始权重，本仓库不分发公司的Edge权重。

三个环境的关键包版本固定在 `configs/requirements-edge.txt`、`requirements-asr.txt`、`requirements-tts.txt`。这是已运行环境的关键依赖清单，不是所有传递依赖的完整锁文件。不要将三个清单装进同一环境。

将 `configs/runtime.example.json` 复制到忽略的 `.local/runtime.json`，填写模型、虚拟环境和ffmpeg路径，或设置 `HOMEVOICE_<键名大写>` 环境变量。Linux应改用bin/python及对应llama.cpp运行时；该平台未经本次实际验证。

密钥在忽略的 `.local/keys.json` 中配置bailian/deepseek键，或使用DASHSCOPE_API_KEY/DEEPSEEK_API_KEY环境变量。调用地址配置在 `.local/cloud.json`，格式见 `configs/cloud.example.json`。密钥不进入命令行、Git或日志。已有Release音频可直接复测，无需重新付费生成输入。

## 固定模型设置

| 系统 | 设置 |
|---|---|
| Qwen3.5-2B / 4B | llama.cpp b11552（23b0202a1），原始HF权重经同版本converter转BF16 GGUF再Q8_0；每slot8192上下文、4slots、不滑动截断 |
| Qwen官方采样 | temperature=1、top_p=1、top_k=20、min_p=0、presence_penalty=2、seed=42、max_tokens=512、enable_thinking=false；没有greedy baseline |
| Edge原生 | 发布权重BF16/FP32自动dtype、SDPA、do_sample=false、seed42、max_new_tokens256、8192上下文；16k输入、24k原生输出，无外部ASR/TTS |
| ASR | Qwen3-ASR-0.6B、BF16、Chinese、max_new_tokens256；离线批处理，保留实际识别文本 |
| baseline TTS | Qwen3-TTS-12Hz-0.6B-CustomVoice、Vivian、Chinese、原始generation_config采样参数、max_new_tokens1024；共享文字规范化后合成 |
| Judge | qwen3.8-omni-flash、temperature0、enable_thinking=false、实际用户与助手WAV、隐藏系统标签 |

新版converter的GGUF与b11552存在张量布局不兼容，故使用固定版本converter转换原始权重。实际哈希见 `reports/conversion_2B.json`、`reports/conversion_4B.json`。未换成不同模型或量化格式。

新机器先准备官方CUDA13共享库到runtime/cuda（或配置cuda_library_dir），运行prepare_runtime.py下载固定运行时与ASR；fetch_converter.py按configs/pinned_converter_files.json逐文件校验固定源码；随后在已安装torch/transformers的环境运行convert_reference_models.py，将自己的原始HF权重转换成这版Q8_0。已准备好的模型不重复转换。

## 运行顺序

```powershell
python -m unittest discover -s tests -v
python scripts/validate_dataset.py
# 已下载冻结音频时无需重新生成
# 全新版本：generate_dataset.py → synthesize_inputs.py → freeze_dataset.py
# 新版本使用新目录，不覆盖当前冻结数据
.venv-asr/Scripts/python.exe scripts/batch_speech.py asr --batch-size 32
python scripts/complete_evaluation.py
python scripts/summarize.py
python scripts/build_docs.py
node scripts/build_workbook.mjs
python scripts/build_site.py
python scripts/audit_release.py
```

原生worker共用一份权重进行最多4条推理微批，native talker串行访问，避免会话状态串扰。混合1至4轮历史的独立试验中，批处理与逐条输出一致，见 `reports/edge_batch_pilot.json`。早期正式记录含单条推理，每次实际批大小均有记录。

两条Qwen各4并发slot；ASR按32批处理；TTS按文本长度排序。最初以32条一批开始，在实测显存有余量后增至64，完成128段；随后64条批次触发Windows WDDM显存溢出和约99%的系统提交内存占用，停止该未完成批次，保留已完成输出。之后固定16条一批继续（--batch-size 16 --max-batch-size 16）。没有根据答案质量或分数重跑，不更换模型与采样参数。实际每批大小见speech_batches，批量调整见speech_batch_adjustments，资源事件见speech_resource_attempts。原次输出的逐位复现需要对应的batch_keys和batch_seed，单独固定seed不够。多个GPU引擎不同时加载。离线ASR、音频缓存及批量TTS用于吞吐效率，交互墙钟不是端到端实时延迟。

另做过仅拆分波形解码批维度的独立试验：输入codec与全批padding保持一致，但BF16波形误差超过预先写入的比较阈值，因而没有用于正式测评。reports/tts_vocoder_pilot.json记录差异与不采用的决定；scripts/verify_vocoder_batching.py和homevoice/vocoder_batch.py仅用于复核这个基础设施试验，不由正式batch_speech.py调用。正式全部语音继续使用原版波形解码器。

固定16条续跑432段后，发现不同长度批次使分配器保留大量空闲显存（活跃张量峰值约5GiB，但nvidia-smi显示约19GiB）。保留此时累计560段输出，再续跑时于每批结束调用torch.cuda.empty_cache，仅释放空闲缓存，不改变活跃模型张量、采样或波形解码算法。allocator_cache_policy记录该策略，批次记录同时保存释放前后的reserved显存。每批完成即写入可恢复进度，避免中断时丢失批次证据。

该策略稳定运行并再完成992段后，为提高剩余长文本的吞吐，保留累计1552段，后续起始批量改为24，上限24。设置torch.cuda.set_per_process_memory_fraction(0.70)，将CUDA分配器限制在可见显存的70%；若实际批次触及此上限，记录OOM并按现有规则减半。此项是资源调度调整，不改变文本、工具输出、采样参数或原版解码器；实际批次成员与种子仍逐条保存。

该次续跑完成2424段后，一批24条在申请额外2.68GiB时触及分配器上限，程序自动降到12条并继续；此前累计3976段正式音频保留。失败批次没有输出保存或评分，原批次成员、种子和OOM信息见 `reports/speech_resource_attempts/tts_1794865044219854300.json`。

缩批后又完成240段，12条批次约70秒、活跃显存峰值约8.3GiB。为提高余下长回复的吞吐，保留累计4216段后，将后续起始和最大批量设置为18，沿用70%分配器容量限制与OOM自动减半。这个中间批量的选择仅依据资源计量；调度事件和保留记录见speech_resource_attempts。每次续跑的实际批次成员和种子均记录，不能仅凭全局seed复建本次所有音频。

judge_stream.py最多16个云端评分并发：一题的实际输出语音准备好就评分，可与GPU推理和TTS重叠。每题只排入一个在途任务；管线结束时等待流式评分退出再做最后补漏，避免两个评分进程同时改同一条记录。

已有完整记录（包括模型失败）默认跳过。只有明确的基础设施错误才能移入 `runs/infra_attempts` 后重试，保留原因与原记录。预算耗尽、错误工具或错误回答不能因分数低而重跑。随机采样受batch成员和调度影响，seed固定不代表跨GPU/运行库逐位复现；实际输出和批次证据完整保存。

Excel由 `@oai/artifact-tool` 的单一builder读取reports生成，含公式汇总、公式检查和渲染检查。网页为内嵌数据的独立HTML。重新生成报告不需要重新跑模型。

Excel成品随仓库分发，可直接打开。重新运行 `build_workbook.mjs` 需要Node和可解析的 `@oai/artifact-tool`；本次使用Codex随附的2.8.145版本，该库不包含在Python的requirements.txt内，也不随仓库复制。若当前环境没有这套库，可直接使用已导出的Excel及reports中的JSON总览；Python生成统计、Markdown和HTML的步骤独立可用。最终发布前还会从Git索引导出干净副本，运行语法与单元测试，并核对1000道冻结题的字节哈希；结果见 `reports/clean_export_validation.json`。
