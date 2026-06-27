# Investor Workspace Architecture

## Purpose

Investor Workspace 讓 AI Stock Radar 從固定 Watchlist 產品升級成個人化波段決策工作台。

## Components

```text
config/user_watchlist.json
        ↓
Stock Universe Extension
        ↓
Real Price Decision Engine
        ↓
Dashboard / Report
```

```text
config/portfolio.json
        ↓
Portfolio Analysis
        ↓
Position Guidance
        ↓
Dashboard / Report
```

## Data Policy

`config/user_watchlist.json` 與 `config/portfolio.json` 屬於本機個人資料，預設被 `.gitignore` 排除，不應提交到 GitHub。
