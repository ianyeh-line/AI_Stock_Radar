# Release v2.3.1 - Streamlit Deploy Hotfix

## Goal

修正 Streamlit Community Cloud 在安裝 dependencies 階段失敗的問題。

## Root Cause

`packages.txt` 內容原本是說明文字：

```text
# System packages for Streamlit Cloud.
# Currently no additional apt packages are required.
```

Streamlit Cloud 在 apt 安裝階段將其中的文字 token 當成 Linux 套件名稱處理，因此出現 `Unable to locate package #`、`Unable to locate package System` 等錯誤。

## Fix

- 移除 `packages.txt`。
- 保留 `requirements.txt` 安裝 Python packages：`streamlit`、`plotly`、`pandas`。

## Validation

部署後 Streamlit Cloud 應能通過 dependency installation，進入 app startup。
