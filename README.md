# AI Stock Radar v3.2.2

AI Stock Radar 是「AI 股市老師」盤前決策工具，目標是幫助使用者在 3 分鐘內完成台股觀察與波段操作決策。

## 本版重點

- 修正線上版台灣交易狀態判斷。
- 修正市場結論文字被截斷。
- 新增 Supabase 設定助手與新手文件。
- 保留 v3.2.0 的資料可信度、Beta Access、MACD 0 軸與技術線圖能力。

## 本機執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## Supabase 設定

請看：

```text
docs/deploy/supabase-beginner-guide.md
```
