# Release v2.2.4 Stock Master Hotfix

## Goal
Fix user-entered Taiwan stock numbers being displayed as generic custom watchlist items.

## Fixes
- Added local Taiwan Stock Master resolver.
- Fixed `2313` to display as `2313 華通` instead of `2313 自訂觀察`.
- Automatically repairs legacy user watchlist and portfolio records whose names start with `自訂觀察` when a known stock identity exists.
- Shared resolver now works for personal watchlist, portfolio, query search, and custom stock creation.

## Validation
- `make_custom_stock("2313")` returns `2313 華通`.
- `resolve_stock_query("2313")` returns `2313 華通`.
- `resolve_stock_query("華通")` returns `2313 華通`.
- Test suite: 12 passed.
