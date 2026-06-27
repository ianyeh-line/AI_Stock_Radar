# Release Notes - v1.2.1 Investor Workspace Hotfix

## Summary

v1.2.1 修正 v1.2.0 Dashboard 驗收時發現的核心體驗問題，包括功能列表位置、Plotly duplicate ID、K 線與成交量圖表配置、觀察清單新增錯誤，以及持股無法用股票名稱輸入的問題。

## Product Changes

- 功能列表移至頁面最上方。
- 點擊個股後自動切換到「個股技術線圖」。
- K 線、均線、布林通道與成交量整合為同一張圖。
- 持股與觀察清單新增流程支援「清單選擇」與「自由輸入」。
- 新增常用台股名稱解析，提高中文名稱輸入成功率。

## Validation

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```
