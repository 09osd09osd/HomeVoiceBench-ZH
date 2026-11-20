# 本地人工听音评审台

双击 `启动人工评审.cmd`，浏览器打开 `http://127.0.0.1:18789/review/`。页面读取 `review/data.json` 与本地音频，不调用模型、不重新生成。

## 能做什么

1. 左侧按场景/话题/编号筛选 200 个案例；
2. 逐轮播放：用户输入 + 五个系统回答音频；
3. 查看每系统判官评分、理由、工具调用；
4. 写人工备注（本地存储），标记“已听/需复核”；
5. 导出评审 JSON / CSV。

## 数据要求

`review/data.json`（已随仓库提供）与音频。评分案例的音频路径相对 `versions/v0.5/assets/` 或 `assets/sample/`；GitHub 克隆不含大体积音频，需按 [DELIVERY.md](DELIVERY.md) 放置。

## 启动

```powershell
python scripts/serve_review.py --open
```
