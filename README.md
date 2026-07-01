# AI Stock Radar v3.7.0

AI 股市老師盤前決策系統。

## 本版重點：強勢股雷達

v3.7.0 新增「強勢股雷達」，把產品拆成兩個不同問題：

1. **今日可買**：股市老師波段買點，重視買進區間、支撐壓力與風險報酬比。
2. **今日強勢**：市場資金正在追的股票，包含漲停 / 接近漲停、已漲不追、明日接力觀察。

這版不把「強勢」直接等於「可買」。如果股票已漲太多，系統會標示為「已漲不追」或「明日接力觀察」。

## Run CLI

```bash
PYTHONPATH=src python3 -m radar.cli run
```

## Run Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## Upgrade

```bash
bash ~/Desktop/AI_Stock_Radar_v3.7.0_StrongMomentum_Product_Release/upgrade_to_repo.sh
```
