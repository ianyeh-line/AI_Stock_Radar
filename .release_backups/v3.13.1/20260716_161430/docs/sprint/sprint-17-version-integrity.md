# Sprint 17 - Version Integrity

## Problem

User saw app shell showing a newer version while the Daily Report content still displayed an older release. This undermines confidence in whether recommendations are current.

## Decision

Version metadata must be centralized and all runtime output must be validated before display.

## Done

- Added `src/radar/version.py`.
- App, CLI, report generator, and decision payload now use the shared version.
- Stale output invalidation added.
- Upgrade script deletes old runtime output.
- Regression tests added.
