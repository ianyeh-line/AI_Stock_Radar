# AI Stock Radar：Supabase 新手設定指南

目的：讓朋友在線上版輸入 Email + 自訂存取碼後，可以保存自己的觀察清單與個人持股。完成後，朋友下次再用同一組 Email + 存取碼進入，就不用重新輸入持股。

> 不需要 Google Cloud。這版先用 Beta Access：Email + 自訂存取碼。

---

## 你最後需要完成什麼？

你需要拿到並放進 Streamlit Secrets 的三個值：

```toml
[supabase]
url = "https://你的專案.supabase.co"
service_role_key = "你的 Supabase Secret 或 service_role key"
table = "user_profiles"
```

請不要把 key 貼到 GitHub，也不要貼到公開聊天或 LINE 群組。

---

## Step 1：建立 Supabase Project

1. 打開 Supabase 網站並登入。
2. 進入 Dashboard。
3. 如果系統要求你建立 Organization：
   - Organization name：`AI Stock Radar`
   - Type：`Personal`
   - Plan：`Free`
4. 點 `New project` 或 `Create new project`。
5. 填入：
   - Project name：`ai-stock-radar`
   - Database password：按 `Generate a password`，並先存到你的記事本。
   - Region：優先選 `Singapore`，沒有就選 Asia Pacific 相關區域。
   - Plan：`Free`
6. 按 `Create new project`。
7. 等 1～3 分鐘，直到左側出現 `Table Editor`、`SQL Editor`、`Project Settings`。

---

## Step 2：建立 user_profiles 資料表

1. 左側點 `SQL Editor`。
2. 點 `New query`。
3. 貼上以下 SQL：

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

4. 按 `Run`。
5. 如果看到 `Success` 或沒有紅色錯誤，代表成功。

---

## Step 3：確認資料表是否建立成功

1. 左側點 `Table Editor`。
2. 找到 `user_profiles`。
3. 點進去後應該看到欄位：
   - `user_email`
   - `watchlist`
   - `portfolio`
   - `created_at`
   - `updated_at`
4. 目前沒有任何資料是正常的。

也可以到 `SQL Editor` 執行：

```sql
select * from public.user_profiles;
```

如果顯示空表格或 0 rows，但沒有紅色錯誤，就是正常。

---

## Step 4：取得 Project URL

1. 左側點齒輪或 `Project Settings`。
2. 找 `API`、`Data API`，或畫面上方的 `Connect`。
3. 複製 `Project URL`。
4. 它長得像：

```text
https://xxxxxxxxxxxxxxxxxxxx.supabase.co
```

先放到記事本，標記為 `SUPABASE_URL`。

---

## Step 5：取得 Secret / service_role key

1. 仍在 `Project Settings`。
2. 找 `API Keys`。
3. 如果你看到新版 key：
   - 請複製 `Secret key`，通常像 `sb_secret_...`
4. 如果你看到舊版 key：
   - 請複製 `service_role` key。
5. 不要複製到 GitHub。

先放到記事本，標記為 `SUPABASE_SERVICE_ROLE_KEY`。

---

## Step 6：把設定貼到 Streamlit Cloud Secrets

1. 打開 Streamlit Cloud。
2. 進入你的 AI Stock Radar App。
3. 點右下角或右上角 `Manage app`。
4. 點 `Settings`。
5. 找到 `Secrets`。
6. 貼上：

```toml
[supabase]
url = "把你的 Project URL 貼在這裡"
service_role_key = "把你的 Secret 或 service_role key 貼在這裡"
table = "user_profiles"
```

7. 按 `Save`。
8. 按 `Reboot app`。

---

## Step 7：驗收

1. 打開線上版 AI Stock Radar。
2. 左側輸入你的 Email。
3. 輸入自訂存取碼，例如：`ian-test-001`。
4. 新增一檔觀察股，例如 `2313`。
5. 新增一檔持股，例如 `2408`。
6. 重新整理網頁。
7. 再輸入同一組 Email + 存取碼。
8. 如果持股與觀察清單還在，代表設定完成。

---

## 常見問題

### Q1：畫面仍顯示 Supabase 尚未設定？

請檢查 Streamlit Secrets 裡是否是：

```toml
[supabase]
url = "..."
service_role_key = "..."
table = "user_profiles"
```

不是 `SUPABASE_URL=...` 這種格式。

### Q2：我可以用 anon key 嗎？

不建議。請用 Secret key 或 service_role key，並只放在 Streamlit Secrets。

### Q3：朋友是否要知道存取碼？

朋友自己設定並記住即可。同一組 Email + 存取碼會對應同一份雲端資料。
