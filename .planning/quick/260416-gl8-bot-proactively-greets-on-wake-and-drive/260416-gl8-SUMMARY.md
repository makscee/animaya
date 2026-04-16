---
task: 260416-gl8
title: Bot proactively greets on wake and drives first turn
type: quick
completed: 2026-04-16
commits:
  - 2465962  # Task 1: rewrite BOOTSTRAP.md
  - 857ba67  # Task 2: proactive greet on ownership claim
files:
  modified:
    - bot/data-seed/BOOTSTRAP.md
    - bot/bridge/telegram.py
  created:
    - tests/test_telegram_bridge.py
tests:
  added: 8
  passed: 96  # affected suites: telegram, claim, bridge, bootstrap
---

# Quick Task 260416-gl8: Bot Proactively Greets on Wake Summary

Gave Animaya a first-turn contract: when an operator claims ownership, the bot wakes up from `BOOTSTRAP.md`, emits a warm opener, and drives the conversation — no more dead-end `"Ownership claimed."` plaintext.

## Tasks

### Task 1 — Rewrite `BOOTSTRAP.md` with wake-up framing + first-turn contract
Commit: `2465962`

Reframed `bot/data-seed/BOOTSTRAP.md` as a wake-up brief addressed to the bot itself:
- Opens with "first_boot" framing ("you just woke up — no memories yet")
- Introduces the **first-turn contract**: acknowledge, introduce self ("I'm Animaya"), invite collaboration, match operator language
- Documents the `SYSTEM_EVENT: first_boot` envelope that `_claim_proactive_greet` injects
- Lists lifecycle post-greet: soak up operator's opening, consolidate into memory, never re-emit first-boot

### Task 2 — Proactively greet operator on ownership claim
Commit: `857ba67`

Wired the first-boot contract into the Telegram bridge. Key additions in `bot/bridge/telegram.py`:

- **`_build_greet_envelope(lang_code)`** — Produces the `SYSTEM_EVENT: first_boot` prompt; adds a language hint for non-English operators (`'your opener'`).
- **`_GREET_FALLBACK`** — Bilingual "Hi / Привет… Animaya…" safety net when Claude cannot respond.
- **`_claim_proactive_greet(chat, user, context, module_dir)`** — Idempotent orchestrator:
  1. Reads `state.json`; bails if `greeted=True`.
  2. Runs a one-shot Claude turn through the streaming pipeline using the first-boot envelope.
  3. On SDK failure, sends `_GREET_FALLBACK` via `context.bot.send_message`.
  4. Sets `greeted=True` in state so the path is truly one-shot.
- Post-claim flow no longer emits the legacy `"Ownership claimed."` plaintext — the greet replaces it.

## Tests

New file `tests/test_telegram_bridge.py` (8 cases):
- `test_greets_on_first_claim` — happy path sets `greeted=True`.
- `test_idempotent` — second invocation is a no-op.
- `test_fallback_on_query_failure` — SDK raise → bilingual fallback sent.
- `test_no_ownership_claimed_plaintext` — legacy plaintext is gone.
- `test_build_greet_envelope_{no_lang,with_lang,en_no_hint}` — envelope shape.
- `test_greet_fallback_constant` — fallback constant contains "Hi / Привет" + "Animaya".

Regression check: ran `tests/` with `-k "telegram or claim or bridge or bootstrap"` → **96 passed, 0 failed**.

## Verification

- `uvx ruff check bot/bridge/telegram.py tests/test_telegram_bridge.py` → `All checks passed!`
- `uv run pytest tests/test_telegram_bridge.py -v` → `8 passed`
- Broader affected suite → `96 passed`

## Deviations

None — plan executed as written. Ruff flagged three long method signatures and one long docstring line during cleanup (wrapped them to respect the 100-char limit); no behavior change.

## Self-Check: PASSED

- `bot/bridge/telegram.py` modified, committed in `857ba67`
- `tests/test_telegram_bridge.py` created, committed in `857ba67`
- `bot/data-seed/BOOTSTRAP.md` modified, committed in `2465962`
- Commits `2465962` and `857ba67` present in `git log`
