# AI Stock Radar v3.1.0

AI Stock Radar 是一個「股市老師盤前決策系統」，目標是協助投資人用更少時間完成：

- 今天哪些股票可以買
- 哪些股票只適合觀察
- 持股是否續抱、加碼或減碼
- 哪些個股具備 MACD 0 軸轉強條件

## v3.1.0 重點

1. 清單外個股支援動態新增。
2. 使用者輸入清單外股號時，系統會嘗試抓取 Yahoo Finance `.TW / .TWO` 日線資料。
3. 若 Yahoo 回傳可用資料，系統會自動使用該股資料進行分析。
4. 若可取得股票名稱，會保存到本機自訂股票主檔。
5. 新增「MACD 即將從 0 軸翻正」名單。
6. 持股與觀察清單仍保存於 `~/.ai_stock_radar/`，更新版本不會洗掉。

## 本機執行

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## 升級

```bash
bash ~/Desktop/AI_Stock_Radar_v3.1.0_DynamicStock_MACDZero_Product_Release/upgrade_to_repo.sh
```

## 提交

```bash
bash scripts/cleanup_repo.sh
git add .
git commit -m "Release v3.1.0 Dynamic Stock and MACD Zero Axis"
git push
```
