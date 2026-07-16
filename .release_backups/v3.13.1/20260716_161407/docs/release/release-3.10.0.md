# Release v3.10.0

## Title

Daily Decision Loop

## Summary

把 AI Stock Radar 從單次推薦工具升級為每日股市老師閉環：

```text
盤前計畫 → 盤中觀察 → 盤後檢討 → 明日準備
```

## Acceptance Criteria

- CLI 可執行。
- Streamlit 可開啟。
- Payload 包含 `decision_loop`。
- 每日報告包含決策閉環段落。
- `data/journal/` 不會被 Git 追蹤。
- 測試通過。
