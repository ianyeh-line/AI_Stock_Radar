# AI Stock Radar

AI Stock Radar 是台股「股市老師盤前決策系統」。目標不是提供更多資訊，而是每天早上用 3 分鐘回答：哪些股票可以買、哪些等待、哪些避開、持股如何處理。

## v2.1.0 Phase 5 MVP

本版一次推進到 Phase 5 的可執行雛形：

- Phase 2：資料可信度與推薦防呆
- Phase 3：推薦邏輯 Guardrails
- Phase 4：輕量歷史回測驗證
- Phase 5：持股總教練

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
```

## Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

打開：

```text
http://localhost:8501
```

## 注意

本產品是決策輔助工具，不是保證獲利的投資指令。價格使用執行當下可取得的日線資料，新聞為 RSS，法人籌碼以 TWSE 最新可得資料或 fallback 模型補足。
