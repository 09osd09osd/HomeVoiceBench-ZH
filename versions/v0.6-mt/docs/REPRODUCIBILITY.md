# 运行复现

## 环境

- Windows/Linux，Python 3.10+
- 级联：qwen3-asr + 语言模型（GGUF / Transformers）+ qwen3-tts
- 原生：edge worker（EdgeInstant-Omni-2B）；Qwen2.5-Omni-3B（16kHz 输入）
- 判官：阿里云 MaaS `qwen3.8-omni-flash`

## 步骤（mt-eval）

```powershell
python scripts/local_bridge.py prep --n 100 --skip-asr
python scripts/local_bridge.py content --system qwen35_4b --n 100
python scripts/local_bridge.py tts --system qwen35_4b --workers 4
python scripts/judge_local.py --systems qwen35_4b --workers 8
python scripts/aggregate.py --inp data/judged_local/merged.jsonl --out data/judged_local/summary.json
python scripts/make_report.py
```

## 说明

- 输入语音需先按 `prep` 建立索引；Omni 需 16kHz 重采样（`--resample16`）。
- 判官密钥、模型权重、大体积音频不包含在仓库。
