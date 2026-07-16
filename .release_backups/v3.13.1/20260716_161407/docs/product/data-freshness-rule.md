# Data Freshness Rule v1

## Core Rule

只要資料是目前台股交易狀態下可取得的最新有效資料，就不因來源是 Yahoo、TWSE 或 TPEx 而降等。

## Valid Data By Session

- 盤前：前一交易日收盤資料有效。
- 盤中：當日盤中最新資料有效，並標示「盤中資料非收盤定論」。
- 盤後：當日最新可得資料有效。
- 非交易日：最近交易日資料有效。

## Downgrade Only When

- 資料早於目前交易狀態應採用的最新資料日。
- 資料為 fallback 或模擬資料。
- 資料缺失或無法判斷日期。
- 技術指標樣本不足。

## Not A Downgrade Reason

- 資料來源是 Yahoo。
- 官方資料尚未更新但 Yahoo 較新。
- Yahoo 與官方價格不同但其中一方日期較新。
