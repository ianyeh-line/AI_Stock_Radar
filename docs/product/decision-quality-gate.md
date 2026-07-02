# Decision Quality Gate

## Purpose

避免 AI Stock Radar 顯示「看起來有分數，但實際不可操作」的推薦。

## Gate Rules

A stock cannot remain A-grade if:

1. Data is fallback, stale, missing, or insufficient.
2. Current price is already above the pullback buy zone and has not completed an effective breakout.
3. Breakout has happened but volume confirmation is insufficient.
4. RSI is overheated.
5. Volume is excessively abnormal.
6. The breakout price is not executable in the current session.

## Output Principle

Teacher advice must answer:

- Can I buy now?
- If not, what price should I wait for?
- What confirms the thesis?
- What invalidates the thesis?
- If I already hold it, should I hold, trim, or add?
