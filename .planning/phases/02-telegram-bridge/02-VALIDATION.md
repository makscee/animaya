---
phase: 2
slug: telegram-bridge
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-15
retroactive: true
nyquist_gap_reason: "threat_model not enforced at Phase 02 plan time; behavioral tests in tests/test_bridge.py cover all TELE-XX"
---

# Phase 2 — Validation Strategy

> Retroactive per-phase validation contract. Phase 02 shipped with 37 tests covering TELE-01 through TELE-05. This document maps those tests to requirements and documents the Nyquist sign-off.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/test_bridge.py tests/test_formatting.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_bridge.py tests/test_formatting.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | TELE-01 | — (N/A — phase predates security_enforcement) | Markdown→HTML formatting preserves code blocks, escapes HTML | unit | `python -m pytest tests/test_formatting.py -x -q` | ✅ | ✅ green |
| 02-01-02 | 01 | 1 | TELE-02 | — | Streaming throttle respects min interval + min chars | unit | `python -m pytest tests/test_bridge.py::TestStreamingThrottle -x -q` | ✅ | ✅ green |
| 02-01-03 | 01 | 1 | TELE-03 | — | Per-user asyncio locks prevent concurrent Claude calls | unit | `python -m pytest tests/test_bridge.py::TestUserLocking -x -q` | ✅ | ✅ green |
| 02-01-04 | 01 | 1 | TELE-04 | — | Long responses chunked to ≤4096 chars per Telegram limit | unit | `python -m pytest tests/test_bridge.py::TestMessageChunking -x -q` | ✅ | ✅ green |
| 02-01-05 | 01 | 1 | TELE-05 | — | build_options returns ClaudeCodeOptions with correct model/cwd/permissions | unit | `python -m pytest tests/test_bridge.py::TestBuildOptions -x -q` | ✅ | ✅ green |
| 02-02-01 | 02 | 2 | TELE-01 | — | main() calls build_app with TELEGRAM_BOT_TOKEN | integration | `python -m pytest tests/test_skeleton.py::TestTelegramBridgeIntegration -x -q` | ✅ | ✅ green |
| 02-02-02 | 02 | 2 | TELE-01 | — | main() awaits run_polling (not blocked on asyncio.Event) | integration | `python -m pytest tests/test_skeleton.py::TestTelegramBridgeIntegration::test_main_awaits_run_polling -x -q` | ✅ | ✅ green |
| 02-02-03 | 02 | 2 | TELE-01 | — | assemble_claude_md called before build_app | integration | `python -m pytest tests/test_skeleton.py::TestTelegramBridgeIntegration::test_assemble_claude_md_before_build_app -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Retroactive — Wave 0 coverage pre-existed in `tests/test_bridge.py` and `tests/test_formatting.py` shipped with Phase 02. All test files were created as part of the TDD RED phase (Plan 01, Task 1) and were green by Plan 01, Task 2.

- [x] `tests/test_formatting.py` — 37 tests total covering formatting, bridge, skeleton integration
- [x] `tests/test_bridge.py` — bridge streaming, locking, chunking tests
- [x] `tests/test_skeleton.py` — 12 skeleton/integration tests including 3 bridge integration tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Telegram send/receive with live bot token | TELE-01 | Requires real Telegram account + live bot token; no mock can fully substitute PTB polling loop | 1. Set `.env` with TELEGRAM_BOT_TOKEN + CLAUDE_CODE_OAUTH_TOKEN. 2. `python -m bot`. 3. Send `/start` — verify welcome message. 4. Send text — verify streamed Claude response with typing indicator. 5. Send 500+ word prompt — verify multiple messages. 6. Ctrl+C — verify clean exit. |
| Voice message falls through gracefully | TELE-05 | Voice transcription stub requires real Telegram voice message | Send a voice message; verify placeholder response `[Voice messages not yet supported]` appears |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (retroactive — tests shipped with phase)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] Threat model gap documented: N/A — phase predates security_enforcement; behavioral tests in tests/test_bridge.py cover all TELE-XX requirements

**Approval:** approved 2026-04-15 (retroactive)
