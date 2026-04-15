---
phase: 01-install-foundation
plan: 01
subsystem: install
tags: [bash, systemd, setup, tdd]
dependency_graph:
  requires: []
  provides: [install-script, systemd-service, run-wrapper]
  affects: [all-phases]
tech_stack:
  added: [systemd user service]
  patterns: [idempotent-bash-installer, env-validation, venv-scoped-python]
key_files:
  created:
    - scripts/setup.sh
    - run.sh
    - systemd/animaya.service
    - tests/conftest.py
    - tests/test_install.py
  modified: []
decisions:
  - "Use explicit venv python path (not source activate) in run.sh for systemd reliability"
  - "Warn but do not auto-install Node.js to avoid breaking Claude Code's own Node"
  - "chmod 600 .env immediately after creation to satisfy T-01-01 threat mitigation"
metrics:
  duration: 15m
  completed: "2026-04-13"
requirements:
  - INST-01
  - INST-02
  - INST-03
  - INST-04
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 1 Plan 1: Install Infrastructure Summary

**One-liner:** Idempotent bash installer with .env validation, Python venv, systemd user service, and CLAUDECODE env sanitization in run.sh.

## What Was Built

Three install artifacts plus a test suite:

- `scripts/setup.sh` — Idempotent install/upgrade script: validates or creates .env interactively (silent token read), checks Node.js, creates Python venv, installs deps, creates `~/hub/knowledge/animaya`, installs and starts systemd user service with linger.
- `run.sh` — Systemd ExecStart wrapper: unsets `CLAUDECODE` and `CLAUDECODE_EXECUTION_ID` before sourcing .env and exec-replacing with venv Python.
- `systemd/animaya.service` — User-mode service unit with `Restart=on-failure`, `RestartSec=5`, journal logging, `WantedBy=default.target`.
- `tests/conftest.py` + `tests/test_install.py` — 27 tests covering syntax, content assertions, threat mitigations.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for install artifacts | 64f1424 | tests/conftest.py, tests/test_install.py |
| 1 (GREEN) | Install infrastructure implementation | ae0285e | scripts/setup.sh, run.sh, systemd/animaya.service |

## Verification

```
bash -n scripts/setup.sh   → exit 0
bash -n run.sh             → exit 0
pytest tests/test_install.py -x -q  → 27 passed
```

## Threat Mitigations Applied

| Threat | Mitigation | Location |
|--------|-----------|----------|
| T-01-01: .env disclosure | `chmod 600 .env` immediately after creation | setup.sh |
| T-01-02: Token prompt leakage | `read -rs` (silent) for CLAUDE_CODE_OAUTH_TOKEN | setup.sh |
| T-01-03: Hardcoded paths | `%h` expansion in ExecStart | animaya.service |
| T-01-04: CLAUDECODE injection | `unset CLAUDECODE` + `unset CLAUDECODE_EXECUTION_ID` | run.sh |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

- `scripts/setup.sh` exists: FOUND
- `run.sh` exists: FOUND
- `systemd/animaya.service` exists: FOUND
- `tests/conftest.py` exists: FOUND
- `tests/test_install.py` exists: FOUND
- Commit 64f1424 (RED tests): FOUND
- Commit ae0285e (GREEN implementation): FOUND
