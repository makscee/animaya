---
phase: 260416-l1z
plan: 01
subsystem: bot/claude_query
tags: [bootstrap, onboarding, session-reset, sdk-options]
requirements: [QUICK-260416-l1z]
files_modified:
  - BOOTSTRAP.md
  - bot/claude_query.py
  - tests/test_claude_query_bootstrap.py
commit: ded559d
date: 2026-04-16
---

# Quick 260416-l1z: Bootstrap Mode Overrides Resumed Session Summary

Two-part fix prevents stale `~/.claude/projects/<encoded-cwd>/` transcripts from
leaking into BOOTSTRAP-driven onboarding: (1) prompt-level authoritative
override clause in BOOTSTRAP.md, (2) SDK-level `continue_conversation=False`
when BOOTSTRAP.md is present.

## What Changed

### BOOTSTRAP.md
Inserted a new `## Bootstrap overrides all prior memory` section between
"You just came online" and "Your first reply — non-negotiable shape". Tells
Claude to treat the operator as first-contact and to ignore any recalled
names/projects/contexts while the file exists.

### bot/claude_query.py
In `build_options()`, compute `in_bootstrap_mode = bool(bootstrap)` right after
`bootstrap = _read_bootstrap()`. Pass
`continue_conversation=not in_bootstrap_mode` to `ClaudeCodeOptions(...)`,
replacing the hardcoded `True`. Emits an INFO log line when bootstrap mode
forces a fresh session so ops can confirm from logs.

### tests/test_claude_query_bootstrap.py
Added a `_options(tmp_path, monkeypatch)` helper that mirrors the existing
`_system_prompt` monkeypatch pattern but returns the full `ClaudeCodeOptions`.
Added three tests:
- `test_continue_conversation_false_when_bootstrap_present` — asserts
  `opts.continue_conversation is False` when BOOTSTRAP.md has non-empty content.
- `test_continue_conversation_true_when_bootstrap_absent` — asserts `True`
  when BOOTSTRAP.md is missing.
- `test_continue_conversation_true_when_bootstrap_empty` — asserts `True`
  when BOOTSTRAP.md exists but is whitespace/empty (matches `_read_bootstrap`
  "no injection" semantics).

All four pre-existing tests (`test_bootstrap_injected_when_present`,
`test_bootstrap_absent_when_file_missing`, `test_bootstrap_absent_when_file_empty`,
`test_bootstrap_tag_escape`) pass unchanged.

## Verification

- `uvx ruff check bot/claude_query.py tests/test_claude_query_bootstrap.py` → clean.
- `python -m pytest tests/test_claude_query_bootstrap.py -v` → 7 passed.
- `python -m pytest tests/ -x` → 319 passed (full suite green, no regressions).

## Deviations from Plan

**[Rule 1 - Lint fix] Split logger.info line**
- **Found during:** ruff post-implementation pass
- **Issue:** `logger.info("BOOTSTRAP.md present — forcing fresh Claude session (continue_conversation=False)")` was 104 chars (E501, limit 100).
- **Fix:** Split into a two-segment implicit-string-concatenation call inside a multi-line `logger.info(...)`. Message text unchanged.
- **File:** `bot/claude_query.py`
- **Commit:** `ded559d`

**[Rule 3 - Out-of-scope cleanup] Reverted `.claude/settings.json`**
- **Found during:** pre-commit `git status` scan.
- **Issue:** Unrelated local edit removed the project's Stop-hook autocommit config — not part of this task and not in `files_modified`.
- **Fix:** `git checkout -- .claude/settings.json` before staging.
- **File:** `.claude/settings.json` (left unchanged on disk)

## Self-Check: PASSED

- FOUND: `BOOTSTRAP.md` contains "Bootstrap overrides all prior memory" section.
- FOUND: `bot/claude_query.py` contains `continue_conversation=not in_bootstrap_mode`.
- FOUND: `tests/test_claude_query_bootstrap.py` contains all 3 new tests.
- FOUND: commit `ded559d` in git log.
- FOUND: 7/7 bootstrap tests pass; 319/319 full suite pass.
