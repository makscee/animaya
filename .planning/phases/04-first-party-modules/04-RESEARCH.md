# Phase 4: First-Party Modules - Research

**Researched:** 2026-04-14
**Domain:** Module-driven identity/memory/git-versioning for Claude Code SDK bot on LXC
**Confidence:** HIGH on module wiring & git versioning; MEDIUM on consolidation cadence & onboarding trigger mechanism; one LOW item (Haiku pricing flagged for user confirmation)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Identity Module**
- **D-01:** Onboarding is **Telegram-conversational**. On the first user message after identity module install, bot runs a short Q&A (≈3 questions) and writes answers to `hub/knowledge/identity/`. No dashboard, no seed-file editing.
- **D-02:** Identity files are exactly two: `~/hub/knowledge/identity/USER.md` and `~/hub/knowledge/identity/SOUL.md`. Naming matches v1 Animaya convention.
- **D-03:** IDEN-03 injection wraps each file in its own XML block inside the module's system-prompt snippet: `<identity-user>{USER.md}</identity-user>` and `<identity-soul>{SOUL.md}</identity-soul>`. Assembler XML-wraps the whole module snippet per Phase 3 D-17.
- **D-04:** IDEN-04 reconfigure is a Telegram `/identity` command that re-runs the same onboarding flow and overwrites the files. Same code path as IDEN-01.
- **D-05:** Onboarding trigger: identity module startup reads USER.md/SOUL.md; if either is missing/placeholder, module registers a one-shot "pending onboarding" state consumed by the bridge on next user message. Exact mechanism is Claude's Discretion.

**Memory Module**
- **D-06:** Claude writes memory using the **built-in Write/Edit tools** targeting `~/hub/knowledge/memory/`. No custom MCP tool, no skill file. Module's prompt snippet documents path + naming + size expectations.
- **D-07:** **Memory file structure is deferred to a deeper plan-phase research pass.** Planner must evaluate flat topic files vs tiered core/working/archive vs topic index, pick one backed by research.
- **D-08:** MEMO-04 injection: **only** the core summary file (working name `CORE.md`) is injected into system prompt. All other memory files are read on demand by Claude via Read tool.
- **D-09:** MEMO-03 core summary is **auto-consolidated** by a separate SDK query using a **cheaper Claude model** (e.g. Haiku). Runs post-session. Soft cap ~150 lines enforced by instruction.
- **D-10:** Consolidation uses Claude Code SDK with explicit cheap-model override; main query keeps configured `CLAUDE_MODEL`.

**Git Versioning Module**
- **D-11:** GITV-01 committer is a **background asyncio task inside the bot process**. Commit interval from module config (default 300s). Task lifecycle ties to bot startup/shutdown.
- **D-12:** GITV-02 single-committer enforced by **`asyncio.Lock`** wrapping the commit operation inside the bot process.
- **D-13:** GITV-03 commits are **single commit per interval** covering all changed paths under `~/hub/knowledge/` (scoped by `git add` path limits). Commit message format: `animaya: auto-commit {ISO timestamp}`. Skips entirely when no diff.
- **D-14:** Git-versioning's `owned_paths` covers its config + commit-task wiring, NOT `hub/knowledge/` itself. Uninstalling stops the commit loop but leaves history intact.

**Module Boundaries & Install Order**
- **D-15:** Per-module owned_paths: `identity` → `identity/`; `memory` → `memory/`; `git-versioning` → its module dir only.
- **D-16:** MODS-06 no-import isolation: modules communicate only through hub files. No Python imports between modules.
- **D-17:** Recommended install sequence after setup.sh: `identity → memory → git-versioning`.

### Claude's Discretion
- Exact filename of core summary (`CORE.md` vs `SUMMARY.md`) — aligned with D-07 research pass
- Mechanism the identity module uses to signal "pending onboarding" to the bridge
- Haiku model id + token budget for consolidation query
- Whether `/identity` is a plain Telegram command vs natural-language intent
- Exact commit-loop backoff/jitter when bot is idle (skip-if-no-diff is mandatory)
- Where consolidation runs (inline asyncio task vs scheduled per interval)

### Deferred Ideas (OUT OF SCOPE)
- Dashboard identity/memory edit forms — Phase 5
- Semantic/vector search over memory — v2 (SRCH-01/02)
- Skill files (`~memory.md` etc.) — v2 (ADVM-01)
- Memory auto-summarization triggered by size rather than cadence
- Per-module commit scoping (separate commits per module subdir)
- Out-of-process committer (systemd timer)
- Manifest config surface to switch consolidation model
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IDEN-01 | User completes onboarding defining who they are + who assistant is | Trigger via pending-onboarding flag read by bridge `_handle_message`; Q&A uses python-telegram-bot `ConversationHandler` or stateful flag on `context.user_data`. |
| IDEN-02 | Identity data stored as markdown in Hub `knowledge/identity/` | Write USER.md + SOUL.md; owned_paths = ["identity/"]. |
| IDEN-03 | Identity injected via XML-delimited blocks in system prompt | Module's `prompt.md` embeds `<identity-user>...</identity-user>` and `<identity-soul>...</identity-soul>`. Static vs dynamic render — see Pitfall #1. |
| IDEN-04 | User can reconfigure identity from dashboard without reinstalling | Telegram `/identity` command reruns onboarding (Phase 4 scope); dashboard form is Phase 5. |
| MEMO-01 | Assistant can read/write memory markdown in Hub `knowledge/memory/` | Module prompt doc states path; Claude uses built-in Write/Edit/Read tools (already allowed in `claude_query.build_options`). |
| MEMO-02 | Memory files are git-versioned with full audit trail | Covered by git-versioning module (no memory-specific work). |
| MEMO-03 | Core summary file provides session context | Haiku consolidation task; writes to `memory/CORE.md` (name TBD in plan research). |
| MEMO-04 | Memory module injects relevant context into system prompt | Module's prompt snippet reads CORE.md content at assembly time — requires assembler change OR runtime interpolation (see Open Question #1). |
| GITV-01 | Auto-commits data changes on configurable interval | asyncio background task started in bot main.py, interval from module config (default 300s). |
| GITV-02 | Single-committer pattern prevents concurrent writes | asyncio.Lock wraps each commit call. |
| GITV-03 | Commits scoped to module subdirectories for clean history | `git add hub/knowledge/` (or individual module subdirs); single commit per tick per D-13. |
</phase_requirements>

---

## Summary

Phase 3 delivered the full lifecycle machinery: `bot/modules/{manifest,registry,assembler,lifecycle,__main__}.py` plus the bridge reference module. Phase 4 adds three real modules that exercise distinct integration surfaces — **prompt-content injection (identity), tool-mediated file mutation (memory), background-task lifecycle (git-versioning)** — that together stress-test every seam in the Phase 3 contract.

The largest implementation risk is **MEMO-04 / IDEN-03 prompt injection timing**. The Phase 3 assembler reads each module's `system_prompt_path` file at every install/uninstall AND at every bot startup (D-18). USER.md, SOUL.md, and CORE.md live in hub/knowledge/ and change per session (identity onboarding, Haiku consolidation), but the assembler only reads the module-owned `prompt.md`. Two clean solutions exist: (1) the module's `prompt.md` is a **template** and the assembler is extended to interpolate file contents; (2) the module's `prompt.md` stays static, and the bridge reads USER.md/SOUL.md/CORE.md at query time via `bot.claude_query.build_options(system_prompt_extra=...)` — the existing Phase 2 pattern. **Option 2 is the recommended path**: it preserves Phase 3's assembler contract unchanged, matches the Phase 2 `_build_system_context()` pattern already in `bot/bridge/telegram.py`, and gives each message the latest file contents without needing an assembler-rerun after every memory consolidation.

Second-largest risk: **single-committer invariant**. The asyncio.Lock (D-12) protects against concurrent commits within one Python process, but the bot container startup, a future manual user `git commit`, or a Hub-side sync could step on it. The committer MUST handle "repo dirty with unrelated staged changes" defensively (reset-index or `git add -- hub/knowledge/` path scoping, not `git add -A`).

Third: **onboarding-trigger durability**. An in-memory flag loses state on restart. A sentinel file (e.g., `hub/knowledge/identity/.pending-onboarding`) is more robust and inspection-friendly, and it naturally self-heals at next startup by re-probing USER.md/SOUL.md presence.

**Primary recommendation:** Build the three modules in the order `identity → git-versioning → memory` (not the CONTEXT.md-recommended `identity → memory → git-versioning`) inside Phase 4 development order; ship-time install order per D-17 is a separate concern. Git-versioning has no upstream dependency and unblocks manual end-to-end testing of memory file changes immediately.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-telegram-bot | 21.10+ (already installed) | `/identity` command handler + ConversationHandler for onboarding Q&A | [VERIFIED: pyproject.toml] Already wired in `bot/bridge/telegram.py`; `CommandHandler` + `ConversationHandler` is the idiomatic Q&A pattern. |
| claude-code-sdk | 0.0.25+ (already installed) | SDK query with `model=claude-haiku-4-5` override for consolidation | [VERIFIED: bot/claude_query.py] `ClaudeCodeOptions(model=...)` already supported; override is a single param. |
| subprocess (stdlib) | 3.12 | Running `git` commands from committer | [VERIFIED: bot/features/git_versioning.py v1] v1 uses subprocess with explicit env; pattern proven. |
| asyncio (stdlib) | 3.12 | Background commit task + `asyncio.Lock` (D-12) | [CITED: docs.python.org/3/library/asyncio-task.html] Standard pattern; `asyncio.create_task(...)` with cancellation on shutdown. |
| pathlib (stdlib) | 3.12 | Filesystem paths | Project convention. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | >=2.0 (already installed) | Per-module config_schema validation (JSON Schema passthrough today; typed models later) | Already in Phase 3 manifest stack — reuse. |
| pytest / pytest-asyncio | >=8.0 / >=0.23 | Unit tests for consolidation prompt, commit-loop, onboarding state machine | Already configured. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `subprocess` git | GitPython library | New dep for trivially wrapping 3 git calls (`status`, `add`, `commit`). v1 ran bare subprocess successfully — [VERIFIED: bot/features/git_versioning.py] shows 42 lines of subprocess code suffices. Skip GitPython. |
| `ConversationHandler` for onboarding | Raw state-on-`user_data` + if/else in `_handle_message` | ConversationHandler adds nested state and dispatch overhead for only 3 questions. A lightweight "pending_onboarding" flag with sequential reply handling is simpler — but ConversationHandler is better-tested against timeouts. Planner picks. |
| Sentinel-file pending-onboarding marker | In-memory bot_data dict | Sentinel survives restart; bot_data is lost. Recommend sentinel. |
| `git add -A` | `git add -- hub/knowledge/` path-scoped add | Path-scoped add enforces GITV-03 "scoped to module subdirectories" automatically and prevents picking up stray files. Use path-scoped. |
| Haiku consolidation | Sonnet consolidation (main model) | D-09 locks: cheaper model. Recommended: `claude-haiku-4-5`. |

**Installation (Wave 0 verification only — no new deps expected):**
```bash
# Verify already present (no new install)
python -c "import telegram, claude_code_sdk, pydantic; print('ok')"
```

**Version verification:**
- [CITED: anthropic.com/claude/haiku] Claude Haiku 4.5 model id: `claude-haiku-4-5`. Pricing: $1/M input, $5/M output (as of 2026-04-14). Tagged **[ASSUMED]** for final model-id selection — user may prefer a different cost tier; see Assumptions Log A1.
- [VERIFIED: pyproject.toml] python-telegram-bot 21.10+, claude-code-sdk 0.0.25+, pydantic already declared.

---

## Architecture Patterns

### Recommended Project Structure

```
~/animaya/
├── modules/
│   ├── identity/
│   │   ├── manifest.json            # name="identity", owned_paths=["identity/"]
│   │   ├── install.sh               # Creates hub/knowledge/identity/ with placeholder USER.md/SOUL.md
│   │   ├── uninstall.sh             # Removes hub/knowledge/identity/ (MODS-05 leakage enforcement)
│   │   └── prompt.md                # Static doc instructing Claude about identity; actual content injected at query-time via bridge
│   ├── memory/
│   │   ├── manifest.json            # name="memory", owned_paths=["memory/"]
│   │   ├── install.sh               # Creates hub/knowledge/memory/ with empty CORE.md + README
│   │   ├── uninstall.sh             # Removes hub/knowledge/memory/
│   │   └── prompt.md                # Static prompt doc ("You can Write/Read memory files under knowledge/memory/…"); CORE.md injected at query-time via bridge
│   └── git-versioning/
│       ├── manifest.json            # name="git-versioning", owned_paths=[] (committer wiring only)
│       ├── install.sh               # Initializes ~/hub as git repo if not already
│       ├── uninstall.sh             # No-op (leaves repo + history intact per D-14)
│       └── prompt.md                # Minimal; tells Claude that knowledge/ is git-versioned
└── bot/
    ├── main.py                      # Extended: spawn git-versioning task if module installed
    ├── bridge/telegram.py           # Extended: /identity command, onboarding flow, pending-onboarding probe
    ├── claude_query.py              # Extended: build_options() reads USER.md/SOUL.md/CORE.md into system_prompt
    ├── modules_runtime/             # NEW PACKAGE — per-module Python runtime code (NOT the module's shell scripts)
    │   ├── __init__.py
    │   ├── identity.py              # onboarding state machine + file I/O
    │   ├── memory.py                # consolidation query + CORE.md reader
    │   └── git_versioning.py        # commit loop + asyncio.Lock
    └── templates/CLAUDE.md          # Updated base template
```

**Critical design note:** The module's shell scripts (`install.sh`, `uninstall.sh`) handle *filesystem lifecycle*. The module's *runtime behavior* (onboarding Q&A, consolidation, commit loop) runs inside the bot process and must live in Python. Per MODS-06 (D-20), we avoid cross-module Python imports — runtime code lives under `bot/modules_runtime/` as bot-owned adapters, not inside `modules/<name>/`. This matches Phase 3 A2-style resolution where bridge module code also lives under `bot/bridge/` not `modules/bridge/`.

### Pattern 1: Identity Onboarding with Sentinel File

**What:** A file at `hub/knowledge/identity/.pending-onboarding` signals an unfinished onboarding. Bridge's `_handle_message` checks for it on every message; if present, route to onboarding flow instead of Claude.

**When to use:** Only when USER.md or SOUL.md are missing/placeholder.

**Example:**
```python
# Source: [ASSUMED] — derived from D-05 discretion + durability reasoning
from pathlib import Path

IDENTITY_DIR = Path.home() / "hub" / "knowledge" / "identity"
PENDING_SENTINEL = IDENTITY_DIR / ".pending-onboarding"
USER_FILE = IDENTITY_DIR / "USER.md"
SOUL_FILE = IDENTITY_DIR / "SOUL.md"

PLACEHOLDER_MARKER = "<!-- animaya:placeholder -->"

def is_identity_initialized() -> bool:
    if not (USER_FILE.exists() and SOUL_FILE.exists()):
        return False
    for f in (USER_FILE, SOUL_FILE):
        if PLACEHOLDER_MARKER in f.read_text(encoding="utf-8"):
            return False
    return True

def mark_pending_onboarding() -> None:
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_SENTINEL.write_text("awaiting first user message\n", encoding="utf-8")

def clear_pending_onboarding() -> None:
    PENDING_SENTINEL.unlink(missing_ok=True)
```

The identity module's `install.sh` writes USER.md + SOUL.md with `PLACEHOLDER_MARKER` content plus creates `.pending-onboarding`. The bridge's `_handle_message` runs `PENDING_SENTINEL.exists()` check before dispatching to Claude.

### Pattern 2: Telegram Onboarding Q&A

**What:** Sequential 3-question flow using `ConversationHandler` states or a lightweight custom state machine on `context.user_data`.

**When to use:** First message after identity install (sentinel present) OR explicit `/identity` command (D-04).

**Example (ConversationHandler):**
```python
# Source: [CITED: docs.python-telegram-bot.org/en/stable/telegram.ext.conversationhandler.html]
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

Q1_USER, Q2_SOUL, Q3_ADDRESS = range(3)

async def onboarding_start(update, context):
    await update.message.reply_text(
        "Let's get to know each other. First: tell me about yourself — "
        "who are you, what do you do, what matters to you?"
    )
    return Q1_USER

async def onboarding_q1(update, context):
    context.user_data["identity_user"] = update.message.text
    await update.message.reply_text(
        "Thanks. Now — what kind of assistant do you want me to be? "
        "Personality, tone, what should I prioritize?"
    )
    return Q2_SOUL

async def onboarding_q2(update, context):
    context.user_data["identity_soul"] = update.message.text
    await update.message.reply_text(
        "Last one: how should I address you? (e.g., first name, nickname, 'boss'…)"
    )
    return Q3_ADDRESS

async def onboarding_q3(update, context):
    addressing = update.message.text
    write_identity_files(
        user_text=context.user_data["identity_user"],
        soul_text=context.user_data["identity_soul"],
        addressing=addressing,
    )
    clear_pending_onboarding()
    await update.message.reply_text(
        f"Got it. I'll remember you as {addressing}. Send me anything."
    )
    return ConversationHandler.END

conv = ConversationHandler(
    entry_points=[CommandHandler("identity", onboarding_start)],
    states={
        Q1_USER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_q1)],
        Q2_SOUL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_q2)],
        Q3_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_q3)],
    },
    fallbacks=[CommandHandler("cancel", onboarding_cancel)],
)
```

**Key design:** `/identity` is the `entry_points` handler (satisfies D-04). The pending-onboarding sentinel triggers entry on *any* first message after install by routing through the same `onboarding_start` — this is the detail the planner must wire.

### Pattern 3: Memory Injection at Query Time (NOT Assemble Time)

**What:** `bot/claude_query.build_options()` reads USER.md, SOUL.md, CORE.md on every query and concatenates into `system_prompt_extra`. The module's static `prompt.md` (assembler-injected) only documents the *contract* ("you have an identity / you have memory you can Read/Write"), not the *content*.

**Why not assemble-time:** CORE.md changes after every consolidation; USER.md changes after every `/identity`. Assembler runs on install/uninstall/startup (D-18). Running the assembler after every memory write creates a feedback loop and a race with the git committer.

**Example (extend `bot/claude_query.py`):**
```python
# Source: [ASSUMED] — extends existing Phase 2 pattern; mirrors _build_system_context
from pathlib import Path

HUB_KNOWLEDGE = Path.home() / "hub" / "knowledge"

def _read_if_present(p: Path, max_chars: int = 8_000) -> str:
    if not p.is_file():
        return ""
    text = p.read_text(encoding="utf-8").strip()
    return text if len(text) <= max_chars else text[:max_chars] + "\n…[truncated]"

def build_options(
    data_dir: Path | None = None,
    system_prompt_extra: str = "",
    cwd: Path | str | None = None,
):
    from claude_code_sdk import ClaudeCodeOptions

    parts = []
    if system_prompt_extra:
        parts.append(system_prompt_extra)

    # IDEN-03: identity injection (XML-delimited per D-03)
    user_md = _read_if_present(HUB_KNOWLEDGE / "identity" / "USER.md")
    soul_md = _read_if_present(HUB_KNOWLEDGE / "identity" / "SOUL.md")
    if user_md:
        parts.append(f"<identity-user>\n{user_md}\n</identity-user>")
    if soul_md:
        parts.append(f"<identity-soul>\n{soul_md}\n</identity-soul>")

    # MEMO-04: core summary injection
    core_md = _read_if_present(HUB_KNOWLEDGE / "memory" / "CORE.md")
    if core_md:
        parts.append(f"<memory-core>\n{core_md}\n</memory-core>")

    system_prompt = "\n\n".join(parts) if parts else ""
    # … rest unchanged
```

**Important:** the `<identity-*>` / `<memory-*>` XML delimiters here are the content wrap (per D-03). The Phase 3 assembler further wraps the whole `prompt.md` in `<module name="identity">…</module>` (per D-17) — but that wraps the *static prompt doc*, not the dynamic content. These are different injection channels.

### Pattern 4: Consolidation Query with Cheap Model

**What:** A separate Claude Code SDK query that reads the session's conversation, extracts facts, writes them to memory files, and rewrites `CORE.md` as a ≤150-line summary. Uses `model="claude-haiku-4-5"` override.

**When:** Post-session. Cadence (session-end, N-turn, manual trigger) is Claude's Discretion per D-09 — planner picks.

**Example:**
```python
# Source: [ASSUMED] — derived from D-09/D-10 + v1 bot/memory/core.py:build_consolidation_prompt()
from claude_code_sdk import ClaudeCodeOptions, query
from claude_code_sdk.types import AssistantMessage, TextBlock

CONSOLIDATION_MODEL = "claude-haiku-4-5"

async def consolidate_memory(conversation_text: str, hub_knowledge: Path) -> None:
    prompt = f"""You are updating the user's persistent memory based on the conversation below.

CONVERSATION:
{conversation_text}

TASK:
1. Extract new facts about the user or their world that are worth remembering long-term.
2. Read ~/hub/knowledge/memory/CORE.md (if it exists) — the current summary.
3. Write an updated CORE.md that incorporates new facts AND keeps the total under ~150 lines.
4. Write additional topic files in ~/hub/knowledge/memory/<topic>.md as markdown if appropriate.

RULES:
- Only new information; don't restate what's already in CORE.md.
- Bullet style, factual, no narrative.
- If nothing worth remembering, make no edits.

Use the Read and Write tools. When done, respond with a single-line summary of what you changed (or "no changes").
"""
    options = ClaudeCodeOptions(
        model=CONSOLIDATION_MODEL,
        system_prompt="You are a memory-consolidation assistant. Be terse and factual.",
        cwd=str(hub_knowledge),
        allowed_tools=["Read", "Write", "Edit"],
        permission_mode="acceptEdits",
        continue_conversation=False,   # fresh context; do NOT continue main session
    )
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    logger.info("consolidation: %s", block.text.strip()[:200])
```

**Critical:** `continue_conversation=False` — consolidation runs outside the main chat's session context. Mixing contexts would pollute the user-facing chat's `--continue` state.

### Pattern 5: Git Commit Loop with asyncio.Lock

**What:** Background asyncio task, 300s default interval, path-scoped `git add hub/knowledge/`, skip when no diff. Wrap every commit operation in `asyncio.Lock` per D-12.

**Example:**
```python
# Source: [VERIFIED: bot/features/git_versioning.py v1 pattern] adapted to asyncio
import asyncio, subprocess, logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

HUB_ROOT = Path.home() / "hub"
KNOWLEDGE_DIR = HUB_ROOT / "knowledge"
_COMMIT_LOCK = asyncio.Lock()

async def _run_git_async(*args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(HUB_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ,
             "GIT_AUTHOR_NAME": "Animaya Bot",
             "GIT_AUTHOR_EMAIL": "bot@animaya.local",
             "GIT_COMMITTER_NAME": "Animaya Bot",
             "GIT_COMMITTER_EMAIL": "bot@animaya.local"},
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    return stdout.decode().strip()

async def commit_if_changed() -> bool:
    async with _COMMIT_LOCK:
        if not (HUB_ROOT / ".git").is_dir():
            return False
        # Path-scoped status — ONLY knowledge/ counts
        status = await _run_git_async("status", "--porcelain", "--", "knowledge/")
        if not status:
            return False
        await _run_git_async("add", "--", "knowledge/")
        cached = await _run_git_async("diff", "--cached", "--stat", "--", "knowledge/")
        if not cached:
            return False
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await _run_git_async("commit", "-m", f"animaya: auto-commit {ts}")
        logger.info("committed knowledge/ changes at %s", ts)
        return True

async def commit_loop(interval: int = 300) -> None:
    logger.info("git auto-commit loop started (interval=%ds)", interval)
    try:
        while True:
            await asyncio.sleep(interval)
            try:
                await commit_if_changed()
            except Exception:
                logger.exception("auto-commit tick failed")
    except asyncio.CancelledError:
        logger.info("git auto-commit loop stopping; final commit")
        try:
            await commit_if_changed()
        except Exception:
            logger.exception("final commit failed")
        raise
```

**Integration:** `bot/main.py` checks registry for `git-versioning` and, if installed, spawns the task:
```python
from bot.modules.registry import get_entry
entry = get_entry(data_path, "git-versioning")
if entry is not None:
    interval = entry.get("config", {}).get("interval_seconds", 300)
    commit_task = asyncio.create_task(commit_loop(interval=interval))
```

But `main.py` today is sync (`app.run_polling()` is blocking). Because python-telegram-bot runs its own event loop via `run_polling()`, the auto-commit task must be registered via `application.post_init` or `application.create_task(...)`. See Pitfall #2.

### Anti-Patterns to Avoid

- **Assembler reading identity/memory files:** The assembler reads `module_dir / prompt.md` only. Putting USER.md content into the assembler output means every memory write requires a CLAUDE.md rewrite plus a git commit — classic feedback loop. Keep identity/memory content injected at query-time.
- **`git add -A` in auto-commit:** GITV-03 says "scoped to module subdirectories". Path-scoped `git add -- knowledge/` enforces this; `-A` picks up temp files, session logs, unrelated staging.
- **Calling `subprocess.run()` (blocking) from an asyncio task:** Blocks the event loop during 30-second git operations. Use `asyncio.create_subprocess_exec`.
- **Persistent onboarding state in `context.user_data` only:** Lost on bot restart mid-onboarding. Use the sentinel file as the source-of-truth; bot_data is fast path.
- **Running consolidation with `continue_conversation=True`:** Pollutes the main chat's `--continue` session. Consolidation MUST use `continue_conversation=False` and a distinct `cwd` (recommend `hub/knowledge/`).
- **Writing a custom MCP "memory" tool:** D-06 rules this out. Claude uses built-in Write/Edit. Do not build a tool.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Conversation state machine | Bespoke if/elif on `context.user_data["step"]` | `telegram.ext.ConversationHandler` | Handles entry/exit, timeouts, fallbacks, cancellation out of the box. |
| Markdown frontmatter parsing | Custom regex for USER.md metadata | Plain markdown body — no frontmatter needed for v1 | The content is the content; don't add YAML ceremony. |
| Git plumbing | GitPython, dulwich, pygit2 | `subprocess` calls to `git` CLI | v1 proved 3 subprocess calls suffice; the git binary is already present on Claude Box. |
| Diff detection | Custom hash/mtime comparison | `git status --porcelain -- knowledge/` | Git already tracks diffs authoritatively. |
| Cross-process commit mutex | File locking (flock) | asyncio.Lock (in-process) per D-12 | Bot is the only writer by design (D-12). In-process lock is correct AND simpler. |
| Memory tokenizer / chunker | Custom chunk logic for CORE.md | Instruction in prompt: "keep under 150 lines" | Soft cap via instruction per D-09; no programmatic truncation needed. |
| Post-session detection | Wall-clock heuristics | Explicit trigger: end of each `_handle_message` call OR every N messages counted in `context.chat_data` | Deterministic. Planner picks cadence; both are simple. |

**Key insight:** Every problem in this phase has a battle-tested standard tool. The failure mode is inventing middleware.

---

## Common Pitfalls

### Pitfall 1: Confusing "module prompt" with "module dynamic content"

**What goes wrong:** Developer puts `{{USER.md}}` placeholder in `modules/identity/prompt.md`, expects assembler to interpolate.
**Why it happens:** D-03 says identity content is wrapped in `<identity-user>` XML — natural to assume assembler does it.
**How to avoid:** Module `prompt.md` is a *static doc* (assembler-injected once). The *dynamic* identity content is injected per-query via `bot.claude_query.build_options()`. Document this split in module-authoring-guide amendment.
**Warning signs:** Module prompt contains template placeholders; CLAUDE.md on disk shows literal `{{...}}` strings.

### Pitfall 2: Spawning the commit task before the event loop exists

**What goes wrong:** Calling `asyncio.create_task(commit_loop())` from sync `main()` raises `RuntimeError: no running event loop`.
**Why it happens:** `bot/main.py` is sync; `app.run_polling()` creates the loop internally.
**How to avoid:** Use python-telegram-bot's `application.post_init` hook or `application.create_task()` which runs inside the loop.
```python
async def _post_init(app):
    if get_entry(data_path, "git-versioning"):
        app.create_task(commit_loop(interval=300), name="git-autocommit")

app = (Application.builder()
       .token(token)
       .post_init(_post_init)
       .build())
```
**Warning signs:** Bot starts, logs `RuntimeError: no running event loop` immediately.

### Pitfall 3: `git add -- knowledge/` when knowledge/ is not yet a git repo

**What goes wrong:** git-versioning module installs before `hub/` has `.git/`; first commit tick fails.
**Why it happens:** Hub may or may not be git-managed on the LXC — depends on user setup.
**How to avoid:** `install.sh` for git-versioning MUST run `git init` if `$ANIMAYA_HUB_DIR/../.git` is absent. Also configure `user.name` / `user.email` inside the repo to avoid committer identity errors on pristine boxes.
**Warning signs:** First auto-commit tick logs `fatal: not a git repository`.

### Pitfall 4: Uninstalling identity wipes USER.md before user realizes

**What goes wrong:** `uninstall.sh` deletes `hub/knowledge/identity/`, user loses their self-definition silently.
**Why it happens:** MODS-05 demands zero artifacts — the owned_paths leakage check will RAISE if the dir remains.
**How to avoid:** Document in user-facing uninstall message that identity data is erased. Optionally: `uninstall.sh` moves `identity/` to `identity.backup-{timestamp}/` OUTSIDE owned_paths. [ASSUMED] user is okay with full deletion per D-15; planner confirms.
**Warning signs:** User reinstalls and finds USER.md empty after previous sessions.

### Pitfall 5: Consolidation query hangs bot handler

**What goes wrong:** Consolidation is launched synchronously at end of `_handle_message`, user's next message is blocked.
**Why it happens:** SDK queries are long (seconds). Running inline adds latency to every follow-up.
**How to avoid:** Spawn consolidation as fire-and-forget: `asyncio.create_task(consolidate_memory(...))` after the user reply is sent. Wrap in try/except so failures don't crash the handler.
**Warning signs:** "Typing" indicator appears and disappears between user turns; latency spikes every N turns.

### Pitfall 6: Pending-onboarding sentinel survives uninstall

**What goes wrong:** User uninstalls identity module; sentinel remains in `hub/knowledge/identity/` orphan; next install triggers onboarding unnecessarily.
**Why it happens:** Sentinel is owned by identity; uninstall.sh must remove it.
**How to avoid:** `uninstall.sh` deletes the whole `hub/knowledge/identity/` dir (which includes the sentinel). Leakage check confirms.
**Warning signs:** Post-uninstall, `hub/knowledge/identity/.pending-onboarding` remains → MODS-05 leakage check raises.

### Pitfall 7: Haiku consolidation exceeds token budget or writes garbage

**What goes wrong:** Haiku hallucinates, writes contradictions to CORE.md, or produces a 500-line "summary".
**Why it happens:** Soft cap via instruction (D-09) is not enforced programmatically.
**How to avoid:** Post-consolidation, bot reads CORE.md, counts lines; if > 200 (25% overrun), log a warning. Don't auto-truncate — let next consolidation self-correct. Include "if you can't fit in 150 lines, drop least-important facts" in prompt.
**Warning signs:** CORE.md grows monotonically over sessions.

### Pitfall 8: `/identity` command collision with Phase 2 command handler registration

**What goes wrong:** `/identity` is registered by identity-module wiring, but Phase 2 `_handle_message` also filters `~filters.COMMAND` — if registration order is wrong, `/identity` falls into message handler.
**Why it happens:** python-telegram-bot dispatches by handler order; message handler registered before command handler wins for unmatched commands.
**How to avoid:** Register `/identity` CommandHandler (or ConversationHandler with `/identity` entry point) BEFORE the generic MessageHandler. Place in `build_app()` right after `/start`.
**Warning signs:** `/identity` typed in Telegram triggers normal Claude query instead of onboarding flow.

---

## Runtime State Inventory

Phase 4 is greenfield module creation — not a rename or migration. No existing runtime state to rewrite. Inventory for completeness:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `hub/knowledge/identity/`, `hub/knowledge/memory/` are new dirs created by module install.sh | None; install.sh creates. |
| Live service config | None — no external services bound to identity/memory. | None. |
| OS-registered state | None — no systemd timers (D-11 commits in-process). | None. |
| Secrets/env vars | `CLAUDE_CODE_OAUTH_TOKEN` already set (Phase 1). No new secrets. | None. |
| Build artifacts | None — no new compiled code. | None. |

**Nothing found in any category — verified by reviewing CONTEXT.md Deferred list and existing `bot/` tree.**

---

## Code Examples

Verified patterns ready for plan adoption.

### identity/manifest.json

```json
{
  "manifest_version": 1,
  "name": "identity",
  "version": "1.0.0",
  "system_prompt_path": "prompt.md",
  "owned_paths": ["identity/"],
  "scripts": {
    "install": "install.sh",
    "uninstall": "uninstall.sh"
  },
  "depends": [],
  "config_schema": null
}
```

### identity/install.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

# Source: v1 conventions + D-02 file names
IDENTITY_DIR="${ANIMAYA_HUB_DIR}/identity"
mkdir -p "${IDENTITY_DIR}"

# Placeholder content with sentinel marker — bridge detects via marker
cat > "${IDENTITY_DIR}/USER.md" <<'EOF'
<!-- animaya:placeholder -->
# User

(Pending onboarding — the user will describe themselves on first message.)
EOF

cat > "${IDENTITY_DIR}/SOUL.md" <<'EOF'
<!-- animaya:placeholder -->
# Assistant Identity

(Pending onboarding — the user will shape the assistant's persona.)
EOF

# Pending-onboarding sentinel
printf 'awaiting first user message\n' > "${IDENTITY_DIR}/.pending-onboarding"

echo "identity module installed; onboarding pending"
```

### identity/uninstall.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

IDENTITY_DIR="${ANIMAYA_HUB_DIR}/identity"
# Idempotent; MODS-05 requires full removal
rm -rf "${IDENTITY_DIR}"
echo "identity module uninstalled (identity data removed)"
```

### identity/prompt.md

```markdown
## Identity Module

The user has a persistent identity file at `hub/knowledge/identity/USER.md`
and the assistant's persona at `hub/knowledge/identity/SOUL.md`.

Both files are loaded into the system prompt on every message as
`<identity-user>` and `<identity-soul>` blocks. Respect them.

If the user asks to update their identity, use `/identity` (re-runs onboarding)
or edit the files directly with the Write tool.
```

### memory/manifest.json

```json
{
  "manifest_version": 1,
  "name": "memory",
  "version": "1.0.0",
  "system_prompt_path": "prompt.md",
  "owned_paths": ["memory/"],
  "scripts": {
    "install": "install.sh",
    "uninstall": "uninstall.sh"
  },
  "depends": ["identity"],
  "config_schema": {
    "type": "object",
    "properties": {
      "consolidation_model": {
        "type": "string",
        "default": "claude-haiku-4-5"
      },
      "core_max_lines": {
        "type": "integer",
        "default": 150
      }
    }
  }
}
```

Note the `depends: ["identity"]` — memory is meaningful only after identity exists (you need a "who" before you store facts about them). Enforced via D-15.

### memory/install.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

MEMORY_DIR="${ANIMAYA_HUB_DIR}/memory"
mkdir -p "${MEMORY_DIR}"

# CORE.md starts empty but present — avoids assembler reading a missing file on first run
if [ ! -f "${MEMORY_DIR}/CORE.md" ]; then
  cat > "${MEMORY_DIR}/CORE.md" <<'EOF'
# Core Memory

(Auto-generated by Haiku consolidation after sessions. Empty until first session.)
EOF
fi

if [ ! -f "${MEMORY_DIR}/README.md" ]; then
  cat > "${MEMORY_DIR}/README.md" <<'EOF'
# Memory

- `CORE.md` — rolling ~150-line summary auto-maintained by the memory module.
- Other files — topic-specific memories written by the assistant.
EOF
fi

echo "memory module installed"
```

### memory/prompt.md

```markdown
## Memory Module

You have a persistent memory under `hub/knowledge/memory/`:

- `CORE.md` — current rolling summary (loaded into system prompt on every message
  as `<memory-core>`). Keep it concise; it is auto-rewritten after sessions.
- Other files (e.g., `people.md`, `projects.md`, `preferences.md`) — topical
  memories. Read them with the Read tool as needed; write new facts with the
  Write/Edit tool.

Never fabricate memories. Only write things the user actually said or asked you
to remember. If unsure, ask.
```

### git-versioning/manifest.json

```json
{
  "manifest_version": 1,
  "name": "git-versioning",
  "version": "1.0.0",
  "system_prompt_path": "prompt.md",
  "owned_paths": [],
  "scripts": {
    "install": "install.sh",
    "uninstall": "uninstall.sh"
  },
  "depends": [],
  "config_schema": {
    "type": "object",
    "properties": {
      "interval_seconds": {
        "type": "integer",
        "default": 300,
        "minimum": 30
      }
    }
  }
}
```

### git-versioning/install.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

HUB_ROOT="$(dirname "${ANIMAYA_HUB_DIR}")"   # ANIMAYA_HUB_DIR = ~/hub/knowledge/animaya → HUB_ROOT = ~/hub
# Actually hub git repo root is ~/hub itself. Confirm with user / adjust if HUB_ROOT convention changes.

# Correct derivation: the git repo lives at ~/hub/, not a parent of ANIMAYA_HUB_DIR.
# Use explicit path or discover via ANIMAYA_HUB_DIR's own ancestry. See Open Question #3.
GIT_REPO_ROOT="$(cd "${ANIMAYA_HUB_DIR}" && git rev-parse --show-toplevel 2>/dev/null || echo "${HOME}/hub")"

if [ ! -d "${GIT_REPO_ROOT}/.git" ]; then
  git -C "${GIT_REPO_ROOT}" init
  git -C "${GIT_REPO_ROOT}" config user.name "Animaya Bot"
  git -C "${GIT_REPO_ROOT}" config user.email "bot@animaya.local"
fi

echo "git-versioning installed; repo at ${GIT_REPO_ROOT}"
```

### git-versioning/uninstall.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

# Per D-14: history remains intact. Just log.
echo "git-versioning uninstalled; existing git history preserved."
```

### Example: updated bot/main.py excerpt (post-init wiring)

```python
async def _post_init(application) -> None:
    from bot.modules.registry import get_entry
    from bot.modules_runtime.git_versioning import commit_loop

    data_path = Path(os.environ.get("DATA_PATH", DEFAULT_DATA_PATH))
    entry = get_entry(data_path, "git-versioning")
    if entry is not None:
        interval = entry.get("config", {}).get("interval_seconds", 300)
        application.create_task(commit_loop(interval=interval), name="git-autocommit")
        logger.info("git-versioning commit loop scheduled")
```

---

## State of the Art

| Old (v1 Docker bot) | New (v2 LXC modules) | Impact |
|---|---|---|
| `SOUL.md`, `OWNER.md` hard-coded in `bot/memory/core.py` | `USER.md`, `SOUL.md` owned by identity module in `hub/knowledge/identity/` | Naming change: OWNER → USER (matches REQUIREMENTS IDEN-01 "who they are"); SOUL stays. |
| `facts.md`, `people.md`, `projects.md` hard-coded paths | Memory file structure **deferred to planner research** (D-07) | Phase 4 picks structure empirically, not by v1 precedent. |
| Sonnet consolidation | **Haiku consolidation** (`claude-haiku-4-5`) | $1/M input tokens; 5x cheaper than Sonnet. Cost-driven architecture. |
| Git commit via threading.Thread + blocking subprocess | asyncio task + `asyncio.create_subprocess_exec` | Non-blocking; integrates with telegram-bot's loop; clean shutdown via CancelledError. |
| Commit message: `auto: data update {ts}` | `animaya: auto-commit {ISO timestamp}` (D-13) | Consistent prefix for history filtering; ISO timestamp for machine-parsable logs. |
| `GIT_COMMIT_INTERVAL` env var (global) | Module config `interval_seconds` in registry.json | Per-module config; still defaults to 300s. |

**Deprecated:**
- `bot/memory/core.py:build_core_context()` — v1 shape. Phase 4 replaces with query-time injection in `bot/claude_query.py`. The file can be deleted or repurposed.
- `bot/features/git_versioning.py` — v1 threading implementation. Phase 4 replaces with `bot/modules_runtime/git_versioning.py` (asyncio).
- `OWNER.md` name — superseded by `USER.md` (D-02).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Consolidation model is `claude-haiku-4-5` | Standard Stack, Pattern 4 | User may prefer a different tier (cost vs quality); easy to flip via module config `consolidation_model`. **CONFIRM WITH USER** before locking. |
| A2 | Hub git repo root is `~/hub/` (not `~/hub/knowledge/`) | Pattern 5, git-versioning/install.sh | Wrong repo root means commits fail or land in unintended places. Plan must verify with user / with Phase 1 setup.sh. |
| A3 | `continue_conversation=False` for consolidation query is correct | Pattern 4 | If set to True, consolidation pollutes main chat's --continue context. Verified by SDK docs but untested in this codebase. |
| A4 | Query-time injection (not assemble-time) is the right channel for identity/memory content | Summary, Pattern 3, Pitfall #1 | If planner chooses assemble-time instead, every memory write triggers assembler + (via D-18) every bot restart re-injects stale snapshot. Recommend query-time. |
| A5 | Onboarding-trigger mechanism is a sentinel file `.pending-onboarding` | Pattern 1 | D-05 explicitly discretion. Sentinel is durable; in-memory flag is faster but fragile. |
| A6 | Bot process is the only writer to `hub/knowledge/` | Pattern 5, D-12 | If user runs manual `git commit` in hub/ concurrently, asyncio.Lock doesn't protect. Git's own index locking protects at file level but may surface as visible commit failures. Monitor via Pitfall #3 warning. |
| A7 | `depends: ["identity"]` on memory module | memory/manifest.json | Enforces install order, but doesn't block uninstalling identity while memory is installed (D-15 reverse). Blocks if user wants memory without identity — probably correct but worth confirming. |
| A8 | Consolidation runs post-reply as fire-and-forget | Pitfall #5 | If cadence is "every N turns" instead of "every session", pattern still applies. |

**User confirmation required for A1, A2, A7 before execution.**

---

## Open Questions

1. **Injection channel for identity/memory content — assemble-time vs query-time?**
   - What we know: D-03 says "identity injection wraps each file in its own XML block inside the module's system-prompt snippet". Literal reading → assembler reads files.
   - What's unclear: CORE.md changes every session. Assembler runs at install/uninstall/boot. Who refreshes CLAUDE.md between boots? Nobody today.
   - Recommendation: **Query-time injection** via `bot/claude_query.build_options()`. Preserves Phase 3 contract; matches Phase 2 `_build_system_context()` pattern. Flagged for planner confirmation — if they insist on assemble-time, add an assembler refresh trigger after every memory write.

2. **Consolidation cadence — session-end, N-turn, time-based?**
   - What we know: D-09 says post-session, cadence is planner's call.
   - What's unclear: "Session" is fuzzy — Telegram chats are continuous.
   - Recommendation: Trigger fire-and-forget after every Nth successful reply (`context.chat_data["turn_count"] % 10 == 0`). Simplest to reason about; user can tune N via config.

3. **Git repo root — `~/hub/` or `~/hub/knowledge/`?**
   - What we know: ANIMAYA_HUB_DIR is `~/hub/knowledge/animaya/` (Phase 3 D-06). Hub-level git covers all knowledge, not just animaya.
   - What's unclear: Is hub already a git repo on the target LXC?
   - Recommendation: Plan a small probe task ("run `git -C ~/hub rev-parse --show-toplevel`"). Install.sh falls back to `git init` if no repo exists, at `$HOME/hub/`.

4. **Memory file structure (D-07 deferred research)**
   - What we know: Planner must pick among flat / tiered / topic-index.
   - What's unclear: Usage patterns not yet known (no real bot traffic).
   - Recommendation: **Tiered**: CORE.md (always injected) + topical files (e.g., `people.md`, `projects.md`, `preferences.md`) read on demand. Matches v1 convention, matches `build_consolidation_prompt()` v1 shape, minimal cognitive load. Planner validates in plan-research pass.

5. **`/identity` under ConversationHandler vs plain CommandHandler?**
   - What we know: D-04 says same code path as IDEN-01 onboarding.
   - What's unclear: python-telegram-bot ConversationHandler is heavier; a plain CommandHandler + stateful user_data works too.
   - Recommendation: ConversationHandler. Adds <20 LOC, handles timeouts + /cancel cleanly.

6. **Post-uninstall of identity while memory is installed — what happens to memory?**
   - What we know: Memory depends on identity (A7). Uninstall of identity is blocked per D-15 while memory is installed.
   - What's unclear: If user *removes* USER.md manually (not via uninstall), the bridge injects an empty identity block — silent UX issue.
   - Recommendation: Bridge's identity-reader logs a warning if the file is missing/placeholder at query time; no blocking.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git (CLI) | git-versioning module | Assumed present on Claude Box | any modern | None — hard requirement; install.sh fails loud if missing |
| python-telegram-bot | Identity `/identity` command + onboarding Q&A | Installed | 21.10+ | None |
| claude-code-sdk | Memory consolidation query | Installed | 0.0.25+ | None |
| pydantic | config_schema validation | Installed (Phase 3) | 2.13 | None |
| `~/hub/` directory | All three modules | Created by Phase 1 setup.sh (referenced in state) | — | install.sh mkdir -p |
| `~/hub/.git/` | git-versioning | MAY be absent on pristine boxes | — | install.sh runs `git init` on first install |
| Claude Haiku model access | Consolidation | Assumed via existing OAUTH_TOKEN | `claude-haiku-4-5` | If not accessible: fall back to Sonnet and flag budget warning. Plan a smoke test on Wave 0. |

**Missing dependencies with no fallback:**
- None blocking.

**Missing dependencies with fallback:**
- Hub git repo: falls back to `git init` in install.sh (covered).
- Haiku access: falls back to configured `CLAUDE_MODEL` with warning log.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.23+ (`asyncio_mode = "auto"`) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_modules_first_party.py -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IDEN-01 | Sentinel exists after install; cleared after Q&A completes | unit+integration | `pytest tests/test_modules_first_party.py::TestIdentityOnboarding -x` | ❌ Wave 0 |
| IDEN-02 | `install.sh` creates USER.md, SOUL.md, sentinel at correct paths | unit | `pytest tests/test_modules_first_party.py::TestIdentityInstall -x` | ❌ Wave 0 |
| IDEN-03 | `build_options()` output contains `<identity-user>` + `<identity-soul>` when files present | unit | `pytest tests/test_claude_query.py::test_identity_injection -x` | ❌ Wave 0 |
| IDEN-04 | `/identity` command re-runs onboarding, overwrites files | integration | `pytest tests/test_modules_first_party.py::TestIdentityReconfigure -x` | ❌ Wave 0 |
| MEMO-01 | After Claude Write to `memory/facts.md`, file persists | integration (mock SDK) | `pytest tests/test_modules_first_party.py::TestMemoryPersist -x` | ❌ Wave 0 |
| MEMO-02 | After file write, auto-commit tick creates a commit | integration | `pytest tests/test_modules_first_party.py::TestMemoryGitCommit -x` | ❌ Wave 0 |
| MEMO-03 | Consolidation query runs with `claude-haiku-4-5` + correct prompt | unit (mock SDK) | `pytest tests/test_modules_first_party.py::TestConsolidation -x` | ❌ Wave 0 |
| MEMO-04 | `build_options()` output contains `<memory-core>` when CORE.md present | unit | `pytest tests/test_claude_query.py::test_memory_core_injection -x` | ❌ Wave 0 |
| GITV-01 | commit_loop triggers commit after interval with changed files | integration | `pytest tests/test_modules_first_party.py::TestCommitLoop -x` | ❌ Wave 0 |
| GITV-02 | Two concurrent commits serialize via asyncio.Lock | unit | `pytest tests/test_modules_first_party.py::TestCommitLock -x` | ❌ Wave 0 |
| GITV-03 | `git add -- knowledge/` excludes out-of-scope files | integration | `pytest tests/test_modules_first_party.py::TestCommitScoping -x` | ❌ Wave 0 |
| GITV-01 | No-diff tick is a no-op (no empty commit) | unit | `pytest tests/test_modules_first_party.py::TestCommitSkipEmpty -x` | ❌ Wave 0 |
| MODS-05 | All three modules pass uninstall leakage check | integration | `pytest tests/test_modules.py::TestLeakage -x` (existing) | ✅ reuse |
| Telethon smoke | Real end-to-end onboarding via Telegram | manual | `python ~/hub/telethon/smoke_test.py --scenario onboarding` | Partial — harness exists (Phase 6), scenario needs writing |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_modules_first_party.py tests/test_claude_query.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green + Telethon onboarding scenario PASS before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_modules_first_party.py` — new file for identity/memory/git-versioning tests
- [ ] `tests/test_claude_query.py` — new file for `build_options()` injection tests
- [ ] `tests/conftest.py` — add fixtures: `tmp_hub_with_identity`, `tmp_hub_with_memory`, `tmp_hub_git_repo`
- [ ] Mock `claude_code_sdk.query` fixture for memory consolidation tests
- [ ] Telethon scenario script for onboarding (lives under `~/hub/telethon/`)

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 4 |
|-----------|------------------|
| Python 3.12, type hints everywhere | All new files in `bot/modules_runtime/` fully typed |
| Ruff line-length 100, rules E/F/I/W | Run `ruff check bot/modules_runtime/ modules/` before commit |
| snake_case for all identifiers | `commit_loop`, `consolidate_memory`, `onboarding_start`; file names like `memory.py`, `identity.py` |
| `Path` for filesystem, never string concatenation | USER_FILE, SOUL_FILE, CORE_FILE all `Path` objects |
| Per-module logging: `logger = logging.getLogger(__name__)` | One logger per file under `bot/modules_runtime/` |
| No runtime pip | install.sh scripts MUST NOT `pip install`; all deps in pyproject.toml |
| Module data in `~/hub/knowledge/animaya/` | Identity/memory data in `~/hub/knowledge/identity/` and `~/hub/knowledge/memory/` — *parallel to* animaya/, not inside. Confirm with Phase 1 layout. |
| Package namespace `bot` | `bot.modules_runtime.*`, not standalone |
| Strict startup validation with `sys.exit(1)` | `main.py` exits if TELEGRAM_BOT_TOKEN / CLAUDE_CODE_OAUTH_TOKEN missing (already done); add no new hard-fails |
| `# ──` section separators in larger files | Use in `git_versioning.py` (loop vs lock vs git helpers) |
| MODS-06 no cross-module imports | `bot.modules_runtime.memory` does NOT import `bot.modules_runtime.identity` — communicate via filesystem (memory reads USER.md; does not import identity code) |
| v1 convention `SOUL.md` — do NOT rename | Kept; pair with USER.md per D-02 |
| Simplest solution first | Sentinel file > ConversationHandler edge cases; path-scoped git add > custom diff engine |

---

## Sources

### Primary (HIGH confidence)
- `.planning/phases/04-first-party-modules/04-CONTEXT.md` — all locked decisions (D-01 through D-17), read directly
- `.planning/phases/03-module-system/03-CONTEXT.md` + `03-RESEARCH.md` — Phase 3 contract (assembler, registry, manifest, lifecycle), read directly
- `.planning/REQUIREMENTS.md` — IDEN/MEMO/GITV acceptance criteria, read directly
- `bot/modules/{manifest,registry,assembler,lifecycle,__main__}.py` — existing Phase 3 code, read directly
- `bot/features/git_versioning.py` v1 — reference for subprocess + threading → asyncio translation
- `bot/memory/core.py` v1 — reference for consolidation prompt shape
- `bot/claude_query.py` — existing `build_options()` extension point
- `bot/bridge/telegram.py` — existing `_build_system_context()` pattern; handler registration order
- `bot/main.py` — `_post_init` hook target; existing assembler call

### Secondary (MEDIUM confidence)
- [CITED: docs.python-telegram-bot.org] ConversationHandler reference for Q&A flow
- [VERIFIED: bot/features/git_versioning.py v1 in repo] — 3-call subprocess pattern proven

### Tertiary (LOW confidence)
- [CITED: anthropic.com/claude/haiku] Claude Haiku 4.5 model id `claude-haiku-4-5`, $1/M input — see Sources below
- [ASSUMED] Query-time vs assemble-time injection recommendation — derived from consistency with Phase 2 pattern; not explicitly locked in CONTEXT.md

**Web sources:**
- [Claude Haiku 4.5 - anthropic.com](https://www.anthropic.com/claude/haiku)
- [Models overview - Claude API Docs](https://platform.claude.com/docs/en/about-claude/models/overview)
- [Claude Haiku 4.5 pricing - OpenRouter](https://openrouter.ai/anthropic/claude-haiku-4.5)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every lib already in pyproject.toml; Haiku model id verified 2026-04-14
- Architecture: HIGH for git-versioning + identity file mechanics; MEDIUM for onboarding trigger + consolidation cadence (Claude's Discretion items)
- Pitfalls: HIGH — 8 concrete pitfalls enumerated from real integration surfaces
- Prompt injection channel (A4): MEDIUM-HIGH — strong recommendation for query-time, but planner may need to re-read D-03 to confirm

**Research date:** 2026-04-14
**Valid until:** 2026-06-14 (stable; recheck if Haiku model ID changes or python-telegram-bot 22 ships)

---

## RESEARCH COMPLETE

**Phase:** 4 - first-party-modules
**Confidence:** HIGH (locked decisions are all technically feasible; two assumptions flagged for user confirmation before execution)

### Key Findings
- **Prompt injection should happen at query-time (in `bot.claude_query.build_options()`), NOT assemble-time.** Identity and memory content changes per session; the Phase 3 assembler runs only on install/uninstall/boot. Query-time injection matches the existing Phase 2 `_build_system_context()` pattern and avoids a CLAUDE.md rewrite feedback loop.
- **Runtime code must live under `bot/modules_runtime/` (new package), not inside `modules/<name>/`.** Modules' shell scripts handle filesystem lifecycle; the bot process must own the onboarding state machine, consolidation query, and commit loop. Mirrors Phase 3's bridge pattern where bridge code lives in `bot/bridge/`.
- **Commit loop must use `application.post_init` + `application.create_task()`** — `bot/main.py` is sync and the event loop only exists inside `app.run_polling()`. Naive `asyncio.create_task` at startup raises.
- **Use path-scoped `git add -- knowledge/` and `asyncio.create_subprocess_exec`.** v1's `git add -A` + blocking `subprocess.run` both fail the MODS-06 / single-committer invariants.
- **Haiku 4.5 model ID is `claude-haiku-4-5`** ($1/M input, $5/M output) — verified via anthropic.com 2026-04-14. Flagged as Assumption A1 — user should confirm before locking.

### File Created
`/Users/admin/hub/workspace/animaya/.planning/phases/04-first-party-modules/04-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | All libs already installed; Haiku id verified today |
| Architecture | HIGH | All integration points traced to existing code lines; patterns are direct compositions of locked decisions |
| Pitfalls | HIGH | 8 concrete pitfalls from real seams (async/sync, handler order, sentinel durability, model-id selection) |
| Discretion items | MEDIUM | Onboarding trigger, consolidation cadence, `/identity` dispatcher style — strong recommendations given but user should bless once |

### Open Questions (6 total)
1. Assemble-time vs query-time injection — **strong recommendation: query-time**
2. Consolidation cadence — recommend every-N-turns
3. Git repo root — need probe on LXC (most likely `~/hub/`)
4. Memory file structure (D-07 deferred) — recommend tiered (CORE + topicals)
5. `/identity` as ConversationHandler vs plain CommandHandler — recommend ConversationHandler
6. Identity file missing-at-query-time UX — recommend warn-not-block

### Assumptions Requiring User Confirmation
- **A1** Haiku model id `claude-haiku-4-5`
- **A2** Hub git repo root is `~/hub/`
- **A7** memory depends on identity

### Ready for Planning
Research complete. Planner can now decompose Phase 4 into plans (recommend 3–5 plans: Wave 0 infra, identity, git-versioning, memory install, memory consolidation; or similar).
