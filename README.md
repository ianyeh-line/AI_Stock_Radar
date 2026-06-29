# AI Stock Radar 3.0

AI Stock Radar 3.0 is a simplified AI stock teacher dashboard for Taiwan stock swing-trading decisions.

Core purpose:

> Help investors reduce decision time by showing what to buy, what to wait for, what to avoid, and how to manage existing holdings.

## Run locally

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## Outputs

```text
output/dashboard_data.json
output/daily_report.md
```

## Key features

- AI stock teacher homepage
- Buy / Wait / Avoid lists
- Portfolio coach
- Stock master name resolution
- User data persistence under `~/.ai_stock_radar/`
- Streamlit Cloud compatible
- Beta Access mode for web friends: email + access code

## Disclaimer

This tool is for decision support and research only. It is not investment advice, and it does not guarantee returns.
