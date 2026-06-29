# AI Stock Radar v3.0.2

AI Stock Radar is an AI 股市老師盤前決策工具.

## Run CLI

```bash
PYTHONPATH=src python3 -m radar.cli run
```

## Run Dashboard

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## v3.0.2 Hotfix

This release restores the expanded Taiwan Stock Master so user-entered holdings like `南亞科` / `2408` resolve correctly instead of being treated as unknown custom stocks.
