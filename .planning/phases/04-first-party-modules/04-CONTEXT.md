# Phase 4: First-Party Modules - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver three first-party modules — `identity`, `memory`, `git-versioning` — each packaged as a Phase 3 module (manifest + install.sh + uninstall.sh + prompt snippet + owned_paths). Together they enrich every Claude interaction: identity injects user/assistant self-definition, memory injects a rolling core summary, git versioning captures every knowledge/ change with a single-committer guarantee.

Covers IDEN-01..04, MEMO-01..04, GITV-01..03. No dashboard UX (Phase 5). Module content lives in `~/hub/knowledge/{identity,memory}/` and is git-versioned by the `git-versioning` module.

</domain>

<decisions>
## Implementation Decisions

### Identity Module (IDEN-01..04)
- **D-01:** Onboarding is **Telegram-conversational**. On the first user message after identity module install, bot runs a short Q&A (≈3 questions: who the user is, who the assistant should be, how the user wants to be addressed) and writes answers to hub/knowledge/identity/. No dashboard, no seed-file editing required.
- **D-02:** Identity files are exactly two: `~/hub/knowledge/identity/USER.md` (user self-definition) and `~/hub/knowledge/identity/SOUL.md` (assistant identity/persona). Naming matches the v1 Animaya convention already documented in the project CLAUDE.md.
- **D-03:** IDEN-03 injection wraps each file in its own XML block inside the module's system-prompt snippet: `<identity-user>{USER.md content}</identity-user>` and `<identity-soul>{SOUL.md content}</identity-soul>`. Assembler then XML-wraps the whole module snippet per Phase 3 D-17.
- **D-04:** IDEN-04 reconfigure is a Telegram `/identity` command that re-runs the same onboarding flow and overwrites the files. Same code path as IDEN-01; no separate reconfigure surface. Dashboard edit form is a Phase 5 concern.
- **D-05:** Onboarding trigger: identity module startup reads USER.md/SOUL.md; if either is missing or still contains the placeholder sentinel, the module registers a one-shot "pending onboarding" state consumed by the bridge on next user message. Exact trigger mechanism is Claude's Discretion.

### Memory Module (MEMO-01..04)
- **D-06:** Claude writes memory using the **built-in Write/Edit tools** targeting `~/hub/knowledge/memory/`. No custom MCP tool, no skill file. The module's prompt snippet documents path + naming + size expectations. Mirrors the global auto-memory pattern already in use in `~/.claude/projects/.../memory/`.
- **D-07:** **Memory file structure is deferred to a deeper plan-phase research pass.** The planner must explicitly evaluate options (flat topic files vs tiered core/working/archive vs topic index) against expected usage, and pick a structure backed by research. Do not ship a shape without that pass.
- **D-08:** MEMO-04 injection: **only** the core summary file (working name `CORE.md`, final name planner decides alongside D-07) is injected into the system prompt. All other memory files are read on demand by Claude via the Read tool. Keeps prompt size bounded.
- **D-09:** MEMO-03 core summary is **auto-consolidated** by a separate SDK query using a **cheaper Claude model** (e.g. Haiku). Runs post-session (exact trigger — session-end, N-turn cadence, or manual — is planner's call). Soft cap ~150 lines; the consolidation prompt enforces the cap by instruction, not by hard truncation.
- **D-10:** Consolidation uses the Claude Code SDK with an explicit cheap-model override; the assistant's main query keeps the configured `CLAUDE_MODEL`. Planner picks the exact model string and budget surfaces.

### Git Versioning Module (GITV-01..03)
- **D-11:** GITV-01 committer is a **background asyncio task inside the bot process**. Commit interval comes from module config (default 300s — matches v1 `GIT_COMMIT_INTERVAL`). Task lifecycle ties to bot startup/shutdown. No systemd timer, no separate process.
- **D-12:** GITV-02 single-committer is enforced by an **`asyncio.Lock`** wrapping the commit operation inside the bot process. Since the bot is the only writer by design, in-process lock is sufficient. No file lock, no registry flag.
- **D-13:** GITV-03 commits are **single commit per interval covering all changed paths** under `~/hub/knowledge/` (scoped by `git add` path limits so the module only touches knowledge/, satisfying "scoped to module subdirectories"). Commit message format: `animaya: auto-commit {ISO timestamp}`. Skips entirely when there is no diff.
- **D-14:** Git-versioning module's `owned_paths` covers its config + the commit-task wiring, NOT `hub/knowledge/` itself (memory and identity own their subtrees). Uninstalling git-versioning stops the commit loop but leaves existing history intact.

### Module Boundaries & Install Order
- **D-15:** Per-module owned_paths (MODS-05):
  - `identity`: `~/hub/knowledge/identity/`
  - `memory`: `~/hub/knowledge/memory/`
  - `git-versioning`: no knowledge subtree; owns only its registered commit task + any config file it writes into its module dir.
- **D-16:** MODS-06 no-import isolation: modules communicate only through hub files (identity/memory write markdown; git-versioning reads the filesystem and commits). No Python imports between modules. Convention-enforced per Phase 3 D-20 — reinforced by the module authoring guide.
- **D-17:** Install order is driven by the Phase 3 lifecycle (install-time order → assembler order). Recommended first-install sequence after setup.sh: `identity → memory → git-versioning`. Planner confirms and wires into setup.sh per Phase 3 D-03.

### Claude's Discretion
- Exact filename of the core summary (`CORE.md` vs `SUMMARY.md` vs other) — aligned with D-07 research.
- Mechanism the identity module uses to signal "pending onboarding" to the bridge (in-memory flag, sentinel file, etc.).
- Haiku model id + token budget for the consolidation query.
- Whether `/identity` is a plain Telegram command (via python-telegram-bot command handler) or a bridge-routed natural-language intent.
- Exact commit-loop backoff/jitter when bot is idle (skip-if-no-diff is mandatory per D-13).
- Where consolidation runs (inline asyncio task in bot process vs scheduled per interval) — planner picks once D-09 cadence is set.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Identity Module (IDEN-01..04), §Memory Module (MEMO-01..04), §Git Versioning Module (GITV-01..03)
- `.planning/ROADMAP.md` §Phase 4 — Goal, success criteria, dependencies

### Prior Phase Decisions
- `.planning/phases/03-module-system/03-CONTEXT.md` — Module layout (D-01), registry (D-06/07), manifest schema (D-08/09/10), lifecycle contract (D-11..15), assembler (D-16..19), isolation (D-20)
- `.planning/phases/02-telegram-bridge/02-CONTEXT.md` — Telegram command/message wiring used by onboarding + `/identity`
- `.planning/phases/01-install-foundation/01-CONTEXT.md` — Hub knowledge layout, setup.sh contract

### Existing Code
- `bot/main.py` — startup path, assembler rebuild on boot (Phase 3 D-18)
- `bot/bridge/telegram.py` — command/message handlers; onboarding Q&A hooks here
- `bot/claude_query.py` — SDK options builder; point of override for cheap-model consolidation query (D-09/10)
- `modules/bridge/` — first-party module reference shape from Phase 3
- `bot/modules/` — lifecycle API (`install`, `uninstall`, registry, assembler)

### Project Context
- `.planning/PROJECT.md` — modular/reversible Animaya v2 core value; Hub knowledge/ as module state store
- `CLAUDE.md` §Conventions — `SOUL.md = identity`, `OWNER.md = owner` naming already in project guidance (supports D-02)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 3 module lifecycle (`bot/modules/`) — install/uninstall/registry/assembler already live
- Phase 2 Telegram handlers — command dispatcher can host `/identity`
- v1 `bot/features/git_versioning.py` — reference for background commit loop + interval pattern
- v1 `bot/memory/core.py` — reference for consolidation prompt shape (cheap-model variant is new)
- Claude Code SDK model override — already used in bridge; reuse pattern for consolidation query

### Established Patterns
- asyncio task lifecycle tied to bot startup/shutdown (Phase 2)
- Per-module logger (`logger = logging.getLogger(__name__)`)
- Env-driven config surfaced through manifest `config_schema`
- Strict pydantic manifests (Phase 3 D-10)

### Integration Points
- `bot/main.py` startup — identity-module pending-onboarding probe, git-versioning task spawn
- Bridge `_handle_message` — intercept first message when onboarding pending
- `setup.sh` — append `python -m bot.modules install identity && ... memory && ... git-versioning` per D-17

### New Surface
- `modules/identity/` — manifest, install.sh, uninstall.sh, prompt snippet, onboarding flow code (can live in module dir or under `bot/` with module shim; planner decides)
- `modules/memory/` — manifest, install.sh, uninstall.sh, prompt snippet, consolidation job
- `modules/git-versioning/` — manifest, install.sh (installs commit-loop hook), uninstall.sh (removes hook), prompt snippet (likely minimal)
- `hub/knowledge/identity/USER.md`, `SOUL.md`
- `hub/knowledge/memory/` (structure TBD per D-07)

</code_context>

<specifics>
## Specific Ideas

- SOUL.md naming is intentional — it carries from v1 conventions documented in the root CLAUDE.md. Do not rename it to `assistant.md` even if it reads more generic.
- Memory structure (D-07) is the single biggest open design question in Phase 4 — planner must not skip the research pass. User explicitly flagged it.
- Core summary regeneration with a cheaper model is a deliberate cost choice; this is new behavior vs v1 which consolidated with the main model.
- Single-committer via asyncio.Lock is sufficient **because** committer lives in bot process; this invariant must be preserved (no future out-of-process writer to hub/knowledge/).
- `/identity` reusing the same onboarding flow is a feature, not duplication — keep one code path.

</specifics>

<deferred>
## Deferred Ideas

- Dashboard identity/memory edit forms — Phase 5 (dashboard scope)
- Semantic/vector search over memory — v2 (SRCH-01/02)
- Skill files (`~memory.md` etc.) — v2 (ADVM-01)
- Memory auto-summarization triggered by size rather than cadence — planner may consider but shipping decision is cadence-based
- Per-module commit scoping (separate commits per module subdir) — single commit chosen for v1 simplicity
- Out-of-process committer (systemd timer) — only revisit if a non-bot writer is ever added
- Manifest config surface to switch consolidation model — can ship with hard default first

</deferred>

---

*Phase: 04-first-party-modules*
*Context gathered: 2026-04-14*

## Locked Assumptions

**A1:** claude-haiku-4-5 (memory consolidation model; overridable per-install via memory module `config_schema.consolidation_model.default`)
**A2:** ~/hub (git repo root; git-versioning uses `git -C ~/hub` with path-scoped `-- knowledge/`)
**A7:** depends: ["identity"] (memory module manifest requires identity installed first; blocks identity uninstall while memory present)
**Confirmed:** 2026-04-15

**D-05 mechanism:** sentinel file at ${IDENTITY_DIR}/.pending-onboarding (created by install.sh, cleared by onboarding state-machine on completion, removed by uninstall.sh for MODS-05 clean).
