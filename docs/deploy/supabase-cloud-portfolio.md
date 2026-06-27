# AI Stock Radar v2.4.0 - Google Login + Supabase Cloud Portfolio

目標：朋友打開 Web Beta 後，可以登入並保存自己的觀察清單與個人持股，下次不用重新輸入。

## 1. 建立 Supabase Table

在 Supabase SQL Editor 執行：

```sql
create table if not exists public.user_profiles (
  user_email text primary key,
  watchlist jsonb not null default '[]'::jsonb,
  portfolio jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_user_profiles_updated_at on public.user_profiles;
create trigger set_user_profiles_updated_at
before update on public.user_profiles
for each row execute function public.set_updated_at();
```

## 2. 設定 Streamlit Secrets

在 Streamlit Cloud App -> Settings -> Secrets，貼上：

```toml
[auth]
redirect_uri = "https://你的-app.streamlit.app/oauth2callback"
cookie_secret = "請換成一段長隨機字串"
client_id = "你的 Google OAuth Client ID"
client_secret = "你的 Google OAuth Client Secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[supabase]
url = "https://你的-project-ref.supabase.co"
service_role_key = "你的 Supabase service_role key"
table = "user_profiles"
```

注意：`service_role_key` 只能放在 Streamlit Secrets，不可寫進 GitHub。

## 3. 設定 Google OAuth Redirect URI

Google Cloud OAuth Client 的 Authorized redirect URI 必須加入：

```text
https://你的-app.streamlit.app/oauth2callback
```

本機測試可加入：

```text
http://localhost:8501/oauth2callback
```

## 4. 使用模式

| 模式 | 行為 |
|---|---|
| 本機模式 | 使用 `~/.ai_stock_radar/` 保存你的本機持股 |
| Web Guest Mode | 未登入朋友的資料只存在 session |
| Web Login Mode | Google 登入後，持股與觀察清單保存到 Supabase |

## 5. 驗收

1. 打開 Streamlit 網站。
2. 點「使用 Google 登入」。
3. 新增 `2313 華通` 到觀察清單。
4. 新增一筆持股。
5. 重新整理頁面或重新登入。
6. 確認資料自動載入。
