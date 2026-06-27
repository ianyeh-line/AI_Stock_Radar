# Release v1.0.0 - Investment Manager Release

## Goal

讓 AI Stock Radar 從「能看」升級成「像專業投資經理人一樣給出波段操作建議」。

## Highlights

- 投資經理人早會摘要
- 資金配置建議
- 分數拆解
- Evidence Chain
- Thesis / Invalidation
- 風險控管
- Data Quality Check

## Acceptance

```bash
PYTHONPATH=src python3 -m radar.cli run
PYTHONPATH=src python3 -m streamlit run app.py
```

Expected outputs:

- `output/daily_report.md`
- `output/dashboard_data.json`
- Dashboard at `http://localhost:8501`
