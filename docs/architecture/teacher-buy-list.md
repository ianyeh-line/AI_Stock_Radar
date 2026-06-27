# Teacher Buy List Architecture

## Purpose

The Teacher Buy List translates Decision Cards into practical swing trading actions.

## Input

- Decision Cards
- Technical profiles
- News impact evidence
- Price levels
- User portfolio analysis

## Output

`teacher_buy_list` payload:

- headline
- summary
- ready_to_buy
- wait_breakout
- pullback_watch
- observe_only
- avoid_or_reduce
- portfolio_actions
- grading_rule

## Grade System

- A: 可行動，但必須照價格區間與停損紀律執行。
- B: 接近可買，等待突破或拉回確認。
- C: 只觀察，不主動買進。
- D: 避免或既有部位反彈減碼。

## Operating Levels

Each item includes:

- suggested_entry_zone
- breakout_trigger
- invalidation_price
- risk_reduce_price
- first_profit_take
- second_profit_take
- volume_condition
- do_not_chase_reason
