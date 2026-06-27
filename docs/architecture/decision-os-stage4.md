# Decision OS Stage 4 Architecture

## Objective

v0.8.0 把 AI Stock Radar 從 Dashboard 升級為 Decision OS。

## Pipeline

```text
RSS News / Curated Baseline
        ↓
Chinese Localization
        ↓
Signal Classification
        ↓
Knowledge Map
        ↓
News Evidence Score
        ↓
Technical Radar
        ↓
Risk Score
        ↓
Decision Card
        ↓
Dashboard / Markdown Report
```

## Decision Card

每張 Decision Card 包含：

- 股票代號與名稱
- 雷達分數
- 決策：買進 / 觀察 / 等待 / 賣出
- 信心度
- 新聞分數
- 技術分數
- 風險分數
- Evidence Chain
- Action
- Position Rule
- Risk Note
- Technical Chart Link

## Technical Radar

v0.8.0 支援：

- 現價/收盤價
- 日變動
- 20 日均線
- 60 日均線
- RSI 14
- 技術趨勢
- 技術分數

若即時資料讀取失敗，會自動改用示意備援資料，避免 Dashboard 中斷。

## Product Principle

- 介面必須中文優先。
- 新聞必須回答 So What。
- 每個個股決策必須可點擊查看技術線圖。
- 每個分數必須可拆解。
