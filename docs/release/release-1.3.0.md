# Release v1.3.0

## Theme

AI Universe & Technical Chart Upgrade.

## Scope

- 內建 AI 產業鏈 100 檔台股預設清單。
- 指定觀察與個人持股分析支援從預設清單選取。
- 清單外個股仍可由使用者輸入股號新增。
- 技術線圖改為波段視角，預設 3 個月。
- 技術線圖支援 1M / 3M / 6M / 1Y 切換。
- K 線圖與成交量整合，成交量加入 MV5 / MV20。

## Validation

```bash
PYTHONPATH=src python3 -m radar.cli run
PYTHONPATH=src python3 -m streamlit run app.py
```
