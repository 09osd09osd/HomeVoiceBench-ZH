# 生成、音频与归档元数据字段

题目和运行的完整嵌套字段在 [FIELDS.md](FIELDS.md)。本页补充外部模型生成记录、输入音频缓存、冻结清单和输出缓存。缺值使用null；不存在的供应商计量不填估计值。

## data/authoring/*.json

| 字段 | 含义 |
|---|---|
| blueprint_sha256 | 该批结构化任务蓝图哈希 |
| prompt_sha256 | 作者系统提示词哈希，提示原文见spec/authoring_prompts.json |
| requested_model / returned_model | 请求及返回的模型标识 |
| request_id / usage | 作者请求ID与供应商原始计量 |
| review_request_id / review_usage | 同模型第二次审读请求及计量 |
| review | 审读结论，含每题case_id、valid和问题说明 |
| attempt | 该批成功生成/修复尝试序号，从1开始 |
| generated | 接受的生成内容，含cases数组；每题case_id、title和nodes；每节点node_id、user_text、reference_text |

history与rejected目录保留历史或拒收内容。其对象可能为当次供应商原始响应，不能当成正式接受的题目。整批usage不会重复分摊为每题实测费用。

题目中的provenance.seed是蓝图的数据构造标识，不是DeepSeek请求随机种子。作者请求没有传seed，采用temperature=0.85；不能仅凭这个整数逐字重建云端生成的文字。实际输入TTS种子在audio_assets[].seed及对应data/audio记录中，通常为42，重新合成时按尝试递增。

## data/audio/*.json

| 字段 | 含义 |
|---|---|
| path / sha256 | 实际WAV相对路径与文件SHA256 |
| duration_seconds | 实际音频秒数，来自解析后的PCM帧数 |
| sample_rate / channels / codec | 采样率Hz、声道数、PCM位深格式 |
| model / request_id / usage | 输入TTS模型、调用ID、供应商原始计量 |
| seed / voice_description | 实际请求种子与声音描述提示 |
| source_text / spoken_text | 作者原稿及数字/单位规范化后的实际朗读稿 |
| normalizer_version | zh_spoken_v1 |
| attempt | 合成尝试序号，未通过质检可重生成 |
| status | verified或rejected等生命周期状态 |
| tts_prompt | 新合成记录保留的实际提示，存在时以此为准 |
| qc | 当前输入音频听音质检对象，结构如下 |
| qc_history | 旧质检对象数组，保留版本升级前的证据 |
| wav_container | WAV头规范化审计，结构如下 |

qc字段：

| 字段 | 含义 |
|---|---|
| result | 处理后的质检结果：transcript实际转写、faithful布尔、intelligibility整数0–5、issues问题字符串数组 |
| raw_result | 判官原始质检结果，不被同音/格式等价修正覆盖 |
| orthography_equivalent | 去除标点、数字等价转换及他她它同音归一后是否逐字一致 |
| qc_version | 当前audio_qc_v3 |
| model / request_id / usage / temperature | 实际判官模型、调用ID、计量、温度0 |
| audio_sha256 | 判官实际听取音频的文件哈希 |

wav_container字段：

| 字段 | 含义 |
|---|---|
| version | 容器修正算法版本 |
| upstream_sha256 / canonical_sha256 | 上游原文件与规范WAV文件哈希 |
| pcm_sha256 | 实际采样字节哈希，修正前后保持一致 |
| upstream_declared_frames / actual_frames | 上游头部声明与实际PCM帧数 |
| header_length_repaired | 是否修正声明帧数 |
| resampled / samples_changed | 是否重采样/改变采样内容；本次均false |

正式题目中variants[].audio_assets只保存投影字段，如duration_s、sample_rate_hz、transcript_gt、qc_status；不要把这些名称与缓存元数据duration_seconds/sample_rate混淆。

## ASR与输出音频

`runs/asr/<输入SHA256>.json`：audio_sha256绑定真实输入，text是实际识别文本，language是语言，model是Qwen/Qwen3-ASR-0.6B，ground_truth_supplied固定false。没有作者转写纠正步骤。

`runs/tts/*.json`：text是原始助手文字，spoken_text是规范化朗读文字，normalizer_version是版本；path/sha256/duration_s/sample_rate_hz/model定位实际波形；external_cloud_tts固定false；batch_offset/batch_seed/batch_keys记录离线批次。完整生成参数和运行版本在reports/tts_effective.json及speech_batches历史中。

Edge原生语音缓存按规范化后的朗读文本构造键。不同原文转成同一朗读稿时可复用同一波形，因此assistant_audio.raw_text代表该缓存建立时的原文；当前这一轮的准确模型原文始终以turns[].assistant_text及model_raw_responses为准。assistant_audio.spoken_text仍须与当前轮朗读稿完全一致，发布核验会检查这一点。baseline缓存键还包含原始文字，两种缓存策略都不把未生成的回答补成语音。

正式baseline缓存还含termination_evidence_version=tts_token_eos_v1、ended、hit_frame_budget、codec_generated_tokens和max_codec_tokens。通过只读观察原始talker.generate返回序列判断EOS，不改输入、参数、采样或权重；没有EOS且达到1024 codec token上限时视为截断。旧冒烟试验中缺少这些字段的缓存不进入正式评分。

reports/speech_batches保存每次离线调用的配置和批次时间；batch_size为起始值，adaptive_max_batch_size为扩批上限，batches[].n是实际批大小，seconds是该批墙钟秒数，peak_gpu_bytes是该批峰值显存。自适应TTS记录还含final_batch_size、batch_adjustments和resource_retries。扩批记录offset/from/to/reason/previous_peak_gpu_bytes，另存speech_batch_adjustments。若发生内存不足，speech_resource_attempts记录offset、attempted_batch_size、batch_keys、batch_seed、reason、peak_gpu_bytes和retry_batch_size；失败批次不会先生成评分，再根据分数重跑。

Windows压力事件另外保存实测GPU、可用内存和系统提交量、未完成批次位置及停止原因；中断调用的已完成批次保存为speech_batches/*_partial.json。tts_vocoder_pilot记录独立基础设施试验的同codec比较、帧数、RMSE、最大绝对误差和GPU峰值；decision=not_adopted_in_formal_evaluation明确表示该解码拆批方法没有进入正式语音链路。

allocator_cache_policy=release_unused_after_each_batch表示每批后释放不再使用的CUDA分配器缓存。reserved_gpu_bytes_before_release/after_release是缓存释放前后保留的显存，不等同于peak_gpu_bytes所记录的活跃张量峰值。新调用逐批写入status=running和completed_tasks，正常结束更新status=completed；早期已中断调用的partial记录按当时日志保留。

cuda_allocator_memory_fraction为PyTorch CUDA分配器的进程容量比例，后期设为0.70；这是分配器上限，不是对整台机器或其他进程的显存保证。interrupted_for_resource_scheduling表示为了资源调度而主动中断，不能当作模型错误或OOM；已写入缓存的结果均保留。

`runs/edge_audio/*.json`：raw_text、spoken_text、normalizer_version、path、sha256、duration_s、sample_rate_hz、model、external_tts=false、ended、hit_frame_budget、wall_seconds。ended说明原生talker是否正常结束；hit_frame_budget为true时严格通过被否决。实际题目raw文字以turns[].assistant_text为准，同一朗读稿可共享波形缓存。

## 冻结与归档

| 文件/字段 | 含义 |
|---|---|
| manifest.version / frozen_at / meaning | 版本、UTC冻结时间、冻结定义 |
| manifest.cases[].case_id / path | 每题ID与JSON相对路径 |
| manifest.cases[].file_sha256 | 文件字节哈希 |
| manifest.cases[].canonical_sha256 | 规范JSON哈希，算法见FIELDS.md |
| manifest.audio[].path / sha256 / duration_s | 每个去重引用输入的路径、哈希和秒数 |
| release_assets.inputs / evaluation | 输入与实际测评两个归档组 |
| name / path / bytes / sha256 | ZIP文件名、本地相对路径、大小及哈希 |
| source_sha256 | 归档成员清单哈希 |
| files / uncompressed_bytes | 成员数量及压缩前总大小 |

各ZIP内部release_manifest含files数组，每项path/bytes/sha256。解压保持相对路径。归档不会包含权重、密钥或运行环境。

inputs归档覆盖冻结清单中的全部正式输入。evaluation归档覆盖正式输出、逐题运行与判官原始JSON，并附带本地仍存在的历史/冒烟输出缓存波形。未接受的输入合成尝试不属于正式数据集，不能由其历史元数据推断所有旧输入WAV均已发布。

## 轮数分组统计

`reports/run_overview.json`的turn_count表示实际完成的助手回答轮数；planned_user_turns表示冻结题目预设的正常用户轮数。Excel的Runs表分别显示“完成轮数”和“预设轮数”。`reports/case_overview.json`中的turn_count沿用题目定义，表示预设正常用户轮数。

`summary.by_planned_user_turns`按system_id、category与planned_user_turns分组。planned为该组冻结题数，run_count为已有运行记录数，decided_count为已有最终判定数，passed_count为严格通过数；仅当该组全部判定时strict_pass_rate才为passed_count/planned，否则为null。分组始终依据题目预设轮数，提前终止的运行保留在其原组；实际澄清轮仍受五轮总预算约束。

`reports/api_usage.jsonl`的provider表示接口适配器键（bailian或deepseek），实际地址可由私有配置覆盖。requested_model和returned_model分别表示请求与服务返回的模型标签，不能单靠provider字段推断服务运营方；本次配置核对说明见PROVENANCE.md。
