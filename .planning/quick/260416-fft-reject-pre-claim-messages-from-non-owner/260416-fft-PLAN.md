---
phase: 260416-fft
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/bridge/telegram.py
  - tests/test_bridge.py
autonomous: true
requirements:
  - FFT-CLAIM-GATE
must_haves:
  truths:
    - "Before ownership is claimed (claim_status != 'claimed'), no non-claim-code message reaches Claude Code SDK"
    - "A user sending a non-claim message pre-claim receives a concise prompt telling them to send the 6-digit pairing code from the dashboard"
    - "A valid 6-digit pairing code still successfully claims ownership (unchanged behavior — _claim_handler runs at group=-2, before _owner_gate)"
    - "Post-claim behavior is unchanged: owner messages flow through, non-owner messages are dropped via ApplicationHandlerStop"
  artifacts:
    - path: "bot/bridge/telegram.py"
      provides: "_owner_gate rejects pre-claim non-code messages with an informative reply + ApplicationHandlerStop"
      contains: "ApplicationHandlerStop"
    - path: "tests/test_bridge.py"
      provides: "Pytest coverage of _owner_gate's three states: unclaimed → drop+reply, claimed+owner → pass, claimed+non-owner → drop"
      contains: "async def test"
  key_links:
    - from: "bot/bridge/telegram.py::_owner_gate"
      to: "telegram.ext.ApplicationHandlerStop"
      via: "raise after reply_text() when claim_status != 'claimed'"
      pattern: "raise ApplicationHandlerStop"
    - from: "bot/bridge/telegram.py::_owner_gate"
      to: "bot.modules.telegram_bridge_state.read_state"
      via: "state.get('claim_status') check"
      pattern: "claim_status"
---

<objective>
Fix a bridge regression where pre-claim (unclaimed / pending) bots forward ALL incoming Telegram messages to Claude, triggering onboarding flows for random senders before any owner has claimed the bot.

Purpose: Claim codes are handled by `_claim_handler` (group=-2) which raises `ApplicationHandlerStop` on success. Anything that survives to `_owner_gate` (group=-1) pre-claim is, by definition, NOT a valid pairing code — it must be dropped with an informative reply, not passed through.

Output:
- `bot/bridge/telegram.py::_owner_gate` updated to reject pre-claim non-code messages.
- `tests/test_bridge.py` gains coverage for the three `_owner_gate` states.
- Reply text: "This bot is not yet claimed. Send the 6-digit pairing code from the dashboard to claim ownership."
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@bot/bridge/telegram.py
@bot/modules/telegram_bridge_state.py

<interfaces>
<!-- From bot/bridge/telegram.py — `ApplicationHandlerStop` is ALREADY imported (line 21), no new import needed. -->
<!-- Existing imports include `from telegram.ext import ..., ApplicationHandlerStop, ...`. -->

Current `_owner_gate` (bot/bridge/telegram.py, approx. lines 698–717):

```python
async def _owner_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    module_dir = context.bot_data.get("module_dir")
    if module_dir is None:
        return  # no module dir = can't check ownership, allow through
    from bot.modules.telegram_bridge_state import read_state  # noqa: PLC0415
    state = read_state(module_dir)
    if state.get("claim_status") != "claimed":
        return  # BUG: allows all messages through pre-claim
    owner_id = state.get("owner_id")
    if owner_id is None:
        return
    user_id = update.effective_user.id if update.effective_user else None
    if user_id != owner_id:
        raise ApplicationHandlerStop
```

Handler registration order (confirmed, line 732–733):
- `group=-2`: `_claim_handler` (runs first — consumes valid 6-digit codes, raises ApplicationHandlerStop on success claim)
- `group=-1`: `_owner_gate` (runs second — anything here pre-claim is NOT a pairing code)

From `bot/modules/telegram_bridge_state.py::read_state` — returns `{}` on missing/corrupt state. `claim_status` possible values: absent (treated as unclaimed), `"unclaimed"`, `"pending"`, `"claimed"`.

Test suite layout: `tests/test_bridge.py` exists (no current `_owner_gate` tests — grep confirmed zero references to `_owner_gate`, `owner_gate`, `claim`, or `ApplicationHandlerStop` in it). Test conventions use pytest-asyncio (`asyncio_mode = "auto"` in pyproject.toml), so `async def test_*` is sufficient — no decorator needed.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Reject pre-claim non-code messages in _owner_gate + test coverage</name>
  <files>bot/bridge/telegram.py, tests/test_bridge.py</files>
  <behavior>
    Unit tests for `_owner_gate` in `tests/test_bridge.py`:

    - `test_owner_gate_preclaim_drops_and_replies`: state.json has `claim_status="unclaimed"` (or missing claim_status entirely). Mock `update.message.reply_text` as an AsyncMock. Calling `_owner_gate(update, context)` MUST raise `ApplicationHandlerStop` AND call `reply_text` exactly once with a string containing "pairing code" (case-insensitive) and "dashboard".
    - `test_owner_gate_pending_drops_and_replies`: same as above but `claim_status="pending"`. Same assertions (pending is still "not yet claimed" from a gate perspective — valid codes would have been consumed by `_claim_handler` at group=-2).
    - `test_owner_gate_claimed_owner_passes`: `claim_status="claimed"`, `owner_id=12345`, `update.effective_user.id=12345`. Call MUST NOT raise and MUST NOT call `reply_text`.
    - `test_owner_gate_claimed_non_owner_drops_silently`: `claim_status="claimed"`, `owner_id=12345`, `update.effective_user.id=99999`. Call MUST raise `ApplicationHandlerStop` and MUST NOT call `reply_text` (post-claim drop is silent — unchanged behavior).
    - `test_owner_gate_no_module_dir_passes`: `context.bot_data["module_dir"]` absent. Call MUST NOT raise and MUST NOT reply (defensive passthrough for misconfigured bots — unchanged behavior).

    Tests use `tmp_path` for `module_dir`, write `state.json` via `bot.modules.telegram_bridge_state.write_state`, and build a lightweight `update`/`context` via `unittest.mock.MagicMock` + `AsyncMock`.
  </behavior>
  <action>
    Step 1 (RED): Add five tests above to `tests/test_bridge.py`. Import `_owner_gate` from `bot.bridge.telegram` and `ApplicationHandlerStop` from `telegram.ext`. Use `pytest.raises(ApplicationHandlerStop)` for the three drop cases. Run `python -m pytest tests/test_bridge.py -v` — the three pre-claim / claimed-non-owner tests should show the new behavior is not yet implemented (pre-claim tests fail because no exception is raised; claimed-non-owner test already passes under current code).

    Step 2 (GREEN): Modify `_owner_gate` in `bot/bridge/telegram.py`. Replace the `if state.get("claim_status") != "claimed": return` branch with:

    ```python
    if state.get("claim_status") != "claimed":
        # Pre-claim: _claim_handler (group=-2) already consumed valid pairing codes.
        # Anything reaching here is NOT a code — drop it and prompt the user.
        if update.message:
            with suppress(Exception):
                await update.message.reply_text(
                    "This bot is not yet claimed. "
                    "Send the 6-digit pairing code from the dashboard to claim ownership."
                )
        raise ApplicationHandlerStop
    ```

    `ApplicationHandlerStop` is ALREADY imported (line 21). `suppress` is ALREADY imported (line 13). No new imports required.

    Rationale for `with suppress(Exception)`: matches the defensive pattern used elsewhere in this file for Telegram API calls (see `_delete_status`, `_typing_loop`) — a failed reply (network blip, chat blocked) must NOT prevent the drop from taking effect. The `raise ApplicationHandlerStop` is the load-bearing line; the reply is best-effort UX.

    Note on reply deduplication: scope constraints state a single reply per incoming update is acceptable. No dedup/rate-limit state needed — pairing codes resolve the state quickly, and the handler runs once per Telegram update by design.

    Step 3 (VERIFY): Re-run `python -m pytest tests/test_bridge.py -v`. All five new tests MUST pass. Run full bridge suite `python -m pytest tests/test_bridge.py tests/modules/test_bridge_state.py tests/dashboard/test_bridge_install.py -v` to confirm no regressions in adjacent claim-related tests.
  </action>
  <verify>
    <automated>python -m pytest tests/test_bridge.py tests/modules/test_bridge_state.py tests/dashboard/test_bridge_install.py -v</automated>
  </verify>
  <done>
    - All five new `_owner_gate` tests pass.
    - No regressions in `tests/modules/test_bridge_state.py` or `tests/dashboard/test_bridge_install.py`.
    - Grepping `_owner_gate` in `bot/bridge/telegram.py` shows `raise ApplicationHandlerStop` appearing TWICE (once in pre-claim branch, once in post-claim non-owner branch).
    - Manual sanity: reply text matches the exact string in CONTEXT ("This bot is not yet claimed. Send the 6-digit pairing code from the dashboard to claim ownership.").
  </done>
</task>

</tasks>

<verification>
Automated:
- `python -m pytest tests/test_bridge.py tests/modules/test_bridge_state.py tests/dashboard/test_bridge_install.py -v` — all green.
- `python -m ruff check bot/bridge/telegram.py tests/test_bridge.py` — no new warnings.

Manual (out-of-band, after redeploy to LXC 205 per task_context reminder):
- From a fresh unclaimed bot instance, send "hello" from a non-owner Telegram account → expect the pairing-code prompt, NOT onboarding Q1.
- From the dashboard, generate a pairing code and send the 6-digit code from Telegram → expect "Ownership claimed." (unchanged behavior).
- Post-claim, owner sends "hello" → normal Claude streaming response. Non-owner sends "hello" → silently dropped (unchanged).
</verification>

<success_criteria>
- Pre-claim: non-owner "test" messages DO NOT reach Claude; user receives pairing-code prompt.
- Pre-claim: valid 6-digit codes still claim ownership via `_claim_handler` at group=-2.
- Post-claim: owner and non-owner behavior unchanged.
- Five new unit tests lock the contract for `_owner_gate`.
- Zero changes to `_claim_handler`, `_bridge_message_handler`, module install/uninstall, or state schema.
</success_criteria>

<output>
After completion, create `.planning/quick/260416-fft-reject-pre-claim-messages-from-non-owner/260416-fft-01-SUMMARY.md` following the standard summary template.
</output>
