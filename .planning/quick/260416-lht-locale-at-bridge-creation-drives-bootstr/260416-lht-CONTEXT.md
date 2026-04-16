# Quick Task 260416-lht: locale at bridge creation drives bootstrap language + who-are-you then who-am-i opening script — Context

**Gathered:** 2026-04-16
**Status:** Ready for planning (decisions locked by user approval)

<domain>
## Task Boundary

Two coupled changes:

1. **Locale at bridge install time.** Operator picks a locale (`en` / `ru`, extendable later) in the bridge install dialog. Stored in bridge module config. Fed into the system prompt so Claude's *first* utterance is in that language — no more "mirror the user's first message" inference.

2. **Opening script shape.** First two real turns follow the pattern confirmed by research (OpenClaw, Letta, ChatGPT custom instructions, Replika, Pi.ai): user-identity first (**"Who are you?"**), assistant-identity second (**"Who do you want me to be?"**). One question per turn, split across two turns with a reaction in between.

</domain>

<decisions>
## Implementation Decisions

### Locale is a bridge-config field
- Add `locale` (str, default `"en"`) to telegram-bridge module config.
- Render as a `<select>` in both `bridge_install_modal.html` AND `bridge_install_form.html`. Options: `English (en)`, `Русский (ru)`. Default selected: `en`. Operator-editable later via the config page.
- Persisted in `registry.json` under the module's `config` dict, same path as `token`.
- Propagated from registry → supervisor → `bot.modules_runtime.telegram_bridge.on_start(config)` → bridge_state (or module-instance memory) → `claude_query.build_options()` when building each user's system prompt.

### BOOTSTRAP.md uses placeholders
- New sections replace lines 34-73 (existing "Your first reply" + "Language examples" + "Rhythm" sections) with the approved draft (see §Specifics).
- Two placeholder tokens: `{locale}` and `{locale_example}`. Substituted at read-time by `claude_query._read_bootstrap()` (or a new helper) before injection.
- The SUBSTITUTION VALUES live in a new dict `LOCALE_SUBSTITUTIONS` in `bot/claude_query.py` (or a small new `bot/locale.py` — planner's call). Map:
  - `en` → `{locale: "English"}`, `{locale_example: 'Example of your opening message: "Hi. I think we've just met — I don\'t know you at all yet. Tell me — who are you?"'}`
  - `ru` → `{locale: "русском"}`, `{locale_example: 'Пример твоего первого сообщения: "Привет. Кажется, мы с тобой только что познакомились — я тебя совсем не знаю. Расскажи, кто ты?"'}`
- Unknown locale → fallback to `en`.

### Locale flows to claude_query at query build time
- `build_options(...)` gains a `locale: str | None = None` parameter.
- When `locale` provided → substitute placeholders in BOOTSTRAP content before wrapping in `<bootstrap>` tags.
- When `locale` is `None` (identity onboarding finished, or caller didn't pass) → fall back to `en` substitution. BOOTSTRAP.md should not exist in that case, so substitution is moot.
- Caller (`bot/bridge/telegram.py`) pulls locale from the bridge module's config (registry entry) or from state.json, passes it into `build_options`.

### Locale at onboarding is FIXED for the session
- Once locale is set at install, that's the identity Claude writes USER.md/SOUL.md in.
- If operator later wants to switch, they reset.

### /identity concept stays gone
- No per-user override. This is a single-operator bot.

### Tests
- `tests/test_claude_query_bootstrap.py` — add tests for locale substitution (en path + ru path + unknown fallback + None).
- `tests/dashboard/` — snapshot test for bridge install modal rendering the new `<select>`; POST test confirming `locale` is persisted into registry config.
- Update any existing assertions about BOOTSTRAP.md content (language-mirror examples are gone).

### Bridge install dialog wiring
- Modal HTML adds `<select name="locale">`. HTMX `hx-include` picks it up (already includes `[name='token']`; change to a form or add `[name='locale']`).
- `install_bridge` endpoint reads both `token` and `locale` from the body, passes both into `start_install(config=...)`.
- Existing validator `validate_bot_token` untouched.

### Claude's Discretion
- Whether to introduce a tiny new module `bot/locale.py` or inline the substitutions in `claude_query.py`. Both fine — prefer the one that adds fewer files. Recommendation: inline (1 dict + 1 helper in `claude_query.py`).
- Exact placeholder syntax. Prefer braces (`{locale}`) not Jinja since `claude_query._read_bootstrap` is plain-text I/O, not a template engine.
- Whether to display the chosen locale in the bridge config page after install (next to "✓ Configured"). Nice-to-have; include if trivial.

</decisions>

<specifics>
## Specific Ideas

### Approved BOOTSTRAP.md replacement (verbatim)

Replace the three sections "Your first reply", "Language examples", "Rhythm" (current lines 34-73 of BOOTSTRAP.md) with this block. Keep sections before and after ("You just came online", "Bootstrap overrides all prior memory", "When to commit", "Deleting this file", "What NOT to do") unchanged.

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

### Locale substitutions

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

</specifics>

<canonical_refs>
## Canonical References

- Current `BOOTSTRAP.md` — repo root
- `bot/claude_query.py` — injection site, `build_options` + `_read_bootstrap`
- `bot/bridge/telegram.py` — calls `build_options`; pulls config from registry entries
- `bot/modules_runtime/telegram_bridge.py` — module entry; receives `config` dict on start
- `bot/dashboard/bridge_routes.py` — install endpoint reads token from body, now also reads locale
- `bot/dashboard/templates/_fragments/bridge_install_modal.html` — add locale `<select>`
- `bot/dashboard/templates/_fragments/bridge_install_form.html` — add locale `<select>` (post-install replace flow; lower priority)
- `bot/dashboard/module_routes.py` — config GET route, may need to show current locale if we display it
- Research: 260416-gl8 RESEARCH.md + current conversation turn

</canonical_refs>
