# 交付包与解压说明

本目录为 `versions/v0.6-mt/`，可与根目录其他版本共存。

## 目录

```text
v0.6-mt/
  启动人工评审.cmd
  README.md
  docs/            # 讲解网页与本目录 md
  review/          # 本地听音台（index.html / app.js / style.css / data.json）
  reports/         # summary.json / coverage.json
  outputs/         # HomeVoiceBench-MT.xlsx
  assets/sample/   # 两段样例输入与五系统回答音频
  scripts/         # serve_review.py
  data/            # 脚本级数据（可选）
```

## 音频

Git 仓库只含两段样例音频（`assets/sample/`）。完整 2,000 轮输入与回答音频体积大，需从发布包/网盘解压到项目根目录 `assets/`，保持相对路径。缺失时听音台会提示“无音频”，不会补造。

## 其他电脑

1. 克隆仓库；
2. 将完整音频解压到项目根目录 `assets/`；
3. 双击 `启动人工评审.cmd`；或打开 `docs/index.html` 浏览讲解页。
