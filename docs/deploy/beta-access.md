# Beta Access Persistence

Friends can use Email + Access Code in the sidebar.

If Supabase Secrets are configured, the app saves watchlist and portfolio in Supabase.
If Supabase is not configured, the app keeps data only in the current browser session.

Required Streamlit Secrets:

```toml
[supabase]
url = "https://xxxx.supabase.co"
service_role_key = "your-secret-or-service-role-key"
table = "user_profiles"
```
