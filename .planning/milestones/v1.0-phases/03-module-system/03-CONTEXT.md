# Phase 3: Module System - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver manifest-driven module lifecycle machinery: filesystem layout, pydantic-validated manifest schema, install/uninstall script contract with auto-rollback, hub-state registry.json, and CLAUDE.md assembler that merges a base prompt with per-module XML-wrapped snippets. Phase 3 also retroactively converts the Phase 2 Telegram bridge into the first-party bridge module so the lifecycle is exercised end-to-end.

Covers MODS-01 through MODS-06. No user-facing install CLI (library API only); dashboard install UX is Phase 5. No new functional modules (identity/memory/git) — those are Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Module Location & Scope
- **D-01:** All modules live in `~/animaya/modules/<name>/` inside the repo. First-party and user-installed modules share the same directory. No hub-side module folder in Phase 3.
- **D-02:** Phase 2 Telegram bridge becomes a first-party module (`modules/bridge/`). It gets a manifest, install.sh, uninstall.sh, and prompt snippet. Uninstalling it kills the bot — that's acceptable; lifecycle uniformity wins.
- **D-03:** `setup.sh` invokes the internal install API (`python -m bot.modules install bridge`) on fresh install to auto-install first-party modules. Idempotent: rejects on already-installed (D-11).
- **D-04:** No public user-facing install CLI in Phase 3. Only the Python API (`bot.modules.install(name)`, `uninstall(name)`). Dashboard-driven install lives in Phase 5.
- **D-05:** Installation is binary: installed or uninstalled. No "disabled but kept" state.

### Registry
- **D-06:** `registry.json` at `~/hub/knowledge/animaya/registry.json` is the canonical source of truth for installed modules. Git-versioned with Hub (aligns with Phase 1 D-06).
- **D-07:** Registry entries include: `name`, `version`, `manifest_version`, `installed_at` (ISO timestamp), and `config` (snapshot of user-provided config at install time).

### Manifest Schema (pydantic)
- **D-08:** Required fields: `manifest_version` (int, currently 1), `name` (str, matches folder), `version` (semver str), `system_prompt_path` (str, relative to module dir), `owned_paths` (list[str], every file/dir the module creates for MODS-05 leakage check).
- **D-09:** Optional fields: `scripts.install` / `scripts.uninstall` (default `install.sh` / `uninstall.sh`), `depends` (list[str] of module names), `config_schema` (JSON Schema dict, passthrough for Phase 5 dashboard forms — Phase 3 stores but does not render).
- **D-10:** Validation is **strict**: unknown fields are rejected. Schema evolution happens via `manifest_version` bump.

### Lifecycle Contract
- **D-11:** Install scripts receive context via env vars: `ANIMAYA_MODULE_DIR`, `ANIMAYA_HUB_DIR`, `ANIMAYA_CONFIG_JSON` (serialized user config). No positional args. Same contract for uninstall.sh.
- **D-12:** Registry update order: run install.sh → on exit 0, write registry entry. Registry is the source of truth for "confirmed installed state".
- **D-13:** Install failure (install.sh exit non-zero) triggers **auto-rollback**: core invokes uninstall.sh best-effort to clean partial artifacts, then verifies MODS-05 (no owned_paths remain). No registry entry written.
- **D-14:** Reinstalling already-installed module is **rejected** with clear error. User must `uninstall` first (explicit intent).
- **D-15:** Dependency check: if `manifest.depends` lists modules not in registry, install is rejected. Uninstall of a module with dependents is rejected. No auto-cascade.

### CLAUDE.md Assembly
- **D-16:** Module prompts are assembled in **install order** (ascending `installed_at` from registry). Deterministic, reproducible.
- **D-17:** Each module's prompt is wrapped in `<module name="{name}">...</module>` XML tags. Clear source tracking for Claude.
- **D-18:** Assembly trigger: both at **end of install/uninstall** AND at **every bot startup**. Defensive against drift from registry edits, hub git pulls, or partial failures.
- **D-19:** Output is written to `~/animaya/CLAUDE.md` (repo), with `bot/templates/CLAUDE.md` prepended as the base/core prompt. Module sections appended below.

### MODS-06 Isolation
- **D-20:** No-cross-module-imports rule is **convention-enforced**, not structurally checked. Documented in module authoring guide (to be written as part of Phase 3). No ruff rule, no import scanner.

### Claude's Discretion
- Exact field names inside registry.json (use D-07 as spec but naming like `installed_at` vs `installedAt` — pick pythonic snake_case).
- install.sh and uninstall.sh shell style (bash vs sh shebang, error handling). Pick `#!/usr/bin/env bash` with `set -euo pipefail`.
- Where the bridge module's `owned_paths` should point — Phase 2 bridge writes per-chat working dirs under DATA_PATH. Planner decides whether to declare the DATA_PATH root or per-chat dirs.
- Handling of `config_schema` beyond storage in Phase 3 (render is Phase 5 concern).
- How dependency ordering interacts with install-order for CLAUDE.md (dependencies install first, so install-order naturally respects DAG).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Module System — MODS-01 through MODS-06 acceptance criteria
- `.planning/ROADMAP.md` §Phase 3 — Goal, success criteria, dependencies

### Prior Phase Decisions
- `.planning/phases/01-install-foundation/01-CONTEXT.md` — Hub knowledge layout (D-06), CLAUDE.md assembler stub (D-09), setup.sh contract
- `.planning/phases/02-telegram-bridge/02-CONTEXT.md` — Bridge module definitions, per-chat working dirs, claude_query integration

### Existing Code (to be converted / integrated)
- `bot/main.py` — Phase 1 CLAUDE.md assembler (currently stub); extend to merge module prompts
- `bot/bridge/telegram.py`, `bot/bridge/formatting.py`, `bot/claude_query.py` — Phase 2 code that becomes the bridge module
- `bot/templates/CLAUDE.md` — Base/core prompt prepended by assembler (D-19)
- `bot/dashboard/app.py` — Reference `_rebuild_claude_md()` pattern noted in Phase 1 code context
- `pyproject.toml` — Add pydantic if not already present; add `bot.modules` package

### Project Context
- `.planning/PROJECT.md` — LXC-native, modular, reversible (Animaya v2 core value)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- CLAUDE.md assembler stub already exists from Phase 1 (referenced in bot/main.py)
- `bot/templates/CLAUDE.md` exists as base prompt template
- `bot/bridge/` tree is the first module's code body — just needs manifest + scripts + prompt snippet
- pyproject.toml tracks deps; pydantic likely already present (FastAPI dashboard needs it)

### Established Patterns
- Per-module logging: `logger = logging.getLogger(__name__)`
- snake_case everywhere; Path objects for filesystem
- Env-var driven config (aligns with D-11 script contract)
- Strict startup validation with `sys.exit(1)` on missing config

### Integration Points
- `bot/main.py` startup path — trigger assembler rebuild on boot (D-18)
- `setup.sh` — invoke `python -m bot.modules install bridge` as post-venv step (D-03)
- `~/hub/knowledge/animaya/` — registry.json location + hub artifacts pathing

### New Surface
- `bot/modules/__init__.py` — public API: `install()`, `uninstall()`, `list_installed()`, `validate_manifest()`
- `bot/modules/manifest.py` — pydantic model, strict mode
- `bot/modules/registry.py` — read/write hub registry.json
- `bot/modules/assembler.py` — CLAUDE.md rebuild
- `bot/modules/__main__.py` — `python -m bot.modules install <name>` entrypoint (internal, not promoted as user CLI)
- `modules/bridge/` — first-party bridge module (manifest + install/uninstall + prompt snippet, code stays in `bot/bridge/`)

</code_context>

<specifics>
## Specific Ideas

- Manifest schema MUST be strict (unknown field = error). D-10 comes directly from user pick — explicit anti-pattern avoidance.
- Registry is NOT ephemeral runtime state — it lives in hub knowledge, git-versioned, so it's auditable and survives `rm -rf ~/animaya && git clone` (as long as hub/ is retained).
- Bridge-becomes-module means the bridge's install.sh is trivial (mostly no-op; the code is already in `bot/bridge/`) but exercising the lifecycle is the point.
- CLAUDE.md assembler is invoked on boot, so drift between registry and CLAUDE.md is self-healing at next restart (D-18).

</specifics>

<deferred>
## Deferred Ideas

- User-facing module CLI (`animaya module install ...`) — consider after Phase 5 dashboard lands
- Structural MODS-06 enforcement (ruff rule or import scanner) — convention only in Phase 3
- Three-state enable/disable (installed+disabled) — deferred; no Phase 4/5 dependency identified
- `manifest_version` migration tooling — currently only v1 exists
- Bridge module reload without full bot restart — would need assembler hot-swap; not in scope
- Module `config_schema` form rendering — Phase 5 dashboard concern

</deferred>

---

*Phase: 03-module-system*
*Context gathered: 2026-04-14*
