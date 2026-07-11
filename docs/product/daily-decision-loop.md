# Daily Decision Loop

## 目的

AI Stock Radar 不只產生今日推薦，而是每天形成：

```text
盤前計畫 → 盤中觀察 → 盤後檢討 → 明日準備
```

## 核心規則

- 盤前：給今日作戰計畫。
- 盤中：檢查強勢股哪些可追、哪些不可追。
- 盤後：檢討推薦與市場實際強勢落差。
- 非交易日：整理下個交易日觀察清單。

## Journal

每次產生資料時，系統會保存 compact decision journal 到：

```text
data/journal/
```

此資料屬 runtime data，不提交 GitHub。

## 驗收

- 第一次無 journal 時，應明確告知尚無前次檢討。
- 第二次開始能讀取前次 journal，產生推薦檢討。
- 強勢股若未被選入可買，必須顯示原因。
- 明日準備應整合今日強勢接力與等待突破名單。
