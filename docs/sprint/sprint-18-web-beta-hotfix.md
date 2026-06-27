# Sprint 18 Hotfix - Streamlit Deploy

## Issue

Web Beta 首次部署在 Streamlit Cloud 失敗，錯誤發生於 apt dependency installation。

## Fix

移除不必要的 `packages.txt`，避免註解文字被 apt-get 當成 package names。

## Acceptance Criteria

- GitHub push 後，Streamlit Cloud 重新部署。
- 不再顯示 `Error installing requirements`。
- App 能開啟 `app.py`。
