# Phase 6: Telethon test harness at hub level for end-to-end Telegram bot testing from Claude Code - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Direct user answers (discuss-phase skipped per auto-execute flow)

<domain>
## Phase Boundary

Build a Telethon-based Python harness that lives under `~/hub/telethon/` (outside the animaya repo) so Claude Code can programmatically converse with an Animaya test bot (`@mks_test_assistant_bot`) — sending messages, waiting for streamed replies, and asserting on response content — without any manual Telegram interaction.

**In scope:**
- Telethon client bootstrap + auth using the user's personal Telegram account
- Session-file persistence so first-run interactive login happens once, then tests run non-interactively
- `api_id` / `api_hash` / `phone` loaded from a `.env` in `~/hub/telethon/` (gitignored)
- A minimal async driver library: `send_to_bot(text)`, `wait_for_reply(timeout, min_chunks=1)`, `assert_contains(substr)`
- One plain async Python smoke-test script that runs a text round-trip and prints PASS/FAIL with captured bot text
- README describing first-run login flow and how to invoke the smoke test from Claude Code

**Out of scope (v1):**
- Voice / photo / file / document round-trips
- Concurrent multi-user scenarios
- Streaming-intermediate-chunk assertions (only final consolidated text matters)
- pytest framework integration (plain scripts only)
- CI wiring
- Testing against a local bot (tests target the deployed `@mks_test_assistant_bot` only)

</domain>

<decisions>
## Implementation Decisions

### Location & Layout
- Harness lives at `~/hub/telethon/` — top-level hub directory, not animaya-specific, reusable for other bots later
- Directory structure:
  ```
  ~/hub/telethon/
  ├── .env                     (gitignored, holds api_id/api_hash/phone)
  ├── .env.example
  ├── .gitignore               (ignores .env, *.session, *.session-journal)
  ├── README.md
  ├── driver.py                (send_to_bot, wait_for_reply, assert_contains)
  ├── client.py                (Telethon client factory + session mgmt)
  ├── tests/
  │   └── smoke_text_roundtrip.py
  └── pyproject.toml           (or requirements.txt — planner decides simplest)
  ```

### Authentication
- Uses the user's **personal Telegram account** (not a dedicated test account)
- Credentials: `TG_API_ID`, `TG_API_HASH`, `TG_PHONE` in `~/hub/telethon/.env`
- User obtains `api_id` / `api_hash` from https://my.telegram.org (documented in README)
- Session stored as `~/hub/telethon/animaya.session` (or similar), created on first run
- First-run flow: script prompts for SMS code interactively; subsequent runs reuse the session file silently

### Target Bot
- Bot username: `@mks_test_assistant_bot` (already deployed and running)
- Bot username is configurable via `BOT_USERNAME` env var in `.env` (default: `mks_test_assistant_bot`)
- No need to spin up a local bot — v1 targets the live test bot only

### Driver API (minimal)
- `async def send_to_bot(client, text: str) -> Message` — sends text to configured bot, returns the Telethon `Message` object
- `async def wait_for_reply(client, timeout: float = 30.0, settle: float = 2.0) -> str` — waits for a reply from the bot, returns the final text. `settle` is a quiet-period after the last message-edit event (handles Animaya's streaming edits — wait for edits to stop before treating the message as final)
- `def assert_contains(text: str, needle: str) -> None` — raises `AssertionError` if `needle not in text`
- All async functions use `asyncio` directly; no test framework

### Streaming handling
- Animaya streams responses by editing a single Telegram message, not by sending multiple messages. The driver subscribes to both `NewMessage` and `MessageEdited` events from the target bot and treats the message as "final" once `settle` seconds pass without further edits
- Reply detection: match on `sender_id == bot_id` resolved from `BOT_USERNAME` at startup

### Test runner
- Plain async Python script pattern:
  ```python
  async def main():
      async with get_client() as client:
          await send_to_bot(client, "hello, respond with the word 'pong'")
          reply = await wait_for_reply(client, timeout=60)
          assert_contains(reply, "pong")
          print(f"PASS — bot replied: {reply[:200]}")

  if __name__ == "__main__":
      asyncio.run(main())
  ```
- Exit code 0 on PASS, non-zero on FAIL — makes Claude Code integration trivial (`python tests/smoke_text_roundtrip.py`)

### Dependencies
- `telethon` (latest stable) as sole runtime dep
- `python-dotenv` for `.env` loading
- No animaya imports — harness is fully independent

### Claude's Discretion
- Exact pyproject/requirements format (pick whichever is simplest — one file, no setup.py)
- Whether to wrap the client in a context manager class or expose a plain async factory
- Exact field names inside `.env` beyond the three above
- README formatting and verbosity
- Whether `client.py` exports a `get_client()` async context manager or a plain connect function

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Telethon library
- Telethon docs (resolve via context7 at planning time: `telethon` library ID) — for `TelegramClient`, `NewMessage`/`MessageEdited` event handlers, session files, interactive login, and `get_entity`/`send_message` APIs.

### Animaya bot behavior (target under test)
- `/Users/admin/hub/workspace/animaya/bot/bridge/telegram.py` — defines how the bot receives messages, streams replies via message edits, and chunks long responses. Driver's `wait_for_reply` settle-timer must align with the bot's edit cadence.
- `/Users/admin/hub/workspace/animaya/bot/bridge/formatting.py` — HTML formatting of responses; influences what raw text comes back (assertions should use plain-text substrings that survive Telegram's HTML rendering).

### ROADMAP context
- `/Users/admin/hub/workspace/animaya/.planning/ROADMAP.md` — Phase 6 entry with Goal + Success Criteria this CONTEXT must satisfy.

</canonical_refs>

<specifics>
## Specific Ideas

- Smoke-test prompt: `"hello, respond with the word 'pong'"` — deterministic enough that Claude Code will reliably include "pong" in the reply; if flaky, fall back to `"please echo the exact string TELETHON_SMOKE_OK"` and assert on `TELETHON_SMOKE_OK`.
- README must document: (1) how to get `api_id`/`api_hash`, (2) first-run login command, (3) how to run smoke test from Claude Code, (4) how to rotate/delete the session file.
- Harness must be runnable as `cd ~/hub/telethon && python tests/smoke_text_roundtrip.py` — no pytest, no complex invocation.

</specifics>

<deferred>
## Deferred Ideas

- Voice round-trip tests (transcription verification)
- Photo/file upload tests
- Concurrent conversation tests (multiple parallel sessions)
- Response-latency SLO assertions
- CI integration (GitHub Actions / systemd timers)
- Test fixtures for common scenarios (reset bot state, pre-seed memory, etc.)
- pytest migration once test count grows beyond ~5

</deferred>

---

*Phase: 06-telethon-test-harness-at-hub-level-for-end-to-end-telegram-b*
*Context gathered: 2026-04-14 via direct user Q&A*
