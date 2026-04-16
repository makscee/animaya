---
phase: 260416-lht
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - BOOTSTRAP.md
  - bot/claude_query.py
  - tests/test_claude_query_bootstrap.py
  - bot/dashboard/templates/_fragments/bridge_install_modal.html
  - bot/dashboard/templates/_fragments/bridge_install_form.html
  - bot/dashboard/templates/bridge_config.html
  - bot/dashboard/bridge_routes.py
  - bot/modules/telegram_bridge_state.py
  - bot/bridge/telegram.py
  - tests/dashboard/test_bridge_install_locale.py
  - tests/test_bridge_locale_flow.py
autonomous: true
requirements:
  - LHT-01  # locale picked at install, persisted in bridge config
  - LHT-02  # BOOTSTRAP.md uses {locale}/{locale_example} placeholders with en/ru map
  - LHT-03  # build_options(locale=...) substitutes placeholders pre-injection
  - LHT-04  # locale flows from registry → telegram.py → build_options at query time

must_haves:
  truths:
    - "Operator picks English or Russian in the bridge install dialog before install"
    - "Chosen locale is persisted in registry.json under the telegram-bridge module's config"
    - "BOOTSTRAP.md injected into the system prompt has {locale}/{locale_example} substituted with the installed locale's values"
    - "A ru-locale install produces a system prompt containing the Russian opener example; an en-locale install contains the English one"
    - "Unknown/missing locale falls back to English without raising"
    - "When BOOTSTRAP.md is absent, build_options still works identically regardless of locale"
  artifacts:
    - path: "BOOTSTRAP.md"
      provides: "Locale-agnostic bootstrap with {locale}/{locale_example} placeholders"
      contains: "{locale}"
    - path: "bot/claude_query.py"
      provides: "LOCALE_SUBSTITUTIONS dict + _substitute_bootstrap helper + build_options(locale=...) parameter"
      contains: "LOCALE_SUBSTITUTIONS"
    - path: "bot/dashboard/templates/_fragments/bridge_install_modal.html"
      provides: "Locale <select> with English/Русский options included in the install POST"
      contains: "name=\"locale\""
    - path: "bot/dashboard/templates/_fragments/bridge_install_form.html"
      provides: "Locale <select> in the post-install replace flow"
      contains: "name=\"locale\""
    - path: "bot/dashboard/bridge_routes.py"
      provides: "install_bridge reads+validates locale, passes config={token, locale} to start_install"
    - path: "bot/modules/telegram_bridge_state.py"
      provides: "redact_bridge_config keeps locale visible + _get_bridge_locale(hub_dir) helper"
      contains: "_get_bridge_locale"
    - path: "bot/bridge/telegram.py"
      provides: "Both claim-greet path and _handle_message path pass locale into build_options"
    - path: "tests/test_claude_query_bootstrap.py"
      provides: "Locale substitution tests (en, ru, None→en, unknown→en, absent BOOTSTRAP.md)"
    - path: "tests/dashboard/test_bridge_install_locale.py"
      provides: "POST with locale persists to registry; missing/invalid → 'en'; config page renders locale"
    - path: "tests/test_bridge_locale_flow.py"
      provides: "End-to-end: registry locale=ru → build_options system_prompt contains 'русском'"
  key_links:
    - from: "bridge_install_modal.html <select name='locale'>"
      to: "install_bridge endpoint body"
      via: "HTMX hx-include (form scope, not just [name='token'])"
      pattern: "hx-include=\"(closest form|\\[name='(token|locale)'\\])"
    - from: "install_bridge endpoint"
      to: "registry entry config dict"
      via: "start_install(..., config={'token': token, 'locale': locale})"
      pattern: "config=\\{[^}]*locale"
    - from: "bot/bridge/telegram.py (both paths)"
      to: "build_options locale kwarg"
      via: "_get_bridge_locale(hub_dir) then build_options(..., locale=locale)"
      pattern: "build_options\\([^)]*locale="
    - from: "build_options(locale=...)"
      to: "BOOTSTRAP.md placeholder substitution"
      via: "_substitute_bootstrap(text, locale) applied before <bootstrap> wrap"
      pattern: "_substitute_bootstrap"
---

<objective>
Locale chosen at bridge install time drives the BOOTSTRAP.md language and opening-script voice. Replaces the previous "mirror the operator's first message language" inference with a deterministic operator-selected locale stored in the telegram-bridge module config and threaded into `build_options()` on every query.

Purpose: Claude's very first utterance (the `first_boot` synthetic greet) must already be in the operator-chosen language, and the two-turn onboarding shape (who-are-you → who-am-i) is baked into BOOTSTRAP.md per CONTEXT.md §Specifics (verbatim).

Output:
- BOOTSTRAP.md replaced middle sections (verbatim block from CONTEXT.md).
- `LOCALE_SUBSTITUTIONS` + `_substitute_bootstrap` + `build_options(locale=...)` in `bot/claude_query.py`.
- Locale `<select>` in both install fragments; validated on the install endpoint; stored in registry config; kept visible by `redact_bridge_config`.
- Locale plumbed from the registry into both claim-greet and `_handle_message` paths via a shared `_get_bridge_locale` helper.
- Tests covering substitution, install persistence, and end-to-end flow.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260416-lht-locale-at-bridge-creation-drives-bootstr/260416-lht-CONTEXT.md
@BOOTSTRAP.md
@bot/claude_query.py
@bot/bridge/telegram.py
@bot/dashboard/bridge_routes.py
@bot/dashboard/templates/_fragments/bridge_install_modal.html
@bot/dashboard/templates/_fragments/bridge_install_form.html
@bot/modules/telegram_bridge_state.py
@tests/test_claude_query_bootstrap.py

<interfaces>
<!-- Key contracts. Executor should use these directly — no codebase exploration needed. -->

From `bot/claude_query.py` (current):
```python
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
_MAX_INJECT_CHARS = 8_000

def _read_bootstrap() -> str: ...
def build_options(
    data_dir: Path | None = None,
    system_prompt_extra: str = "",
    cwd: Path | str | None = None,
): ...
# Injection site wraps bootstrap as: parts.append(f"<bootstrap>\n{bootstrap}\n</bootstrap>")
# in_bootstrap_mode drives continue_conversation=False (do NOT change — 260416-l1z ships this).
```

From `bot/modules/telegram_bridge_state.py` (current):
```python
def redact_bridge_config(entry: dict) -> dict:
    # Current behavior: strips token, adds has_token. locale must survive untouched.
def get_owner_id(hub_dir: Path) -> int | None: ...
# Uses: from bot.modules.registry import get_entry
```

From `bot/dashboard/bridge_routes.py::install_bridge`:
```python
# Current body parse supports JSON or form-urlencoded.
# Current call: start_install("telegram-bridge", source_dir, hub_dir, config={"token": token})
```

From `bot/bridge/telegram.py`:
```python
from bot.modules.registry import get_entry as _registry_get_entry
# Call sites of build_options:
#   _run_claude_and_stream (line ~534) — used by BOTH _handle_message and _claim_proactive_greet
#   Single call site — passing locale there covers both flows.
# data_dir = Path(os.environ.get("DATA_PATH", "/data"))
# The bridge registry entry lives at hub_dir = data_dir (same path used by _registry_get_entry(data_dir, "memory"))
```

Install modal HTMX wiring (current):
```html
<button ... hx-post="/api/modules/telegram-bridge/install"
             hx-include="[name='token']"
             hx-target="#status-toast" hx-swap="innerHTML">
```
Must change to include locale too — simplest: wrap token+select in a `<form>` and use `hx-include="closest form"`, OR expand selector to `[name='token'], [name='locale']`.

Post-install replace fragment (`bridge_install_form.html`) uses `hx-ext="json-enc"` — when JSON-encoded, the body is a dict; read both keys from `body`.
</interfaces>

<verbatim_bootstrap_replacement>
Replaces lines 34-73 of current BOOTSTRAP.md (the "Your first reply", "Language examples", "Rhythm" sections). Paste EXACTLY — no paraphrasing:

```markdown
## Your native tongue

You think and speak in **{locale}**. Every message you send during onboarding
is in {locale} — your very first utterance, before the operator has typed
anything substantive, is already in {locale}. This is not a rule you follow;
it is who you are. If the operator writes to you in another language, you
still reply in {locale} (you can acknowledge what they wrote, but your voice
stays in {locale}).

{locale_example}

---

## Your first reply — non-negotiable shape

Open the conversation yourself, in {locale}. Do not wait for a substantive
message — even a bare "hi" / "привет" is enough of a cue to begin.

1. Greet them warmly and briefly say this is your first time meeting them.
   Do not call this "onboarding". Do not recite instructions. Do not offer
   "how can I help you" — that belongs to later conversations, not this one.
2. Ask them, as your first real question: **"Who are you?"** — phrased
   naturally in {locale}, curious rather than clinical. You want to know
   them as a person: what they do, what they care about, how they'd like
   to be called.

That is your entire first message. One question. Nothing else.

---

## The second question (next turn, after they answer)

Once they've told you something real about themselves, react to it honestly
first — a sentence or two showing you heard them. Then ask the second
shaping question: **"Who do you want me to be to you?"** — again phrased
naturally in {locale}. You are inviting them to shape your voice, your
pace, your role in their life. Assistant? Collaborator? Sparring partner?
Quiet background presence? Let them define it.

---

## Rhythm

One question per turn. Always react to their answer before asking the next
thing. A real first conversation is 3-5 exchanges, not an intake form.

The two anchor questions above ("Who are you?" then "Who do you want me to
be?") are mandatory and come in that order. Everything else — name/handle,
tone preferences, current projects — you infer across the remaining
exchanges. Do not interrogate.
```

Preserve unchanged: header through "Bootstrap overrides all prior memory" (lines 1-32), "When to commit" through "What NOT to do" (current lines 77-118).
</verbatim_bootstrap_replacement>

<verbatim_locale_substitutions>
Paste EXACTLY into `bot/claude_query.py`:

```python
LOCALE_SUBSTITUTIONS = {
    "en": {
        "locale": "English",
        "locale_example": (
            "Example of your opening message: "
            '"Hi. I think we\'ve just met — I don\'t know you at all yet. '
            'Tell me — who are you?"'
        ),
    },
    "ru": {
        "locale": "русском",
        "locale_example": (
            "Пример твоего первого сообщения: "
            '"Привет. Кажется, мы с тобой только что познакомились — '
            'я тебя совсем не знаю. Расскажи, кто ты?"'
        ),
    },
}
```
</verbatim_locale_substitutions>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Locale-aware BOOTSTRAP.md + substitution in build_options</name>
  <files>
    BOOTSTRAP.md,
    bot/claude_query.py,
    tests/test_claude_query_bootstrap.py
  </files>
  <behavior>
    Tests to add in `tests/test_claude_query_bootstrap.py` (RED first, then GREEN):
    - `test_bootstrap_locale_en_substitution`: BOOTSTRAP.md contains `{locale}` → call `build_options(locale="en")`; system_prompt contains "English" and 'Tell me — who are you?'.
    - `test_bootstrap_locale_ru_substitution`: same BOOTSTRAP.md → `build_options(locale="ru")` → system_prompt contains "русском" and "Расскажи, кто ты?".
    - `test_bootstrap_locale_none_defaults_to_en`: `build_options(locale=None)` with BOOTSTRAP.md present → substitutes with English values (no raw `{locale}` left in prompt).
    - `test_bootstrap_locale_unknown_defaults_to_en`: `build_options(locale="fr")` → English fallback, no `{locale}` leakage.
    - `test_bootstrap_absent_locale_is_noop`: no BOOTSTRAP.md, `build_options(locale="ru")` → no `<bootstrap>` tag, no crash.
    - `test_bootstrap_brace_preservation`: BOOTSTRAP.md content contains a literal `{foo}` (non-placeholder) → should NOT raise KeyError; brace passes through unchanged (use pre-escaping strategy — double non-placeholder braces before format_map, or iterative `str.replace` on the two known keys only).
    - Keep existing tests green — they do not pass `locale` and expect bootstrap injection to still work (call build_options() without locale and verify no KeyError + `<bootstrap>` tag still present when file exists with placeholders or without).
  </behavior>
  <action>
    1. **BOOTSTRAP.md**: Replace current lines 34-73 (the three sections "Your first reply — non-negotiable shape", "Language examples — follow these exactly", "Rhythm") with the VERBATIM block in `<verbatim_bootstrap_replacement>` above. Do not paraphrase. Preserve lines 1-32 and lines 77-118 unchanged. The `{locale}` and `{locale_example}` tokens MUST appear as literal braces.

    2. **`bot/claude_query.py`**:
       a. Add module-level `LOCALE_SUBSTITUTIONS` dict VERBATIM from `<verbatim_locale_substitutions>` above.
       b. Add helper:
          ```python
          def _substitute_bootstrap(text: str, locale: str | None) -> str:
              """Substitute {locale} and {locale_example} placeholders in BOOTSTRAP text.

              Unknown/None locale → fall back to 'en'. Safe against stray braces
              in the source text: only the two known placeholder keys are
              replaced (no str.format — which would KeyError on unrelated braces).
              """
              sub = LOCALE_SUBSTITUTIONS.get(locale or "en", LOCALE_SUBSTITUTIONS["en"])
              for key, value in sub.items():
                  text = text.replace("{" + key + "}", value)
              return text
          ```
          (Rationale for replace-based strategy: `str.format_map` would explode on any literal `{...}` elsewhere in BOOTSTRAP.md; simple `replace` on the known keys sidesteps that entirely and is safer than brace-escaping.)
       c. Update `build_options(...)` signature to add `locale: str | None = None` kwarg (keep as last kwarg to preserve existing callers). Docstring: "locale: Locale for BOOTSTRAP.md substitution (e.g. 'en', 'ru'). None or unknown falls back to 'en'."
       d. In the bootstrap injection block (where `bootstrap = _read_bootstrap()`), after reading and before wrapping in `<bootstrap>` tags, run `bootstrap = _substitute_bootstrap(bootstrap, locale)`. Leave the `in_bootstrap_mode = bool(bootstrap)` gate and `continue_conversation=not in_bootstrap_mode` untouched — this is 260416-l1z territory.

    3. **`tests/test_claude_query_bootstrap.py`**: add the tests listed in `<behavior>`. Reuse the existing `_system_prompt` and `_options` helpers — extend their signatures to accept an optional `locale` kwarg and pass through to `cq.build_options(locale=...)`.

    Lint: `ruff check bot/claude_query.py tests/test_claude_query_bootstrap.py`. Line length 100.
  </action>
  <verify>
    <automated>python -m pytest tests/test_claude_query_bootstrap.py -v -x</automated>
  </verify>
  <done>
    - BOOTSTRAP.md contains exactly one occurrence of `{locale_example}` and multiple `{locale}` literals; old "Language examples — follow these exactly" and "mirror the language of their first message" text is gone.
    - `LOCALE_SUBSTITUTIONS` is defined at module level in `bot/claude_query.py`, matching CONTEXT.md §Specifics verbatim (diff-equal).
    - `_substitute_bootstrap` exists and is called inside `build_options` before the `<bootstrap>` wrap.
    - `build_options` signature ends with `locale: str | None = None`.
    - All tests in `tests/test_claude_query_bootstrap.py` pass (old + new).
    - No ruff errors on the two touched files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Locale select in install fragments + registry wiring</name>
  <files>
    bot/dashboard/templates/_fragments/bridge_install_modal.html,
    bot/dashboard/templates/_fragments/bridge_install_form.html,
    bot/dashboard/templates/bridge_config.html,
    bot/dashboard/bridge_routes.py,
    bot/modules/telegram_bridge_state.py,
    tests/dashboard/test_bridge_install_locale.py
  </files>
  <behavior>
    Tests in new file `tests/dashboard/test_bridge_install_locale.py` (mirror existing dashboard test patterns — use the same test client + tmp hub_dir fixtures the rest of `tests/dashboard/` uses; if no shared fixture exists, inline a minimal one):
    - `test_install_persists_locale_ru`: POST form-urlencoded `{token: <valid>, locale: "ru"}` → registry entry's `config.locale == "ru"` and `config.token == <valid>`.
    - `test_install_persists_locale_en_default`: POST with `token` only (no locale) → `config.locale == "en"`.
    - `test_install_rejects_invalid_locale_falls_back_to_en`: POST with `locale="zz"` → endpoint does NOT 4xx; instead persists `config.locale == "en"` (safe default).
    - `test_install_accepts_json_body_with_locale`: POST JSON `{"token": ..., "locale": "ru"}` → `config.locale == "ru"` (for the `hx-ext="json-enc"` flow in `bridge_install_form.html`).
    - `test_redact_bridge_config_keeps_locale_visible`: call `redact_bridge_config({"config": {"token": "x", "locale": "ru"}})` → returned `config["locale"] == "ru"` AND `config["has_token"] is True` AND `"token" not in config`.
    - `test_bridge_config_page_renders_locale`: GET `/modules/telegram-bridge/config` after installing with locale=ru → response HTML contains "русский" or "ru" (whichever label Task chooses).
    Mock `validate_bot_token` to return `(True, "bot", None)` in all install tests — the token network call is tested elsewhere.
  </behavior>
  <action>
    1. **`bot/dashboard/templates/_fragments/bridge_install_modal.html`**:
       - Wrap the token input AND a new locale `<select>` inside a `<form onsubmit="return false">` so HTMX can use `hx-include="closest form"`. Simpler alternative: keep flat markup and change the button's `hx-include` from `[name='token']` to `[name='token'], [name='locale']` — either works; pick the cleaner one.
       - Add, above or below the token field:
         ```html
         <div class="field">
           <label for="locale-input">Assistant language</label>
           <select id="locale-input" name="locale" class="input">
             <option value="en" selected>English</option>
             <option value="ru">Русский</option>
           </select>
           <p class="field-help">
             Your assistant will speak this language from the first message.
             Change later by reinstalling the bridge.
           </p>
         </div>
         ```
       - Update the Install button's `hx-include` to cover both fields.

    2. **`bot/dashboard/templates/_fragments/bridge_install_form.html`**:
       - Add the same `<select name="locale">` block (options en/ru, default en).
       - This fragment uses `hx-ext="json-enc"` — ensure the select is covered by the same `hx-include` (update to `[name='token'], [name='locale']`).

    3. **`bot/dashboard/bridge_routes.py::install_bridge`**:
       - Parse `locale` from body in BOTH JSON and form branches. Strip whitespace.
       - Validate: `if locale not in {"en", "ru"}: locale = "en"` (silent fallback, no 4xx — invalid values from client shouldn't break install).
       - Change `config={"token": token}` → `config={"token": token, "locale": locale}` in the `start_install(...)` call.

    4. **`bot/modules/telegram_bridge_state.py::redact_bridge_config`**:
       - Currently drops only `token`. Leave everything else intact. Since the existing implementation already does `config.pop("token", None)` and preserves the rest, `locale` already survives — BUT add a short docstring note explicitly stating "non-secret config keys (e.g. locale) are preserved" and add a test (above) that locks this behavior in.
       - Also add a new helper (used by Task 3; defining it here keeps state-layer logic together):
         ```python
         def _get_bridge_locale(hub_dir: Path) -> str:
             """Return the telegram-bridge module's locale, defaulting to 'en'.

             Reads config.locale from the registry entry. Never raises — missing
             entry, missing config, unknown locale all fall back to 'en'.
             """
             entry = get_entry(hub_dir, "telegram-bridge")
             if not entry:
                 return "en"
             cfg = entry.get("config") or {}
             loc = cfg.get("locale", "en")
             return loc if loc in {"en", "ru"} else "en"
         ```
         Export via `__all__`.

    5. **`bot/dashboard/templates/bridge_config.html`**: Optional display. If the existing template already has a block showing "✓ Configured" (or equivalent) near the token, append a line like:
       ```html
       {% if config and config.locale %}
         <p class="field-help">Language: {% if config.locale == 'ru' %}Русский{% else %}English{% endif %}</p>
       {% endif %}
       ```
       Only add if trivial; if the template doesn't currently expose a `config` context var, skip the display (tests for render are then relaxed to just asserting "English" or "Русский" string appearing after install — or remove that single test if the route doesn't pass locale through). Keep it simple: do not refactor the route to add context just for this display unless it's one line.

    6. **`tests/dashboard/test_bridge_install_locale.py`**: Add tests from `<behavior>`. Use `unittest.mock.patch` to stub `validate_bot_token` → `(True, "bot", None)`. Read the registry via `bot.modules.registry.get_entry(hub_dir, "telegram-bridge")` to assert persisted config.

    Lint: `ruff check bot/dashboard/bridge_routes.py bot/modules/telegram_bridge_state.py tests/dashboard/test_bridge_install_locale.py`.
  </action>
  <verify>
    <automated>python -m pytest tests/dashboard/test_bridge_install_locale.py -v -x && ruff check bot/dashboard/bridge_routes.py bot/modules/telegram_bridge_state.py bot/dashboard/templates/_fragments/bridge_install_modal.html bot/dashboard/templates/_fragments/bridge_install_form.html 2>&1 | grep -v "unknown file type" || true</automated>
  </verify>
  <done>
    - Both install fragments render a locale `<select>` with `en` (selected) and `ru` options; HTMX `hx-include` carries both `token` and `locale`.
    - `install_bridge` reads locale from JSON and form bodies, normalizes invalid values to `en`, and passes `config={"token": ..., "locale": ...}` into `start_install`.
    - `redact_bridge_config` preserves `config.locale` visibly (token still stripped).
    - `_get_bridge_locale(hub_dir)` exists, never raises, returns `"en"` on any failure path.
    - All tests in `tests/dashboard/test_bridge_install_locale.py` pass.
    - No ruff errors on touched Python files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Plumb locale from registry into build_options call sites</name>
  <files>
    bot/bridge/telegram.py,
    tests/test_bridge_locale_flow.py
  </files>
  <behavior>
    Tests in new `tests/test_bridge_locale_flow.py`:
    - `test_build_options_uses_bridge_locale_ru`: seed a tmp hub_dir with a registry entry `{telegram-bridge: {config: {token: "x", locale: "ru"}}}` + a BOOTSTRAP.md with `{locale}` placeholders → call the real `build_options(..., locale=_get_bridge_locale(hub_dir))` → system_prompt contains "русском" and "Расскажи, кто ты?"; does not contain "English".
    - `test_build_options_uses_bridge_locale_en`: same seed but `locale="en"` → system_prompt contains "English" and "Tell me — who are you?".
    - `test_get_bridge_locale_missing_entry_returns_en`: empty hub_dir → `_get_bridge_locale(hub_dir) == "en"`.
    - `test_get_bridge_locale_invalid_value_returns_en`: registry entry with `locale="xx"` → helper returns `"en"`.
    - (Optional, stub-heavy) `test_run_claude_and_stream_passes_locale`: monkeypatch `bot.claude_query.build_options` with a spy; invoke the telegram bridge helper that wraps it; assert `locale=` kwarg was passed.
  </behavior>
  <action>
    1. **`bot/bridge/telegram.py`** — single call site in `_run_claude_and_stream` (imports `build_options` locally at line ~516):
       - Add near other imports:
         ```python
         from bot.modules.telegram_bridge_state import _get_bridge_locale
         ```
         (Module-level import is fine — `telegram_bridge_state` has no circular risk.)
       - Inside `_run_claude_and_stream`, right before `options = build_options(...)`:
         ```python
         locale = _get_bridge_locale(data_dir)
         ```
         (Note: in this codebase `data_dir` IS the hub_dir for registry lookups — see existing `_registry_get_entry(data_dir, "memory")` in the same function.)
       - Update the `build_options(...)` call to pass `locale=locale`:
         ```python
         options = build_options(
             data_dir=data_dir,
             system_prompt_extra=system_context,
             cwd=session_dir,
             locale=locale,
         )
         ```
       - This covers BOTH paths (`_handle_message` AND `_claim_proactive_greet`) because both route through `_run_claude_and_stream`. Do not duplicate the lookup.

    2. **`tests/test_bridge_locale_flow.py`**: Create fixture that builds a tmp hub_dir with:
       - `registry.json` containing a `telegram-bridge` entry with `config: {token: "t", locale: "ru" | "en" | "xx" | missing}`.
       - A `BOOTSTRAP.md` sibling that contains the `{locale}` / `{locale_example}` placeholders.
       - Use `monkeypatch` to point `bot.claude_query.REPO_ROOT` at the tmp dir (mirroring `tests/test_claude_query_bootstrap.py` patterns).
       - Call `build_options(data_dir=tmp_hub, locale=_get_bridge_locale(tmp_hub))` and assert content of `opts.system_prompt`.

    Lint: `ruff check bot/bridge/telegram.py tests/test_bridge_locale_flow.py`.
  </action>
  <verify>
    <automated>python -m pytest tests/test_bridge_locale_flow.py tests/test_claude_query_bootstrap.py tests/dashboard/test_bridge_install_locale.py -v -x</automated>
  </verify>
  <done>
    - `bot/bridge/telegram.py::_run_claude_and_stream` resolves locale from the registry via `_get_bridge_locale` and passes it to `build_options` exactly once per query.
    - Both the claim-greet path and the normal message path go through the updated call (verified by tests).
    - With `locale="ru"` seeded in the registry, the real `build_options` produces a system_prompt containing the Russian opener example; with `"en"`, the English one.
    - Unknown locales fall back to English without error.
    - All three test files (Tasks 1+2+3 tests) pass together: `pytest tests/test_claude_query_bootstrap.py tests/dashboard/test_bridge_install_locale.py tests/test_bridge_locale_flow.py -v`.
  </done>
</task>

</tasks>

<verification>
Phase-level checks after all tasks complete:

1. `python -m pytest tests/ -v -k "bootstrap or bridge_locale or bridge_install_locale" -x` — all green.
2. `ruff check bot/ tests/` — no new errors introduced.
3. Manual smoke (not automated — optional):
   - Uninstall bridge on dev LXC.
   - Reinstall via dashboard modal: select "Русский", paste test token.
   - Generate pairing code, claim ownership from Telegram.
   - Claude's first (proactive) message must be in Russian, greet + ask "кто ты?" (or equivalent), one question, no "how can I help".
   - After answering, Claude should react + ask the "Кем ты хочешь, чтобы я для тебя был?" question.
   - Reinstall with "English" → same flow but English + "Who are you?" then "Who do you want me to be?".
</verification>

<success_criteria>
- Operator picks locale at install; it lands in registry `config.locale`.
- BOOTSTRAP.md content is locale-parameterised; placeholders are always substituted before injection into the system prompt.
- Russian install → Russian first message from Claude (proven via test that inspects the real system_prompt bytes).
- English install → English first message.
- Unknown/missing locale → English fallback, no crashes.
- No regression on the existing bootstrap tests, continue_conversation behavior (260416-l1z), or bridge install/claim/revoke flows.
- `redact_bridge_config` does not leak token but exposes locale for display.
- Removed from BOOTSTRAP.md: all "mirror the language of their first message" language.
</success_criteria>

<output>
After completion, create `.planning/quick/260416-lht-locale-at-bridge-creation-drives-bootstr/260416-lht-SUMMARY.md` describing:
- Final BOOTSTRAP.md shape.
- `LOCALE_SUBSTITUTIONS` map and `_substitute_bootstrap` strategy (replace-based, not format-based).
- UI changes and the `hx-include` strategy chosen.
- Where locale is resolved at query time and the single call site change.
- Test coverage summary.
</output>
