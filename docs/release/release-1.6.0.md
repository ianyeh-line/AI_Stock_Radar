# Release Notes: v1.6.0 Fresh Decision Workspace

## Summary

v1.6.0 improves practical usability after v1.5.0 by focusing on data freshness, simplified navigation, MACD consistency, and real analysis for user watchlist and portfolio.

## User-facing Changes

- New top section: 盤前決策總覽.
- MACD table now includes price date and source.
- Watchlist entries now show full AI analysis.
- Portfolio entries now show entry/reduce/invalidation conditions.
- Data Quality Check now explains how fresh the data is.

## Technical Changes

- Dashboard auto-refreshes stale payloads after 30 minutes.
- Portfolio stocks are included in the runtime universe, not only watchlist stocks.
- MACD candidate model includes latest date.
- Portfolio analysis includes more actionable card fields.
