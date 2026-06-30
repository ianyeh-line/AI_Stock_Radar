# AI Stock Radar v3.2.3

AI 股市老師 Web Beta：修正 Supabase Secrets 設定格式造成的雲端保存失敗。

## 安裝

```bash
bash ~/Desktop/AI_Stock_Radar_v3.2.3_SupabaseSecrets_Hotfix/upgrade_to_repo.sh
```

## 本機驗收

```bash
cd ~/Desktop/AI_Stock_Radar
PYTHONPATH=src python3 -m radar.cli run
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m streamlit run app.py
```

## Streamlit Secrets 正確格式

```toml
[supabase]
url = "https://你的專案.supabase.co"
service_role_key = "你的 service_role 或 secret key"
table = "user_profiles"
```

注意：

- `url` 不要包含 `/rest/v1`。
- `table` 不要填 `public.user_profiles`，只填 `user_profiles`。
- key 不要用 publishable / anon key。

v3.2.3 會自動修正常見誤填，但仍建議 Secrets 使用上面格式。
