# AI Stock Radar v3.5.4

AI Stock Radar 是一個以「股市老師」為核心的台股決策輔助工具。

本版重點：

- 持股總教練語氣與邏輯升級。
- 最新有效資料不因來源為 Yahoo 或官方尚未同步而降等。
- 個人持股建議更完整，包含續抱、加碼、減碼、失效條件與劇本推演。

## 本機執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```
