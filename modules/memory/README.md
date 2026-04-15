# memory module

Persistent memory under `~/hub/knowledge/memory/` written by Claude via
built-in Write/Edit tools. CORE.md is auto-maintained by a Haiku
consolidation task triggered every N user turns.

## Files

- `manifest.json` — Phase 3 module manifest. **depends: ["identity"]** — you
  need a "who" (USER.md) before storing facts about them.
- `install.sh`    — creates `~/hub/knowledge/memory/{CORE.md, README.md}`. Idempotent.
- `uninstall.sh`  — removes `~/hub/knowledge/memory/` entirely.
- `prompt.md`     — static module prompt (assembler-injected).

## owned_paths

Empty (`[]`). See identity README for the rationale (knowledge subdir is
sibling of ANIMAYA_HUB_DIR).

## Config

| Key | Default | Description |
|-----|---------|-------------|
| `consolidation_model` | `claude-haiku-4-5` | SDK model id used for consolidation queries (cheap; not the main chat model) |
| `core_max_lines` | 150 | Soft cap enforced by consolidation prompt (not hard-truncated) |
| `consolidation_every_n_turns` | 10 | Trigger consolidation every Nth user turn |

## Runtime

`bot/modules_runtime/memory.py` — `consolidate_memory()` runs a separate
SDK query with `continue_conversation=False` against `~/hub/knowledge/` so
consolidation never pollutes the main chat session. Triggered fire-and-
forget by `bot/bridge/telegram.py` after each successful reply.
