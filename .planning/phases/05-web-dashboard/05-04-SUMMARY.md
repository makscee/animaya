---
plan: 05-04
phase: 05-web-dashboard
title: Home page with live status, activity feed, error feed
status: complete
completed: 2026-04-15
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Plan 05-04 Summary

## Delivered

DASH-03 home page at `/` with three HTMX-polled panels:

- **Status strip** (`/fragments/status`) — bot process state + recent stats (5s poll)
- **Activity feed** (`/fragments/activity`) — last 50 events from `bot.events.tail` (5s poll)
- **Error feed** (`/fragments/errors`) — filtered events where `level == "error"` (5s poll)

Hook pattern: `home_routes.register(app, templates)` called by `build_app` factory
when `bot.dashboard.home_routes` is importable. Replaces the Plan 03 placeholder route.

## Files

**Created:**
- `bot/dashboard/status.py` — `recent_stats(hub_dir)` returns counts + systemctl probe
- `bot/dashboard/home_routes.py` — registers `/`, `/fragments/status`, `/fragments/activity`, `/fragments/errors`
- `bot/dashboard/templates/home.html`
- `bot/dashboard/templates/_fragments/status_strip.html`
- `bot/dashboard/templates/_fragments/activity_feed.html`
- `bot/dashboard/templates/_fragments/error_feed.html`
- `tests/dashboard/test_status.py`
- `tests/dashboard/test_home.py`

**Modified:**
- `bot/dashboard/templates/_home_placeholder.html` — placeholder replaced at register time

## Commits

- `0601fcc` test(05-04): failing tests for status + home + fragments
- `16b8636` feat(05-04): add bot/dashboard/status.py — systemctl probe + recent_stats
- `24784d2` (shared) fix: render owner_id on home page

## Verification

- All 26 home/status tests green
- Full dashboard suite: 74/74 passing
- `require_owner` protects every route; 302→/login for unauthenticated, 403 for non-owner

## Deviations

1. `<details>` attribute change in `module_card_failed.html` to satisfy test contract (shared with 05-05).
2. `home_routes.py` passes `user_id` to home template context for the sign-in chip rendering required by `test_root_with_owner_session_renders_home`.
