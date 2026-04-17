---
status: resolved
phase: 08-bridge-extraction-supervisor-cutover
source: [08-VERIFICATION.md]
started: 2026-04-15
updated: 2026-04-16
---

## Current Test

[all tests complete]

## Tests

### 1. Telethon smoke — bridge roundtrip
expected: install bridge → send message → receive reply.
result: PASSED — sent "ping — phase 08 smoke test", received "pong — ready." via supervisor-driven bridge on LXC 205.

### 2. Module install via CLI + supervisor boot
expected: lifecycle.install registers module, supervisor on_start activates polling.
result: PASSED — CLI install wrote registry entry with runtime_entry, supervisor imported telegram_bridge, PTB Application started, getUpdates polling active. Bug found: supervisor read config from registry entry (empty) instead of config.json — fixed in 6d90bab.

### 3. Boot order log confirmation on LXC
expected: assembler → dashboard → supervisor → bridge start, in that order.
result: PASSED — boot log confirms: CLAUDE.md assembled (1 modules) → Dashboard serving at 8090 → Uvicorn started → telegram-bridge polling started. Token seed fired correctly on first boot.

## Summary

total: 3
passed: 3
issues: 1 (config source bug — fixed)
pending: 0
skipped: 0
blocked: 0

## Gaps

- Missing: tests/telethon/test_bridge_lifecycle_e2e.py (Plan 03 Task 2 SC#3 automated smoke guard) — deferred, manual Telethon smoke passed
