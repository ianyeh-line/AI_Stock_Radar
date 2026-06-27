# Release Notes - v0.8.0 Stage 4 Decision OS

## Summary

本版直接跳到 Stage 4：Decision OS v1，完成中文化、中文新聞、互動式個股技術線圖，以及 News + Technical + Risk 的整合判斷。

## Key User Value

使用者打開 Dashboard 後，可以：

1. 用中文看懂今日市場判斷。
2. 用中文看懂新聞如何影響個股。
3. 點擊任何提到的個股查看技術線圖。
4. 看到每檔股票的新聞、技術、風險分數拆解。
5. 在 3 分鐘內形成買進、觀察、等待、賣出的初步行動。

## Validation Command

```bash
PYTHONPATH=src python3 -m radar.cli run
```

## Dashboard Command

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```
