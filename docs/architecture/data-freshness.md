# Data Freshness Architecture

AI Stock Radar is not a tick-level real-time terminal.

The product follows this model:

1. CLI run always regenerates the decision payload.
2. Dashboard loads the latest generated payload.
3. If the dashboard payload is older than 30 minutes, it regenerates automatically.
4. Users can press 「重新抓取最新資料」 to force refresh.
5. Data Quality Check displays:
   - generated time
   - price latest date range
   - live price count
   - fallback count
   - news count

This is designed for daily swing-trading decisions, not intraday high-frequency trading.
