# Release v3.5.2 - Data Freshness and Input Flow Hotfix

## 目標

修正資料來源優先順序與個人持股新增流程。

## 修正

1. 價格資料以最新可得資料為主，不再盲目偏好官方資料或 Yahoo。
2. Yahoo 日線資料會合併 chart meta 中的最新報價，若該報價日期較新或同日更新，會作為今日股價基準。
3. 官方 TWSE / TPEx 與 Yahoo 仍會比較日期與價格合理性，採用較新且可信的來源。
4. 新增個人持股與觀察清單改用 Streamlit form；使用者輸入股號、股數、成本時不會先抓資料，只有按下加入/更新後才抓取資料。
5. 文件與版本號更新為 3.5.2。

## 驗收

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m streamlit run app.py
```
