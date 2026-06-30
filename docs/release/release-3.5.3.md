# Release v3.5.3 - Data Freshness Rule Update

## Goal

落實新的資料採用規則：只要資料是目前交易狀態下可取得的最新資料，就不因來源為 Yahoo、官方尚未同步、或不同來源價差而自動降等。

## Changes

- 盤前接受前一交易日收盤資料。
- 盤中接受當下最新盤中資料。
- 盤後接受今日最新可得資料。
- 非交易日接受最近交易日資料。
- 移除「價格來源差異過大且無法判斷誰可信」的降等邏輯。
- 僅在資料真正過舊、fallback、缺失或技術樣本不足時限制強推薦。

## Validation

- CLI executable.
- Unit tests updated for v3.5.3.
