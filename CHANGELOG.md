# CHANGELOG

## v3.11.0 - Responsive Decision UX + Chip Data Foundation

### Added

- 新增手機 / 電腦友善的決策頁面結構。
- 新增籌碼資料基礎版，嘗試抓取 TWSE T86 三大法人資料。
- 每張決策卡新增籌碼狀態 badge。
- 個股卡新增「下一步」區塊。
- 個股研究頁將技術圖預設收合，手機閱讀更順。
- 主導覽收斂成六個核心入口。

### Changed

- 資料來源與診斷資訊預設移到頁尾或設定頁，不再搶首頁版面。
- 今日可買、持股、強勢股都改成先結論、再原因、最後細節。
- 籌碼資料不可得時，不再用量能或模板句假裝籌碼判斷。

### Verified

- CLI 可執行。
- 測試通過。
- Release package 不包含 `__pycache__`、runtime output 或 journal runtime 檔案。
