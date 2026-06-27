# AI Stock Radar

AI Stock Radar 是一個「AI 股市老師盤前決策系統」。目標不是成為資訊網站，而是每天早上幫投資人快速回答：今天哪些股票可以買、哪些等待、哪些避開、持股該續抱還是減碼。

## Current Release

## v2.4.0 User Account + Cloud Portfolio

這版讓 Web Beta 具備朋友長期測試的基礎：

- Google Login / Streamlit OIDC Ready
- Supabase Cloud Portfolio Ready
- 朋友登入後可保存個人持股與觀察清單
- 未登入仍可用 Guest Mode
- 本機模式仍保留 `~/.ai_stock_radar/` 個人資料
- 不把個人持股資料寫進 GitHub

## Run locally

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## Deploy to Streamlit Cloud

App entrypoint:

```text
app.py
```

Repository:

```text
ianyeh-line/AI_Stock_Radar
```

Branch:

```text
main
```

## Enable persistent friend portfolios

See:

```text
docs/deploy/supabase-cloud-portfolio.md
```

You need:

1. Google OAuth Client
2. Streamlit Secrets `[auth]`
3. Supabase project
4. Supabase `user_profiles` table
5. Streamlit Secrets `[supabase]`

Without these secrets, the app remains usable in Guest Mode.

## Important data policy

Personal holdings and watchlists are never committed to GitHub.

Storage by mode:

| Mode | Storage |
|---|---|
| Local Mac | `~/.ai_stock_radar/` |
| Web Guest | Streamlit session only |
| Web Login | Supabase `user_profiles` |

## Validation

```bash
PYTHONPATH=src python3 -m radar.cli run
python3 -m pytest
```
