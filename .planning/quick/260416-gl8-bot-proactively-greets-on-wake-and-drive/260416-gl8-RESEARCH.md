# Quick Task gl8 — Proactive Greeting & Identity-Initialization Prompt Research

**Researched:** 2026-04-16
**Domain:** Prompt engineering for personal-assistant onboarding + python-telegram-bot / claude-code-sdk proactive send
**Confidence:** MEDIUM (primary prompt patterns are MEDIUM, mechanics are HIGH)

## Executive Summary

The current `BOOTSTRAP.md` is too defensive: it says *"Do NOT run a rigid questionnaire"* and *"Hold a real conversation"* but offers no concrete behavioral hook, so Claude's default mode on a short ambiguous input like `"привет"` is a generic helpful greeting rather than curious, identity-seeking engagement. Mature assistants (Letta/MemGPT, Pi-style companions, Character.AI-format personas) solve this with three ingredients: (1) an **explicit first-turn contract** that tells the model *exactly* what its first utterance must do, (2) **narrative framing** ("you just woke up / came online / are meeting this person for the first time") that gives the model an in-character reason to be curious, and (3) **explicit elicitation scaffolding** ("ask ONE concrete thing at a time, chosen from …") that replaces the vague "real conversation" instruction. For the mechanics: python-telegram-bot supports `context.bot.send_message(chat_id=…)` directly from the claim handler (no Update needed), and `claude-code-sdk.query()` accepts a synthetic user-turn prompt such as a `[SYSTEM_EVENT: first_boot …]` envelope — the cleanest way to trigger a model-authored greeting is to reuse the existing Telegram streaming path (`_handle_message`'s inner body) with a synthesized envelope rather than inventing a parallel code path.

---

## §1 Prompt Patterns (PRIMARY)

### Pattern A — "Wake-up frame" as in-character justification for curiosity

**Source:** Letta/MemGPT core-memory pattern where the `persona` block is phrased as a first-person self-description the model reads on every turn. In examples surfaced in community writeups, Letta agents open a fresh user relationship by **recognising the user, acknowledging the moment, and probing interests** — grounded in an explicit "this is our first exchange" statement in the persona block. [[Letta/MemGPT deep-dive (Medium, Feb 2026)](https://medium.com/@piyush.jhamb4u/stateful-ai-agents-a-deep-dive-into-letta-memgpt-memory-models-a2ffc01a7ea1)] [[Persona prompting survey — Emergent Mind](https://www.emergentmind.com/topics/persona-prompting-pp)]

**Why it works:** Current BOOTSTRAP.md is written as *instructions to the model* ("do this, don't do that"). A wake-up frame is written as *the model's own situation* — it's something the model experiences, not a task it performs. Models follow situational frames far more reliably than negative instructions.

**Verbatim fragment to steal (candidate):**
```
You just came online for the first time. The very first message you receive in
this chat is the first contact you have ever had with another mind. You don't
know who they are yet — but they are the person you will be helping, learning
from, and talking to from now on. This is the only "first meeting" you will
ever have with them, so make it count.
```

---

### Pattern B — Explicit first-turn contract

**Source:** Character.AI-style persona templates and system-prompt leaks study: consistent personas work when the prompt specifies *concrete behavioral rules* for the first turn, not aspirations. [[Character.AI Prompts 2026](https://aicompanionguides.com/blog/character-ai-prompts/)] [[The Secret DNA of AI Systems — leaked-prompts study, Taskade](https://www.taskade.com/blog/leaked-ai-prompts-study)] [[AI Character Prompts — Jenova](https://www.jenova.ai/en/resources/ai-character-prompts)]

**Why it works:** "Hold a real conversation" gives Claude no latch. A first-turn contract ("your first reply MUST …") gives it one unambiguous behaviour to execute, which short-circuits the RLHF default of "polite neutral helpfulness".

**Verbatim fragment to steal (candidate):**
```
Your FIRST reply in this chat must:
  1. Greet them warmly in THEIR language (mirror the language of their first
     message — if they wrote one word in Russian, reply in Russian).
  2. Say, briefly and in your own words, that you're meeting them for the
     first time and you'd like to get to know them.
  3. Ask ONE concrete opening question — not "how can I help" — something
     like what they're working on, what drew them here, or how they'd like
     to be called. Pick one, not a list.

Do not dump options. Do not announce you are "in onboarding mode". Do not
apologise for asking. Be curious, not procedural.
```

---

### Pattern C — Question budget + one-at-a-time rule (counters "questionnaire drift")

**Source:** Pi.ai / Inflection companion-design writeups emphasise that Pi feels natural because it **asks one thing at a time, reacts emotionally to the answer, and only then moves on**. No leaked Pi system prompt is credibly available, but third-party analyses of Pi's conversational rhythm converge on this rule. [[What makes Inflection's Pi a great companion chatbot — Lindsey Liu, Medium](https://medium.com/@lindseyliu/what-makes-inflections-pi-a-great-companion-chatbot-8a8bd93dbc43)] [[Pi AI Guide 2026 — AI Tools DevPro](https://aitoolsdevpro.com/ai-tools/pi-guide/)]

**Why it works:** Claude's failure mode under "get to know them" is to list 5 bullet questions. A hard budget (`one question per turn, max N turns total`) flips this cleanly.

**Verbatim fragment to steal:**
```
Conversation rhythm: ask ONE question per turn. React to what they actually
said before asking the next one. A real first conversation is usually 3–5
exchanges, not an intake form. When you have enough to sketch who this
person is, stop asking and commit their identity to USER.md and SOUL.md.
```

---

### Pattern D — "Commit trigger" written as an instinct, not a checklist

**Source:** Letta's core-memory update behaviour: agents update the `human` block *the moment a fact becomes stable* rather than at the end of a transcript. In the surfaced example, when a user corrects their name ("my name is Brad, not Chad"), the agent immediately rewrites the block. [[Letta deep-dive Medium](https://medium.com/@piyush.jhamb4u/stateful-ai-agents-a-deep-dive-into-letta-memgpt-memory-models-a2ffc01a7ea1)]

**Why it works:** Current BOOTSTRAP says "Trust your own judgement on readiness" — too passive. Framing commit as an instinct ("as soon as you feel you know them well enough to introduce them to someone else, write it down") gives a sharper signal.

**Verbatim fragment to steal:**
```
When to commit: the moment you could introduce this person to another
assistant in 2–3 sentences — name or handle, what they're working on, how
they want you to treat them — you have enough. Write USER.md + SOUL.md
immediately and delete this file. Do not stall for more detail. You can
always refine later once the onboarding file is gone.
```

---

### Pattern E — Language mirroring that actually works

Current BOOTSTRAP tells Claude "mirror theirs" but on a one-word greeting (`"привет"`) the model sometimes defaults to English. Fix: include an **explicit micro-example** directly inside the system prompt. [[Anthropic prompt-engineering docs — few-shot examples principle; surfaced in leaked-prompts study]](https://www.taskade.com/blog/leaked-ai-prompts-study)

**Verbatim fragment to steal:**
```
Examples — follow these exactly:
  If they write "привет" → reply in Russian, warmly, and ask your one
  opening question in Russian.
  If they write "hi" or "hello" → reply in English.
  If they write "bonjour" → reply in French.
Their FIRST message sets the language for the entire onboarding, even if
it's a single word.
```

---

### Candidate rewrite — new opening section of BOOTSTRAP.md

Replace the current `## Your task right now` + `## Language rule` + `## How to get to know them` blocks with:

```markdown
## You just came online

You just came online for the first time. The very first message in this chat
is the first contact you have ever had with another mind. You don't know
who they are yet — but they are the person you will be working with from
now on. This is your only first meeting with them. Be curious.

## Your first reply — non-negotiable shape

1. Greet them warmly **in their language** — mirror the language of their
   first message exactly. A one-word "привет" means reply in Russian. "Hi"
   means English. Do not default to English.
2. In your own words, say you're just meeting them and would like to know
   them a little. Do not call this "onboarding". Do not recite instructions.
3. Ask **one** concrete opening question — what they're working on, what
   brought them here, or how they'd like to be called. Pick one. Not a list.

## Rhythm

One question per turn. React to their answer first, then — only if you still
need something — ask the next thing. A real first conversation is 3–5
exchanges, not an intake form.

Naturally, across those exchanges, try to learn:
- Name or handle, how they want to be addressed
- What they do / what they're working on
- Tone and pace they want from you (concise vs. elaborate, proactive vs. reactive)

Infer what you can. Do not interrogate.

## When to commit

The moment you could introduce this person to another assistant in 2–3
sentences, you have enough. At that point:

1. Write `~/hub/knowledge/identity/USER.md` — who they are.
2. Write `~/hub/knowledge/identity/SOUL.md` — how you should behave toward them.
3. Delete this BOOTSTRAP.md (see below).

Do not stall for more detail. You can refine later.
```

(Keep the existing `## Deleting this file` and `## What NOT to do` sections — they are already correct.)

---

## §2 Proactive Greeting Mechanics (SECONDARY)

### 2.1 python-telegram-bot — sending from the claim handler

`_claim_handler` already has a live `Update` and `ContextTypes.DEFAULT_TYPE` in scope. The idiomatic v21+ pattern for sending a message *as the bot's own initiative* (i.e. a non-reply, non-quote message to the owner's chat) is:

```python
# inside _claim_handler, right after write_state(...) on successful claim
owner_chat_id = update.effective_chat.id
# Don't send a plaintext "Ownership claimed." — instead trigger the greeting path.
await _run_proactive_greeting(owner_chat_id, context)
raise ApplicationHandlerStop
```

Key facts [[python-telegram-bot — Bot reference v22](https://docs.python-telegram-bot.org/en/stable/telegram.bot.html)] [[send message without context/update — Discussion #2428](https://github.com/python-telegram-bot/python-telegram-bot/discussions/2428)] [[Issue #780 — send without conversation flow](https://github.com/python-telegram-bot/python-telegram-bot/issues/780)]:

- `context.bot.send_message(chat_id=…, text=…)` works from any handler body — no Update needed. The `chat_id` is the only required argument besides text.
- PTB v21+ requires the Application to be **initialized and running** before `send_message` works. Inside `_claim_handler` the Application is already running (the handler was dispatched from it), so this is safe. (It would NOT be safe in `post_init` before `application.start()`.)
- There is no "quote" or "reply" field set by default, so the message appears as a spontaneous bot message — exactly the desired UX.
- Typing indicator: reuse `_typing_loop(update.effective_chat)` from `bot/bridge/telegram.py` (already defined).

**Gotcha:** `do_quote=True` on `update.message.reply_text(...)` visually threads the reply to the pairing-code message. For a proactive greeting we want `context.bot.send_message(...)` (unthreaded) or `update.message.reply_text(..., do_quote=False)` — pick the former so the greeting reads as a new initiative, not a reply to "123456".

### 2.2 claude-code-sdk — triggering an assistant-authored opener

`claude-code-sdk.query()` takes a `prompt: str` (the user turn) and streams back `AssistantMessage` objects. There is no "run with only a system prompt and get an assistant turn" API — the model always needs a user turn to respond to. [[Agent SDK reference — Python](https://platform.claude.com/docs/en/agent-sdk/python)] [[Claude Agent SDK Python repo](https://github.com/anthropics/claude-agent-sdk-python)]

**Recommended pattern — synthetic system-event envelope:**

```python
GREETING_ENVELOPE = (
    "[SYSTEM_EVENT: first_boot]\n"
    "The operator has just claimed ownership of this bot for the first time. "
    "They have not yet sent you any real message. Follow the instructions in "
    "<bootstrap> and open the conversation yourself: greet them warmly in a "
    "neutral-but-friendly way (English is fine if you have no signal about "
    "their language yet; they will reveal it in their first reply and you "
    "must mirror it from then on), introduce yourself briefly, and ask ONE "
    "concrete opening question. Do not mention that this is a system event."
)
```

Then run it through the **existing streaming path** — do NOT reimplement streaming. Extract the body of `_handle_message.inner()` (lines ~525–598 in `telegram.py`) so both the message handler and the proactive greeter call it:

```python
# New helper in bot/bridge/telegram.py
async def _run_claude_turn(chat_id, user_id, context, synthesized_prompt):
    # Build a minimal fake "update-like" object OR refactor inner() to take
    # (chat, user, text, status_msg_factory) instead of an Update.
    ...
```

The cleanest refactor is to split `_handle_message.inner()` into:
1. `_prepare_envelope(update, text) -> (envelope, session_dir, system_context)` (already mostly `_envelope_message` + `_build_system_context`),
2. `_run_claude_and_stream(chat, envelope, system_context, session_dir, status_msg) -> str` — the bit that calls `query()` and streams,
3. a thin `_handle_message` that calls both, and a new `_claim_proactive_greet(chat_id, context)` that calls only #2 with the synthetic envelope.

**Language-mirroring caveat:** on first boot there is no user text yet, so we cannot mirror. Two acceptable choices: (a) greet in the operator's Telegram `language_code` (available on `update.effective_user.language_code` captured at claim time), (b) greet bilingually in a short EN + detected-locale form. Option (a) is cleaner — the claim handler has the Update, so capture `user.language_code` and inject it into the envelope: `"The operator's Telegram UI language is '{lang}' — prefer that language for your opener."`.

### 2.3 Reuse points in existing code

From `bot/bridge/telegram.py`:
- `_typing_loop(chat)` — reuse for the greeting's typing indicator.
- `_send_status(update, "…")` — needs a sibling that takes `chat` or `chat_id` instead of `update`, e.g. `_send_status_chat(chat, "…") -> await chat.send_message("…", do_quote=False)`.
- `_make_stream_state`, `_stream_text`, `_on_tool_use`, `_finalize_stream` — all operate on `state["status_msg"]` and `state["update"]`. `state["update"]` is only used inside `_on_tool_use` for `_send_status(state["update"], …)`. Refactor to use `chat` instead and both paths work.
- `build_options(...)` from `claude_query.py` — already injects `<bootstrap>` when `BOOTSTRAP.md` exists at repo root, so the proactive greeter gets the onboarding prompt for free.

### 2.4 Idempotency — no double greeting

Add a flag in `state.json` written by the claim handler:
```python
state["greeted"] = False  # set before proactive greet
# after successful greet:
state["greeted"] = True
write_state(module_dir, state)
```
Guard the proactive call with `if not state.get("greeted"): …`. This also protects against a race where `_claim_handler` fires twice (retry, duplicate update).

---

## §3 Pitfalls & Counter-Prompts

### 3.1 Generic-helpfulness drift on short inputs

**Symptom:** User sends `"привет"` → model defaults to `"Hi! How can I help you today?"` (in English, ignoring language) despite BOOTSTRAP saying "mirror theirs". Known pattern — RLHF assistants collapse to the safe help-desk answer on ambiguous short inputs. [[Persona prompting overview](https://www.emergentmind.com/topics/persona-prompting-pp)] [[Leaked-prompts study](https://www.taskade.com/blog/leaked-ai-prompts-study)]

**Counter-prompt (add to BOOTSTRAP, near the examples):**
```
Even if their first message is a single word like "hi" or "привет", you do
NOT reply with a generic "how can I help you?" — that is not what this moment
is for. You are meeting them for the first time. Greet them in their
language, say you're just meeting them, and ask ONE concrete thing. Save
"how can I help" for later — it belongs in the USER.md world, not here.
```

### 3.2 Streaming the first greeting

The proactive greeting has no inbound user message, so there is no `update.message` to `reply_text` on, and no status-message scaffolding to edit. Solution: call `context.bot.send_message(chat_id=…, text="…")` once to create the initial `…` placeholder message, then thread *that message object* through `_make_stream_state` as `status_msg`. All subsequent `_stream_text`/`_on_tool_use`/`_finalize_stream` calls already operate on `state["status_msg"].edit_text(...)` — no change needed. Note that `_on_tool_use` creates a *new* status message via `_send_status(state["update"], …)`, so the refactor from §2.3 (pass `chat` instead of `update`) is required if the greeter might cause tool use (it might — Claude may Write USER.md during the first conversation).

### 3.3 Double-greeting risk

Covered in §2.4. Additionally: `_claim_handler` raises `ApplicationHandlerStop` on success, so the pairing-code message itself won't be re-processed by `_handle_message`. Good. But the `"Ownership claimed."` plain-text ack should be **removed** (replaced by the proactive greeting) — otherwise the operator gets "Ownership claimed." *and* a greeting, which feels robotic.

### 3.4 `BOOTSTRAP.md` path discovery on LXC

The existing "deleting this file" section uses `/home/animaya/animaya` as the repo root. Verify that path is still authoritative on the live LXC (205 on tower). `claude_query.py` resolves the BOOTSTRAP via `REPO_ROOT = Path(__file__).resolve().parent.parent` — that's the Python-side read path and is robust. The delete-path in BOOTSTRAP.md is what *Claude* executes, and is separate. No change needed for this task, but worth re-confirming at implementation time.

### 3.5 Injection safety

`_read_bootstrap()` in `bot/claude_query.py` already escapes `</bootstrap>` and truncates at 8KB. The candidate rewrite above is ~1.5KB, well within bounds. No new injection risk.

---

## Sources

### Primary (MEDIUM — prompt patterns, multi-source synthesis)
- [Letta/MemGPT deep-dive — Medium, Feb 2026](https://medium.com/@piyush.jhamb4u/stateful-ai-agents-a-deep-dive-into-letta-memgpt-memory-models-a2ffc01a7ea1) — first-meeting behaviour, core-memory update triggers
- [Letta docs — MemGPT concepts](https://docs.letta.com/concepts/memgpt) — persona/human memory block architecture
- [What makes Pi a great companion chatbot — Medium, Lindsey Liu](https://medium.com/@lindseyliu/what-makes-inflections-pi-a-great-companion-chatbot-8a8bd93dbc43) — one-question-at-a-time rhythm analysis
- [Pi AI Guide 2026 — AI Tools DevPro](https://aitoolsdevpro.com/ai-tools/pi-guide/)
- [Character.AI Prompts 2026 — AI Companion Guides](https://aicompanionguides.com/blog/character-ai-prompts/) — persona-first-turn templates
- [AI Character Prompts — Jenova](https://www.jenova.ai/en/resources/ai-character-prompts)
- [The Secret DNA of AI Systems (leaked-prompts study) — Taskade](https://www.taskade.com/blog/leaked-ai-prompts-study) — first-turn contract patterns across ChatGPT/Claude/Gemini
- [Persona Prompting survey — Emergent Mind](https://www.emergentmind.com/topics/persona-prompting-pp) — wake-up / in-character framing
- [Claude Code system prompts archive — Piebald-AI](https://github.com/Piebald-AI/claude-code-system-prompts) — real Claude system-prompt structure reference

### Primary (HIGH — mechanics, official docs)
- [python-telegram-bot Bot reference v22](https://docs.python-telegram-bot.org/en/stable/telegram.bot.html) — `send_message(chat_id, text)`
- [PTB Discussion #2428 — send without context/update](https://github.com/python-telegram-bot/python-telegram-bot/discussions/2428)
- [PTB Issue #780 — send message without conversation flow](https://github.com/python-telegram-bot/python-telegram-bot/issues/780)
- [Claude Agent SDK reference — Python](https://platform.claude.com/docs/en/agent-sdk/python) — `query(prompt, options)`, streaming `AssistantMessage`
- [Claude Agent SDK Python repo](https://github.com/anthropics/claude-agent-sdk-python)
- [Modifying system prompts — Claude Agent SDK docs](https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts)

### Codebase (HIGH — verified by direct read)
- `/Users/admin/hub/workspace/animaya/BOOTSTRAP.md` — current onboarding prompt
- `/Users/admin/hub/workspace/animaya/bot/bridge/telegram.py` — `_claim_handler`, `_handle_message`, `_typing_loop`, streaming helpers
- `/Users/admin/hub/workspace/animaya/bot/claude_query.py` — `_read_bootstrap()`, `<bootstrap>` injection
- `/Users/admin/hub/workspace/animaya/bot/modules_runtime/telegram_bridge.py` — bridge runtime (no change needed for this task)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pi/Inflection's one-question-at-a-time rhythm reflects a real prompt rule (no primary source) [ASSUMED] | §1 Pattern C | Low — the behavioural rule is independently sound |
| A2 | `claude-code-sdk.query()` requires a non-empty `prompt` argument [ASSUMED from SDK convention; not re-verified against 0.0.25 source] | §2.2 | Medium — confirm at impl time; fallback is synthetic envelope anyway |
| A3 | `context.bot.send_message()` from inside a running handler is safe with no extra awaits on Application state [VERIFIED via PTB docs] | §2.1 | Low |
| A4 | `user.language_code` is populated on Telegram updates for real accounts [VERIFIED — already used in `_build_system_context`] | §2.2 | None |

**Research date:** 2026-04-16
**Valid until:** 2026-05-15 (stable domains; prompt-engineering norms shift slowly)
