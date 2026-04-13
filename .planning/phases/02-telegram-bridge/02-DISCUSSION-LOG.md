# Phase 2: Telegram Bridge - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 02-telegram-bridge
**Mode:** --auto (all decisions auto-selected)
**Areas discussed:** V1 Code Reuse, Memory Integration, Session Management, Formatting & Delivery

---

## V1 Code Reuse

| Option | Description | Selected |
|--------|-------------|----------|
| Port v1 with minimal adaptation | Reuse proven telegram.py and claude_query.py, remove v1-only deps | x |
| Rewrite from scratch | Clean v2 implementation following new patterns | |
| Hybrid — port core, rewrite handlers | Keep streaming/throttle, rewrite message handlers | |

**User's choice:** [auto] Port v1 with minimal adaptation (recommended default)
**Notes:** V1 code is battle-tested with streaming, locks, chunking. Rewriting would duplicate effort without benefit.

---

## Memory Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Stub out memory calls | Return minimal static context, Phase 4 adds real memory | x |
| Include basic memory | Port core.py for simple context injection | |
| No memory at all | Pure stateless responses | |

**User's choice:** [auto] Stub out memory calls (recommended default)
**Notes:** Clean phase boundaries — memory is explicitly Phase 4 scope.

---

## Session Management

| Option | Description | Selected |
|--------|-------------|----------|
| Per-chat working dirs | Each chat gets isolated dir under DATA_PATH | x |
| Single shared dir | All chats share one working directory | |
| No working dirs | Claude operates without persistent workspace | |

**User's choice:** [auto] Per-chat working dirs (recommended default)
**Notes:** Matches v1 pattern, provides session isolation for Claude Code tool use.

---

## Formatting & Delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Port v1 formatting | Use existing markdown-to-HTML converter | x |
| Plain text only | Send raw text, no formatting | |
| New formatting system | Build new converter with different approach | |

**User's choice:** [auto] Port v1 formatting (recommended default)
**Notes:** Existing formatter handles Telegram HTML limitations well.

---

## Claude's Discretion

- Voice transcription, image generation: deferred to Phase 4+
- File upload: Claude may include if trivial, otherwise defer

## Deferred Ideas

- Voice transcription (Groq Whisper)
- Image generation (Gemini)
- Group chat prioritization
