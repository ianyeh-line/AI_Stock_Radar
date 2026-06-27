# Release v2.2.2 Action Logic Hotfix

## Goal

Fix illogical entry/add-position wording when the current price is already above the support level.

## Problem

Example: if current price is 1015 and the support watch zone is 890-915, the app should not say the stock must "stand back above 915".

## Fix

The decision engine now builds entry text from the current price context:

1. Current price below support.
2. Current price inside support zone.
3. Current price above support but below breakout.
4. Current price near/above breakout.
5. Current price far above breakout.

## Product Impact

Advice is now more consistent with swing-trading logic and less likely to mislead users.
