---
status: partial
phase: 08-bridge-extraction-supervisor-cutover
source: [08-VERIFICATION.md]
started: 2026-04-15
updated: 2026-04-15
---

## Current Test

[awaiting human testing]

## Tests

### 1. Telethon smoke — full bridge lifecycle
expected: install bridge → send message → receive reply → uninstall → confirm silence (TimeoutError) → reinstall → receive reply. All five stages complete without error.
result: [pending]

### 2. Dashboard module install/uninstall via UI
expected: Bridge module shows in module list at animaya-dev.makscee.ru/modules; install and uninstall buttons trigger correct lifecycle; /api/modules returns runtime_entry populated.
result: [pending]

### 3. Boot order log confirmation on LXC
expected: journalctl shows: assemble_claude_md → migrate_bridge_rename (first boot only) → dashboard uvicorn → supervisor start. Second boot shows no migration log (idempotent).
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps

- Missing: tests/telethon/test_bridge_lifecycle_e2e.py (Plan 03 Task 2 SC#3 automated smoke guard)
