---
phase: 04-first-party-modules
plan: 1
subsystem: identity-module
tags: [identity, onboarding, telegram, claude-query, injection, sentinel]
dependency_graph:
  requires: [03-module-system, 04-00]
  provides: [identity-module-lifecycle, identity-runtime, identity-injection, identity-command]
  affects: [bot/bridge/telegram.py, bot/claude_query.py]
tech_stack:
  added: [bot/modules_runtime/]
  patterns: [sentinel-file-onboarding, xml-injection-escape, conversation-handler-before-message-handler]
key_files:
  created:
    - modules/identity/manifest.json
    - modules/identity/install.sh
    - modules/identity/uninstall.sh
    - modules/identity/prompt.md
    - modules/identity/README.md
    - bot/modules_runtime/__init__.py
    - bot/modules_runtime/identity.py
  modified:
    - bot/claude_query.py
    - bot/bridge/telegram.py
    - tests/modules/test_identity.py
    - tests/modules/test_claude_query_injection.py
decisions:
  - "owned_paths=[] in manifest; identity files live outside ANIMAYA_HUB_DIR (sibling ~/hub/knowledge/identity/); Phase 3 leakage check passes vacuously"
  - "Sentinel at ~/hub/knowledge/identity/.pending-onboarding created by install.sh, cleared by write_identity_files(), removed by uninstall.sh"
  - "XML tag escaping in _read_for_injection() covers identity-user, identity-soul, memory-core (T-04-01-03)"
  - "ConversationHandler registered before catch-all MessageHandler in build_app() (Pitfall 8)"
  - "Inline import sorted by ruff: bot.claude_query before claude_code_sdk in _handle_message"
metrics:
  duration: "~25 min"
  completed: "2026-04-15"
  tasks: 4
  files: 12
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 4 Plan 1: Identity Module Summary

**One-liner:** Sentinel-triggered Telegram onboarding Q&A writing USER.md/SOUL.md with XML-escaped query-time injection into Claude's system prompt.

---

## What Was Built

### Task 1: modules/identity/ package

Five files under `modules/identity/`:

| File | Purpose |
|------|---------|
| `manifest.json` | Phase 3 manifest: `name=identity`, `owned_paths=[]`, no deps |
| `install.sh` | Creates `~/hub/knowledge/identity/` with placeholder USER.md, SOUL.md, and `.pending-onboarding` sentinel |
| `uninstall.sh` | `rm -rf ${IDENTITY_DIR}` — idempotent, removes entire dir (MODS-05 clean) |
| `prompt.md` | Static module doc referencing `<identity-user>` / `<identity-soul>` blocks |
| `README.md` | Documents owned_paths rationale, runtime location, files |

**owned_paths rationale:** identity files live at `~/hub/knowledge/identity/` which is OUTSIDE `ANIMAYA_HUB_DIR` (`~/hub/knowledge/animaya/`). Phase 3 owned_paths validation rejects `..` segments, so `owned_paths=[]`. Cleanup is enforced by `uninstall.sh`; leakage check passes vacuously.

### Task 2: bot/modules_runtime/ package

**`bot/modules_runtime/__init__.py`** — module docstring explaining MODS-06 isolation rationale.

**`bot/modules_runtime/identity.py`** — exports:
- `IDENTITY_DIR`, `USER_FILE`, `SOUL_FILE`, `PENDING_SENTINEL` — path constants
- `PLACEHOLDER_MARKER = "<!-- animaya:placeholder -->"` — install.sh and is_identity_initialized key
- `is_identity_initialized(identity_dir)` — returns True iff both files exist and neither contains placeholder
- `mark_pending_onboarding(identity_dir)` — creates sentinel
- `clear_pending_onboarding(identity_dir)` — removes sentinel
- `write_identity_files(user_text, soul_text, addressing, identity_dir)` — atomic write via `.tmp` + `os.replace`; clears sentinel on success
- `build_onboarding_handler()` — returns `ConversationHandler` with 3-state Q&A (Q1_USER → Q2_SOUL → Q3_ADDRESS)
- `onboarding_start` — entry point function (also called directly by sentinel routing in bridge)

### Task 3: bot/claude_query.py extended (IDEN-03, MEMO-04)

Added at module level:
- `HUB_KNOWLEDGE: Path = Path.home() / "hub" / "knowledge"` — monkeypatchable constant
- `_PLACEHOLDER_MARKER`, `_MAX_INJECT_CHARS = 8_000`
- `_read_for_injection(p)` — reads file, skips if absent/placeholder, truncates at 8KB, escapes `</identity-user>`, `</identity-soul>`, `</memory-core>` to entity form

Inside `build_options()`:
- Injects `<identity-user>` block from USER.md when non-placeholder
- Injects `<identity-soul>` block from SOUL.md when non-placeholder
- Injects `<memory-core>` block from CORE.md when present (forward-declared for plan 04-03)

### Task 4: bot/bridge/telegram.py wired (IDEN-01, IDEN-04)

1. Added import of `PENDING_SENTINEL`, `build_onboarding_handler`, `onboarding_start` from `bot.modules_runtime.identity`
2. `_handle_message`: after `_is_bot_addressed` check, if `PENDING_SENTINEL.exists()` → call `onboarding_start(update, context)` and return (ConversationHandler picks up subsequent Q&A messages)
3. `build_app()`: `app.add_handler(build_onboarding_handler())` inserted BETWEEN `CommandHandler("start")` and the catch-all `MessageHandler`

**Handler registration order verified:**
```
CommandHandler("start") → ConversationHandler("identity_onboarding") → MessageHandler(catch-all)
```

---

## Test Results: 8/8 IDEN Tests Green

```
tests/modules/test_identity.py::TestIdentityInstall::test_install_creates_user_soul_sentinel PASSED
tests/modules/test_identity.py::TestIdentityOnboarding::test_sentinel_present_after_install_cleared_after_qa PASSED
tests/modules/test_identity.py::TestIdentityReconfigure::test_identity_command_reruns_onboarding PASSED
tests/modules/test_claude_query_injection.py::TestIdentityInjection::test_build_options_contains_identity_user_xml PASSED
tests/modules/test_claude_query_injection.py::TestIdentityInjection::test_build_options_contains_identity_soul_xml PASSED
tests/modules/test_claude_query_injection.py::TestIdentityInjection::test_placeholder_content_not_injected PASSED
tests/modules/test_claude_query_injection.py::TestIdentityInjection::test_closing_tag_in_content_is_escaped PASSED
tests/modules/test_claude_query_injection.py::TestMemoryCoreInjection::test_build_options_contains_memory_core_xml PASSED
```

Full modules suite: **35 passed, 8 xfailed** (remaining Wave 0 stubs for memory/git-versioning plans).

---

## Threat Mitigations Confirmed

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-04-01-01 | `_onboarding_cancel` returns `END` without calling `write_identity_files`; placeholder files remain; sentinel still triggers onboarding on next message | In place — `_onboarding_cancel` in identity.py |
| T-04-01-02 | `IDENTITY_DIR` derived deterministically from `dirname(ANIMAYA_HUB_DIR)`; no user-controlled path concatenation | In place — install.sh line 7 |
| T-04-01-03 | `_read_for_injection()` escapes `</identity-user>`, `</identity-soul>`, `</memory-core>` to entity form; truncates at 8KB | In place — claude_query.py; verified by test_closing_tag_in_content_is_escaped |
| T-04-01-04 | ConversationHandler is per-user; per-user lock at `_enqueue_or_run` prevents concurrent overwrite | Accepted — per-user isolation from ConversationHandler + existing lock |
| T-04-01-05 | git-versioning module (plan 04-02) provides commit-level audit | Accepted — deferred to plan 04-02 |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff I001: unsorted inline imports in _handle_message**
- **Found during:** Task 4 ruff check
- **Issue:** Moving `bot.claude_query` import before `claude_code_sdk` in the inline import block triggered Ruff I001; re-ordering to `claude_code_sdk` first still failed because `bot.` sorts before `claude_` alphabetically
- **Fix:** Applied `ruff check --fix` which separated the block into third-party (`claude_code_sdk`) and first-party (`bot.claude_query`) groups per isort convention
- **Files modified:** `bot/bridge/telegram.py`
- **Commit:** 7a8a73d

**2. [Rule 1 - Bug] Unused pytest import in two test files**
- **Found during:** Tasks 2 and 3 ruff check
- **Issue:** Wave 0 stubs had `import pytest` for `@pytest.mark.xfail`; after removing xfail the import became unused
- **Fix:** Removed `import pytest` from both test files
- **Files modified:** `tests/modules/test_identity.py`, `tests/modules/test_claude_query_injection.py`
- **Commit:** 7a8a73d, e8b7a6a

---

## Known Stubs

None — all files created in this plan have real implementations. `<memory-core>` injection is forward-declared (plan 04-03 ships CORE.md) but the injection code itself is functional and tested via `TestMemoryCoreInjection`.

---

## Sentinel Mechanism

```
install.sh runs
  → creates ~/hub/knowledge/identity/.pending-onboarding

_handle_message receives first user message
  → PENDING_SENTINEL.exists() is True
  → calls onboarding_start(update, context) → returns Q1_USER
  → ConversationHandler state machine takes over

After Q3_ADDRESS answer:
  → write_identity_files() called → USER.md + SOUL.md written atomically
  → clear_pending_onboarding() removes .pending-onboarding
  → PENDING_SENTINEL.exists() is now False → next messages go to Claude

uninstall.sh runs
  → rm -rf ~/hub/knowledge/identity/ (removes sentinel, USER.md, SOUL.md)
```

---

## Self-Check: PASSED

| Item | Status |
|------|--------|
| modules/identity/manifest.json | FOUND |
| modules/identity/install.sh | FOUND |
| bot/modules_runtime/identity.py | FOUND |
| bot/claude_query.py | FOUND |
| bot/bridge/telegram.py | FOUND |
| commit ea603a9 (Task 1) | FOUND |
| commit 5e4b9f9 (Task 2) | FOUND |
| commit e8b7a6a (Task 3) | FOUND |
| commit 7a8a73d (Task 4) | FOUND |
| 8/8 IDEN tests green | PASSED |
| 35 passed, 8 xfailed (full modules suite) | PASSED |
