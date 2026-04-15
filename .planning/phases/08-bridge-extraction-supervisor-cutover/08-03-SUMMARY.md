---
phase: 08-bridge-extraction-supervisor-cutover
plan: 03
status: complete
started: 2026-04-15
completed: 2026-04-15
---

## Summary

Rewrote bot/main.py to use supervisor-driven boot. Removed hard-wired PTB import from core boot path, dropped TELEGRAM_BOT_TOKEN from required env vars, added one-shot config seed for bridge token migration. Supervisor.start_all runs after dashboard is up (D-8.7 boot order). Proper shutdown order maintained via stop_event.

## Key Files

### Created
- `tests/test_main_boot.py` — Boot-order + env-matrix tests (383 lines)

### Modified
- `bot/main.py` — Rewritten _run() with supervisor.start_all, migrate_bridge_rename, token seed
- `bot/modules/lifecycle.py` — Extended with supervisor-aware uninstall path
- `tests/dashboard/test_main_wiring.py` — Updated for new main.py structure
- `tests/modules/test_bridge_config_source.py` — Updated for config seed flow
- `tests/test_skeleton.py` — Adjusted for supervisor boot

## Test Results

271/271 passing, 0 failures

## Self-Check: PASSED

All must_have truths verified:
- bot/main.py contains no import of bot.bridge.telegram in core boot path
- TELEGRAM_BOT_TOKEN is not in REQUIRED_ENV_VARS
- Supervisor.start_all runs AFTER dashboard is up (D-8.7 boot order)
- One-shot seed writes TELEGRAM_BOT_TOKEN into config.json when bridge installed without token
- on_stop runs in updater.stop → stop → shutdown order

## Checkpoint Note

Telethon smoke test (install → roundtrip → uninstall → silence → reinstall) deferred to human verification phase — requires deployed bot on LXC.
