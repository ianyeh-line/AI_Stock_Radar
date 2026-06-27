# AI Stock Radar

AI Stock Radar 是一個協助台股投資人縮短盤前決策時間的本機工具。

目前定位：**AI 股市老師盤前決策系統**。

## v2.2.2 重點

### Action Logic Hotfix

本版修正「現價已高於支撐價，卻仍提示需重新站回支撐價」的不合邏輯語句。

例如國巨現價若為 1015，支撐觀察區為 890～915，系統不會再寫「需重新站回 915」。
新版會改成：

```text
現價 1015.00 已高於支撐區 890.00～915.00，但尚未突破關鍵壓力 1160.00；
不追高，等待突破 1160.00 或回測支撐區守穩再重新評估。
```

### 保留 v2.2.1 修正

- Dashboard 重新抓取資料採快取優先與並行抓取。
- 新增/更新個人持股後，再按重新抓取資料不應長時間卡住。
- 同日價格快取仍保留 Yahoo Finance 最新可得日線資料，避免每次刷新重抓 100 檔。
- MACD 觀察名單只使用最新且真實可得的 Yahoo 日線資料，不使用 fallback 或日期落後資料。
- 個人持股新增後會回到持股分析頁，並顯示本機持股與目前 payload 的分析結果。
- AI 股市老師總評提供盤前姿態、開高/平盤/開低應對與資料風險提醒。

## 執行

```bash
PYTHONPATH=src python3 -m radar.cli run
```

## 開啟 Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

瀏覽器開啟：

```text
http://localhost:8501
```

## 注意

本工具不是逐筆即時交易終端，也不是投資保證。它使用抓取當下可取得的日線價格、RSS 新聞與法人資料，產生波段操作輔助建議。
