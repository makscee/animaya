---
task-id: quick-260416-fft
type: quick
title: Reject pre-claim messages from non-owners
date: 2026-04-16
commit: c6418ce
---

# Quick Task Summary: Reject pre-claim messages from non-owners

## Task

**ID:** `quick-260416-fft`

**Description:** Before the bot has been claimed, any non-pairing-code message
was silently falling through `_owner_gate` and reaching the Claude handler,
exposing the SDK to strangers. The gate should instead drop the message and
prompt the sender for the pairing code.

## Changes

### `bot/bridge/telegram.py` — `_owner_gate`

When `claim_status != "claimed"`:

- `_claim_handler` (registered at `group=-2`) has already consumed any
  valid 6-digit pairing code by this point, so any message that reaches
  `_owner_gate` is known NOT to be a code.
- Reply to the sender with a short prompt: *"This bot is not yet claimed.
  Send the 6-digit pairing code from the dashboard to claim ownership."*
- Raise `ApplicationHandlerStop` so no further handlers (including the
  Claude message handler) fire for this update.
- The reply is wrapped in `suppress(Exception)` so a blocked-bot /
  deleted-chat error cannot leak up and crash the handler.

Previous behaviour (`return` → continue to Claude) is preserved once the
bot is claimed (`claim_status == "claimed"`, normal owner / non-owner
branching unchanged).

### `tests/test_bridge.py`

Added two unit tests exercising the new pre-claim branch:

- `test_owner_gate_preclaim_drops_and_replies` —
  `claim_status = "unclaimed"`, asserts `ApplicationHandlerStop` is
  raised and the reply mentions `"pairing code"` and `"dashboard"`.
- `test_owner_gate_pending_drops_and_replies` —
  `claim_status = "pending"`, same assertions.

Also cleaned up a few pre-existing lint nits flagged by ruff in this file
(unused `sys` / `TG_MAX_LEN` imports, unused `ctx` local renamed to
`_ctx`, invalid `# noqa: unreachable` → `# noqa: F841`, and shortened
two overlong docstrings).

## Files Changed

| File                     | Change                                           |
| ------------------------ | ------------------------------------------------ |
| `bot/bridge/telegram.py` | `_owner_gate` drops + replies when unclaimed     |
| `tests/test_bridge.py`   | +2 tests for pre-claim path; lint cleanups       |

Diff stat: `2 files changed, 112 insertions(+), 6 deletions(-)`.

## Test Evidence

- `uvx ruff check bot/bridge/telegram.py tests/test_bridge.py` →
  *All checks passed!*
- Prior executor run: full `tests/test_bridge.py` suite **56/56 green**
  (two new tests above included, plus all existing TELE-01..05 and
  owner-gate coverage).
- Post-lint-cleanup changes are cosmetic only (imports, docstring
  wording, unused-variable rename) and do not touch any assertion or
  test logic.

## Commit

```
c6418ce fix(quick-260416-fft): reject pre-claim messages from non-owners
```

## Self-Check: PASSED

- `bot/bridge/telegram.py` — modified, committed in `c6418ce`.
- `tests/test_bridge.py`   — modified, committed in `c6418ce`.
- Commit `c6418ce` present in `git log`.
